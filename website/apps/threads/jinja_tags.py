from jinja2 import Markup, contextfunction

from apps.features import feature_flags as features
from canvas.templatetags.jinja_base import jinja_context_tag, render_jinja_to_string


@jinja_context_tag
def thread_new_comment(context, comment, is_op=False, is_current=False, is_first_reply_with_content=False, is_last_reply_with_content=False, ignore_lazy_load=False):
    from canvas.templatetags.helpers import TemplateComment
    from canvas.models import CommentSticker

    request = context['request']
    comment = TemplateComment(comment, request_context=context, is_op=is_op)

    try:
        sticker_name = comment.top_sticker()['name']
    except TypeError:
        sticker_name = None

    try:
        viewer_following_thread = request.user.redis.followed_threads.sismember(comment.id)
    except AttributeError:
        viewer_following_thread = False

    ctx = {
        'request': request,
        'short_id': context.get('short_id'),
        'comment': comment,
        'can_edit_tags': request.user.is_staff or comment.is_author(request.user),
        'lazy_content': features.lazy_content(request),
        'is_current':is_current,
        'ignore_lazy_load': ignore_lazy_load,
        'is_first_reply_with_content': is_first_reply_with_content,
        'is_last_reply_with_content': is_last_reply_with_content,
        'my_post': comment.is_author(request.user),
        'stickered_by_viewer': bool(CommentSticker.get_sticker_from_user(comment.id, request.user)),
        'sticker_name': sticker_name,
        'has_content': bool(comment.reply_content_id),
        'viewer_following_thread': viewer_following_thread,
    }

    return Markup(render_jinja_to_string('threads_new/_thread_comment.html', ctx))

@jinja_context_tag
def thread_new_pagination(context):
    return Markup(render_jinja_to_string('threads_new/_pagination.html', context))

