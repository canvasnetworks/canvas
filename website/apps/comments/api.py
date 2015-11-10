import time

from django.shortcuts import get_object_or_404
from django.conf import settings

from canvas import (models, experiments, session_utils, search, bgwork, economy, last_sticker, fact, util,
                    stickers, browse, knobs)
from canvas.api_decorators import api_decorator
from canvas.exceptions import ServiceError, InsufficientPrivileges
from canvas.forms import validate_and_clean_comment
from canvas.models import Metrics, Comment, UserInfo
from canvas.notifications.actions import Actions
from canvas.redis_models import RateLimit, redis
from canvas.view_guards import require_user

urlpatterns = []
api = api_decorator(urlpatterns)

@api('validate_post')
def validate_comment(request, reply_text='', parent_comment=None, replied_comment=None,
                     reply_content=None, category=None, external_content=None):
    """ Return {"success": True} if valid. """
    validate_and_clean_comment(
        request.user,
        reply_text=reply_text,
        parent_comment=parent_comment,
        replied_comment=replied_comment,
        reply_content=reply_content,
        category=category,
        external_content=external_content,
    )

@api('post')
@require_user
def post_comment(request, anonymous=False, reply_text='', parent_comment=None, replied_comment=None,
                 reply_content=None, category=None, external_content=None, fact_metadata={},
                 title=None, tags=[]):
    anonymous = bool(anonymous)

    # Remember the user's preference for anonymous posting.
    request.user.userinfo.post_anonymously = anonymous
    request.user.userinfo.save()

    replied_comment, parent_comment, reply_content, external_content, category, title = validate_and_clean_comment(
        request.user,
        reply_text=reply_text,
        parent_comment=parent_comment,
        replied_comment=replied_comment,
        reply_content=reply_content,
        category=category,
        external_content=external_content,
        title=title,
    )

    comment = models.Comment.create_and_post(
        request,
        request.user,
        anonymous,
        category,
        reply_content,
        parent_comment=parent_comment,
        reply_text=reply_text,
        replied_comment=replied_comment,
        external_content=external_content,
        fact_metadata=fact_metadata,
        title=title,
        tags=tags,
    )

    if parent_comment is None:
        key = 'posted_unvisited_threads'
        val = request.session.get(key, set())
        val.add(comment.id)
        request.session[key] = val

    @bgwork.defer
    def create_footer():
        if comment.footer.should_exist():
            comment.footer.call_update_in_new_process()

    @bgwork.defer
    def credit_original_author():
        if not comment.reply_content or not comment.reply_content.is_remix() or not comment.reply_content.remix_of.first_caption:
            return
        original_author = comment.reply_content.remix_of.first_caption.author
        if original_author != comment.author:
            economy.credit_received_remix(original_author)

    @bgwork.defer
    def do_notify():
        Actions.replied(request.user, comment)

    @bgwork.defer
    def monster_achievement():
        if comment.is_monster_top():
            request.user.kv.achievements.achieve('monster_top')
        elif comment.is_monster_bottom():
            request.user.kv.achievements.achieve('monster_bottom')

    return {'comment': comment.details()}

@api('replies')
def get_replies(request, comment_id=0, replies_after_timestamp=0.):
    from apps.features import feature_flags as features

    op_id = int(comment_id)
    # Fudge the timestamp a bit to err on the side of too many replies which we'll dedupe, instead of clicking the
    # button and having nothing happening.
    fudge = 5
    replies_after_timestamp = float(replies_after_timestamp) - fudge

    op = get_object_or_404(models.Comment, id=op_id)
    replies = [r.details() for r in op.replies.filter(models.Visibility.q_visible).filter(timestamp__gt=replies_after_timestamp).order_by('timestamp')]

    Metrics.get_new_replies.record(request, op=op_id, replies_after_timestamp=replies_after_timestamp)

    if features.thread_new(request):
        from apps.threads.jinja_tags import thread_new_comment
        html = u''.join(thread_new_comment({'request': request}, reply, ignore_lazy_load=True)
                        for reply in replies)
        return {'replies': replies, 'html': html}

    return {'replies': replies}

@api('mute')
def mute_thread(request, comment_id):
    """
    Mutes the op of a given comment, so that the user never receives any notifications pertaining to that thread.
    """
    comment = get_object_or_404(models.Comment, pk=comment_id)
    request.user.redis.mute_thread(comment)

@api('pin')
@require_user
def pin_comment(request, comment_id):
    """ Pin the thread this comment is a part of. """
    comment = get_object_or_404(models.Comment, pk=comment_id)
    pin = comment.add_pin(request.user)
    if pin is not None:
        # If a reply was pinned, this will be the OP.
        pinned_comment = pin.comment
        request.user.redis.pinned_bump_buffer.bump(pinned_comment.id, time.time())
        Metrics.pin.record(request, comment=pinned_comment.id)

@api('unpin')
@require_user
def unpin_comment(request, comment_id):
    comment = get_object_or_404(models.Comment, pk=comment_id)
    comment.remove_pin(request.user)
    fact.record("unpin", request, {'comment': comment.id})

@api('flag')
@require_user
def flag_comment(request, comment_id):
    comment = get_object_or_404(models.Comment, pk=comment_id)

    # If the user hits the flag rate limit, silently ignore it.
    prefix = 'user:%s:flag_limit:' % request.user.id

    def allowed(key, val):
        if request.user.is_staff:
            return True
        freq, timespan = val
        return RateLimit(prefix+key, freq, timespan).allowed()

    if not all(allowed(key, val) for key,val in knobs.FLAG_RATE_LIMITS.iteritems()):
        Metrics.flag_ratelimit.record(request, comment=comment.id)
        raise ServiceError('Flag rate limit exceeded.')
    else:
        flag = comment.add_flag(request.user, ip=request.META['REMOTE_ADDR'])

        if flag is not None:
            if settings.PROJECT == 'canvas':
                request.user.redis.hidden_comments.hide_comment(comment)

            Metrics.flag.record(request, comment=comment.id)

            if comment.anonymous:
                Metrics.flag_anonymous_post.record(request, comment=comment.id)

    if settings.AUTO_MODERATE_FLAGGED_COMMENTS_THRESHOLD is not None:
        if (not comment.judged
                and comment.details().flag_counts[0] == settings.AUTO_MODERATE_FLAGGED_COMMENTS_THRESHOLD):
            comment.visibility = models.Visibility.DISABLED
            comment.save()
            comment.visibility_changed()

    return {'flag_counts': comment.details().flag_counts, 'flag_id': flag.id}

@api('unflag')
@require_user
def unflag_comment(request, flag_id):
    flag = get_object_or_404(models.CommentFlag, id=flag_id)
    comment = flag.comment

    if flag.user != request.user:
        raise InsufficientPrivileges()

    flag.undone = True
    flag.save()
    comment.details.force()

    fact.record("unflag", request, {'comment': comment.id})

    return {'flag_counts': comment.details().flag_counts, 'flag_id': flag.id}

@api('downvote_action')
@require_user
def downvote_comment(request, comment_id):
    user = request.user
    comment = get_object_or_404(models.Comment, pk=comment_id)
    sticker_count = comment.downvote(request.user, ip=request.META['REMOTE_ADDR'])
    Metrics.downvote_action.record(request, count=sticker_count, comment=comment.id)

@api('delete')
@require_user
def delete_comment(request, comment_id):
    comment = models.Comment.all_objects.get(id=comment_id)

    if not comment.author == request.user:
        raise ServiceError("Not comment author")

    comment.moderate_and_save(models.Visibility.UNPUBLISHED, request.user, undoing=True)

    Metrics.delete_post.record(request, comment=comment.id)

@api('claim')
@require_user
def claim_comment(request, comment_id):
    comment = models.Comment.all_objects.get(id=comment_id)

    if not comment.author == request.user:
        raise ServiceError("Not comment author")

    comment.make_non_anonymous(request.user)

    Metrics.claim_post.record(request, comment=comment.id)

@api('get_user_sticker')
@require_user
def get_user_sticker(request, comment_id):
    """
    Returns whether or not a user has stickered a post.
    """
    comment = get_object_or_404(models.Comment, pk=comment_id)
    sticker = bool(comment.get_user_sticker(request.user))
    return {
        "sticker": sticker,
    }

@api('moderate')
@require_user
def moderate_comment(request, comment_id, visibility, undoing=False):
    comment = get_object_or_404(models.Comment.all_objects, pk=comment_id)
    #TODO don't get attribs from user input without whitelisting or something first.
    visibility = getattr(models.Visibility, str(visibility.upper()))
    can_moderate = request.user.can_moderate_visibility

    if comment.visibility not in can_moderate or visibility not in can_moderate:
        raise InsufficientPrivileges()

    comment.moderate_and_save(visibility, request.user, undoing)

    return {'info': comment.admin_info}

@api('mark_offtopic')
@require_user
def mark_offtopic_comment(request, comment_id, ot_hidden=False):
    comment = get_object_or_404(models.Comment.all_objects, pk=comment_id)
    comment.mark_offtopic(request.user, offtopic=ot_hidden)

