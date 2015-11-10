import logging
import time

from django.conf import settings
from django.conf.urls.defaults import url, patterns, include
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from facebook import GraphAPIError, GraphAPI
from sentry.client.models import client

from apps.canvas_auth.models import User
from apps.suggest.models import get_most_stickered_unfollowed_users
from canvas import knobs, util
from canvas import models, experiments, session_utils, search, bgwork, economy, last_sticker, fact, util, stickers, browse
from canvas.api_decorators import api_decorator, json_service
from canvas.browse import TileDetails
from canvas.cache_patterns import CachedCall
from canvas.exceptions import ServiceError, InsufficientPrivileges, NotLoggedIntoFacebookError
from canvas.models import Metrics, Comment, UserInfo
from canvas.notifications.actions import Actions
from canvas.redis_models import RateLimit, redis
from canvas.templatetags.jinja_tags import explore_tiles
from canvas.upload import api_upload, chunk_uploads
from canvas.util import * #TODO: Remove
from canvas.view_guards import require_staff, require_POST, require_user
from canvas.view_helpers import tile_render_options
from configuration import Config

urls = patterns('canvas.api',
    url(r'^activity/', include('apps.activity.api')),
    url(r'^chunk/', include(chunk_uploads)),
    url(r'^comment/', include('apps.comments.api')),
    url(r'^comment_hiding/', include('apps.comment_hiding.api')),
    url(r'^feed/', include('apps.feed.api')),
    url(r'^following/', include('apps.following.api')),
    url(r'^invite_remixer/', include('apps.invite_remixer.api')),
    url(r'^monster/', include('apps.monster.api')),
    url(r'^logged_out_homepage/', include('apps.logged_out_homepage.api')),
    url(r'^share/', include('apps.share_tracking.views')),
    url(r'^sticky_threads/', include('apps.sticky_threads.api')),
    url(r'^suggest/', include('apps.suggest.api')),
    url(r'^tags/', include('apps.tags.api')),
    url(r'^threads/', include('apps.threads.api')),
    url(r'^upload$', api_upload),
    url(r'^', include('apps.analytics.api')),
)

api = api_decorator(urls)

@api('user/exists', csrf_exempt=True)
def user_exists(request, username):
    """ Returns None if the username is valid and does not exist. """
    error_msg = User.validate_username(username or "")
    if error_msg:
        raise ServiceError(error_msg)

@api('user/actually_exists', csrf_exempt=True)
def user_actually_exists(request, username):
    """ Returns true or false, doesn't validate the username. """
    return {'exists': User.objects.filter(username__iexact=username).exists()}

#TODO remove once we stop migrating accounts to drawquest.
@api('user/info_for_drawquest_migration', csrf_exempt=True)
@require_staff
def user_info_for_drawquest_migration(request, username):
    user = get_object_or_404(User, username=username)

    profile_image_url = None
    if user.userinfo.profile_image is not None:
        profile_image_details = user.userinfo.profile_image.reply_content.details()
        profile_image_url = profile_image_details.get_absolute_url_for_image_type('original')

    return {
        'username': user.username,
        'email': user.email,
        'bio': user.userinfo.bio_text,
        'profile_image_url': profile_image_url,
    }

#TODO remove once we stop migrating accounts to drawquest.
@api('user/check_password', csrf_exempt=True)
@require_staff
def user_check_password(request, username, password):
    user = get_object_or_404(User, username=username)
    return {'correct': user.check_password(password)}

@api('user/facebook_exists')
def facebook_exists(request, facebook_id):
    return {'exists': not UserInfo.facebook_is_unused(facebook_id)}

@api('user/set_facebook')
@require_user
def set_facebook(request, facebook_id):
    request.user.userinfo.facebook_id = facebook_id
    request.user.userinfo.save()

@api('group/exists')
def group_exists(request, name):
    """ Returns None if the group name is valid and does not exist. """
    group = models.Category.all_objects.get_or_none(name=name)
    if group:
        raise ServiceError("This group already exists.")

@api('stamps/search')
def search_stamps(request, query, start):
    """
    Searches the special "stamps" group for stamps that match the search query.

    Returns {comments: [list of comment details]}
    """
    qs = query
    try:
        start = int(start)
    except TypeError:
        raise ServiceError('Invalid "start" parameter.')

    stamps = models.Category.objects.get(name="stamps")
    if qs:
        ids = [x for x in models.Comment.objects.filter(category=stamps).filter(
            Q(reply_text__icontains=qs) | Q(title__icontains=qs)
        ).values_list('id', flat=True)]
        ids = ids[start:start+32]
        comments = models.Comment.curated.exclude(reply_content__id=None).in_bulk(ids)
        details = CachedCall.multicall([comments[id].details for id in ids if id in comments])

    else:
        comments = models.Comment.curated.filter(category=stamps).exclude(reply_content__id=None).order_by('-id')
        comments = comments[start:start+32]
        details = CachedCall.queryset_details(comments)

    return {'comments': details}

@api('stamps/staff_picks')
def staff_pick_stamps(request, page):
    page = int(page)
    page_size = 20

    b36_ids = knobs.REMIX_IMAGES_STAFF_PICKS[page*page_size:(page+1)*page_size]

    ids = [util.base36decode(b36_id) for b36_id in b36_ids]

    details = CachedCall.queryset_details(Comment.objects.in_bulk_list(ids))

    return {'comments': details}

@api('front/more')
def front_more(request, nav_data={}, offset=0, tile_renderer="explore_tiles"):
    offset = int(offset)
    nav = browse.Navigation.load_json_or_404(nav_data, offset=offset)
    show_pins = request.user.is_authenticated()

    if request.user.is_authenticated():
        metric = 'logged_in_infinite_scroll'
    else:
        metric = 'logged_out_infinite_scroll'

    @request.on_success.defer
    def record_scroll():
        getattr(Metrics, metric).record(request, nav_data=nav_data, offset=offset)

    tiles = browse.get_browse_tiles(request.user, nav)

    #TODO delete once we've resolved the missing small_image issue.
    for tile in tiles:
        if hasattr(tile, 'check_for_small_image'):
            tile.check_for_small_image(request)

    return _disposition_tiles(request, dict(request=request), tiles, nav, show_pins=show_pins, tile_renderer=tile_renderer)

@api('user/more')
def user_more(request, nav_data={}, offset=0, tile_renderer="explore_tiles"):
    """ Fetches more posts for infinite scroll on the user page. """
    offset = int(offset)
    nav = browse.Navigation.load_json_or_404(nav_data, offset=offset)

    posts = browse.get_user_data(request.user, nav)

    show_delete_option = nav.user == request.user and nav.userpage_type != 'stickered'

    context = dict(request=request, show_delete_option=show_delete_option)

    return _disposition_tiles(request, context, posts, nav, show_pins=False, tile_renderer=tile_renderer)

def _disposition_tiles(request, context, posts_or_tiles, nav, show_pins=False, tile_renderer='explore_tiles'):
    from apps.monster.jinja_tags import monster_image_tiles

    #TODO refactor since less is being reused now. also fixing the front_more usage of this was a little hacky.

    category = nav.category.details() if nav.category else None

    render_options = tile_render_options(nav.sort, show_pins)

    tile_renderer = {
        'monster_image_tiles'   : monster_image_tiles,
        'explore_tiles'         : explore_tiles,
    }[tile_renderer]

    return HttpResponse(tile_renderer(context, posts_or_tiles, render_options, category))

@api('view_thread/more')
def view_thread_more(request, ids, tile_renderer="jinja_thread_page_tiles"):
    tiles = [TileDetails(reply.details()) for reply in Comment.visible.in_bulk(ids).itervalues()]
    from canvas.templatetags.jinja_tags import jinja_thread_page_tile
    tiles = ''.join(jinja_thread_page_tile(dict(request=request), tile) for tile in tiles)
    return HttpResponse(tiles)

@api('user/set_profile')
@require_user
def user_set_profile(request, comment_id):
    if comment_id is None:
        profile_comment = None
    else:
        profile_comment = get_object_or_404(Comment, id=comment_id)

    request.user.userinfo.profile_image = profile_comment

    if request.user.userinfo.profile_image is not None:
        request.user.userinfo.bio_text = profile_comment.reply_text

    request.user.userinfo.save()

    User.avatar_by_username(request.user.username).force()
    return {'comment_id': comment_id}

@api('user/level_up')
@require_user
def user_level_up(request):
    reward_stickers = economy.level_up(request.user)
    return {'stats': last_sticker.get_info(request.user), 'reward_stickers': reward_stickers}

@api('sticker/comment/validate')
@require_user
def can_sticker_comment(request, comment_id, type_id):
    comment = get_object_or_404(models.Comment, pk=comment_id)
    return comment.validate_sticker(request.user, type_id)

def _sticker_comment(request, comment, type_id, skip_dupe_check=False, skip_self_check=False, epic_message=None):
    """ Returns the number of stickers remaining for the given sticker type. """
    if epic_message:
        Metrics.epic_sticker_message.record(request)

    return comment.sticker(request.user,
                           type_id,
                           epic_message=epic_message,
                           skip_dupe_check=skip_dupe_check,
                           skip_self_check=skip_self_check,
                           ip=request.META['REMOTE_ADDR'])

@api('sticker/comment')
@require_user
def add_sticker_to_comment(request, comment_id, type_id, epic_message=None):
    """ Stickers a comment. You can be logged in or out. """
    sticker = stickers.get(int(type_id))
    comment = get_object_or_404(models.Comment, pk=comment_id)

    if epic_message and len(epic_message) > knobs.STICKER_MESSAGE_MAX_LENGTH:
        raise ServiceError("Message is too long.")
    elif epic_message and not (sticker.cost and sticker.cost >= knobs.EPIC_STICKER_COST_THRESHOLD):
        raise ServiceError("Messages can only be attached to epic stickers.")

    # Calculate if this user has exceeded the stickering rate limit.
    prefix = 'user:%s:stick_limit:' % request.user.id
    if not RateLimit(prefix+'h', 200, 60*60).allowed() or not RateLimit(prefix+'d', 300, 8*60*60).allowed():
        Metrics.sticker_ratelimit.record(request, sticker_type=sticker.type_id, comment=comment.id)
        raise ServiceError("Attempting to sticker too quickly.")

    prev_top_sticker = comment.details().top_sticker()
    remaining = _sticker_comment(request, comment, sticker.type_id, epic_message=epic_message)
    Metrics.sticker.record(request, sticker_type=sticker.type_id, comment=comment.id)

    comment_details = comment.details()
    top_sticker = comment_details.top_sticker()

    @bgwork.defer
    def update_stickered_users():
        get_most_stickered_unfollowed_users(request.user).force()

    if prev_top_sticker is None or prev_top_sticker['type_id'] != top_sticker:
        @bgwork.defer
        def update_footer():
            if comment.footer.should_exist():
                comment.footer.call_update_in_new_process()

    return {
        'new_counts': comment_details.sticker_counts,
        'sorted_counts': comment_details.sorted_sticker_counts(),
        'top_sticker': top_sticker,
        'remaining': remaining,
    }

@api('group/follow')
@require_user
def follow_group(request, category_id):
    return _follow_or_unfollow_group(request, category_id, True)

@api('group/unfollow')
@require_user
def unfollow_group(request, category_id):
    return _follow_or_unfollow_group(request, category_id, False)

def _follow_or_unfollow_group(request, category_id, follow):
    #TODO why does this default to 0?
    category_id = int(category_id or 0)
    category = get_object_or_404(models.Category, id=category_id)
    existing = models.FollowCategory.objects.get_or_none(category=category, user=request.user)

    if follow:
        if not existing:
            try:
                models.FollowCategory(
                    category=category,
                    user=request.user
                ).save()
            except model.FollowCategory.IntegrityError:
                pass
        Metrics.follow.record(request, category=category.id)
    else:
        if existing:
            existing.delete()
            fact.record("unfollow", request, {'category': category.id})

    # Update following count.
    category.details.force()

    return {'follows': [follow.category.details() for follow in request.user.following.all()]}

@api('group/new')
@require_user
def new_group(request, group_name, group_description):
    name = group_name
    description = group_description

    if models.Category.all_objects.get_or_none(name=name):
        raise ServiceError('A group already exists with that name.')
    if models.Category.objects.filter(founder=request.user).count() >= models.Category.FOUND_LIMIT:
        raise ServiceError('Sorry, you can only found up to %s groups at this time.' % models.Category.FOUND_LIMIT)

    group = models.Category(
        founder=request.user,
        founded=time.time(),
        name=name,
        description=description,
    )

    problem = group.validate()
    if problem:
        raise ServiceError(problem)

    group.save()

    request.user.userinfo.details.force()

    # A founder auto-follows their group.
    models.FollowCategory(
        category=group,
        user=request.user
    ).save()

    group_info = {'name': name, 'description': description}
    fact.record('new_group', request, group_info)
    Metrics.new_group.record(request, group_info=group_info)

@api('group/edit')
@require_user
def edit_group(request, group_name, group_description=None, group_disabled=None, referees=None):
    group = get_object_or_404(models.Category.all_objects, name=group_name)

    # This can't be an if/elif/else, since there are staff founders.
    if not (group.can_modify(request.user) or group.can_disable(request.user)):
        raise InsufficientPrivileges()

    if group_disabled is not None:
        if group.can_disable(request.user):
            group.visibility = models.Visibility.DISABLED if bool(group_disabled) else models.Visibility.PUBLIC
        else:
            raise InsufficientPrivileges()

    if group.can_modify(request.user):
        if group_description is not None:
            group.description = group_description
        if referees is not None:
            previous_referees = list(group.moderators.all())
            new_referees = list(User.objects.filter(username__in=referees))
            group.moderators = new_referees
            # Flush the UserInfos for users being unref'd or ref'd.
            for ref in set(previous_referees + new_referees):
                if not (ref in previous_referees and ref in new_referees):
                    ref.userinfo.details.force()

    problem = group.validate()
    if problem:
        raise ServiceError(problem)

    group.save()
    group.details.force()

@api('script/share')
@require_user
def script_share(request, s3sum):
    if not s3sum.isalnum():
        raise ServiceError('sums must be alphanumeric')

    remixplugin = models.RemixPlugin(author=request.user, timestamp=Now(), s3md5=s3sum)
    remixplugin.save()
    return {'plugin_url': remixplugin.get_url()}

@api('script/getsum')
@require_user
def script_getsum(request, short_id):
    rp = models.RemixPlugin.get_from_short_id(short_id)
    return {'sum': rp.s3md5}

@api('store/buy')
@require_user
def store_buy(request, item_type, item_id, quantity=1):
    #item_id could be a sticker.type_id or a Sticker.
    #TODO ^^^ is this true? item_id comes from JSON, so how would it be a Sticker? --alex

    try:
        quantity = int(quantity)
    except TypeError:
        raise ServiceError('Invalid parameter values.')

    if quantity == 0:
        raise ServiceError("Can't buy 0 stickers.")

    if not stickers.get(item_id).is_purchasable(request.user):
        raise ServiceError('Sticker is unpurchasable for you.')

    if item_type == 'sticker':
        try:
            remaining = economy.purchase_stickers(request.user, item_id, quantity)
        except economy.InvalidPurchase, ip:
            raise ServiceError(*ip.args)
    else:
        raise ServiceError('Invalid item_type.')

    return {'new_balance': remaining}

class NoNotificationError(ServiceError):
    def __init__(self):
        ServiceError.__init__(self, "No such notification.")

#TODO delete
@api('notification/acknowledge')
@require_user
def acknowledge_notification(request, nkey):
    """
    Acknowledge and dismiss an in-site notification.

    `nkey`:
        Key of notification.
    """
    nkey = int(nkey)

    notifications = request.user.redis.notifications.get()

    for note in notifications:
        if note['nkey'] == nkey:
            break
    else:
        # This notification key does not exist in the user's notification queue.
        # Probably the user has multiple tabs open, and the notification was acknowledged in another tab.
        raise NoNotificationError()

    success = request.user.redis.notifications.acknowledge(nkey)
    if not success:
        raise NoNotificationError()

@api('testing/test_bgwork', public_jsonp=True)
def test_bgwork(request):
    """ Used by canvas.test.test_bgwork. Writes a file we can check for. """
    @bgwork.defer
    def write_flag_file():
        import os
        from configuration import Config
        path = Config['test_bgwork_path']
        if not path:
            return
        with file(path, 'a'):
            os.utime(Config['test_bgwork_path'], None)

@api('sentry/js_exception')
def sentry_js_exception(request, stackInfo, url):
    """
    Logs an exception in Sentry. POST the following JSON structure:
        {
            "url": "http://example.com/foo/bar",
            "stackInfo": stack // a JSONified "stack info" object that TraceKit provides.
        }
    (See: https://github.com/csnover/TraceKit)

    For now we just log the JSON string. In the future we could format it into something Sentry understands better.
    """
    def stringify(obj):
        return util.dumps(obj, indent=2)

    stack_info = stackInfo
    message = unicode(stack_info.get('message', 'Unknown error'))
    try:
        message += '\n' + ' '*100 + '\n\nStack trace:\n\n' + stringify(stack_info['stack'])
    except KeyError:
        pass

    kwargs = {
        'url':    url,
        'view':   stack_info.get('name', 'JavaScript'), # The main title of this error.
        'level':  logging.ERROR,
        'logger': 'javascript',
    }

    client.create_from_text(message, **kwargs)

@api('staff/redis')
@require_staff
def get_redis(request, key):
    """
    Grabs an entity from Redis given a key.
    """
    for getter in [redis.hgetall, redis.get]:
        try:
            value = getter(key)
            assert value
            return dict(value_in_redis=util.loads(value))
        except Exception, e:
            logging.debug(e)
            continue
    return {}

@api('staff/send_notification_email')
@require_staff
def send_notification_email(request, action, username):
    user = get_object_or_404(User, username=username)
    try:
        pn = getattr(Actions, action)(user)
    except AttributeError:
        raise Http404('No such action.')

@api('facebook/toggle_sharing')
@require_user
def toggle_sharing(request):
    request.user.userinfo.enable_timeline_posts = not request.user.userinfo.enable_timeline_posts
    request.user.userinfo.save()
    return {'enabled': request.user.userinfo.enable_timeline_posts}

def _facebook_graph_action(action, post, access_token, request):
    send_action = "{}:{}".format(settings.FACEBOOK_NAMESPACE, action)
    @bgwork.defer
    def do_graph_action():
        try:
            graph = GraphAPI(access_token)
            graph.put_object('me', send_action, post=post)
            if action == 'sticker':
                Metrics.timeline_sticker.record(request, post=post)
            elif action == 'remix':
                Metrics.timeline_remix.record(request, post=post)
        except GraphAPIError:
            if action == 'sticker':
                Metrics.timeline_sticker_error.record(request, post=post)
            elif action == 'remix':
                Metrics.timeline_remix_error.record(request, post=post)

@api('facebook/sticker')
@require_user
def share_sticker(request, post, access_token):
    if request.user.userinfo.enable_timeline:
        return _facebook_graph_action('sticker', post, access_token, request)

@api('facebook/remix')
@require_user
def share_remix(request, post, access_token):
    if request.user.userinfo.enable_timeline and request.user.userinfo.enable_timeline_posts:
        return _facebook_graph_action('remix', post, access_token, request)

