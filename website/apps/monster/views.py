import random

from django.http import HttpResponseRedirect

from django.conf import settings
from apps.monster.util import public_api_method
from apps.monster.models import (MonsterPart, MonsterInvite, MonsterTileDetails, MONSTER_GROUP,
                                 CompletedMonsterSet, mobile_details_from_queryset)
from canvas import fact, browse
from canvas.api_decorators import api_decorator
from canvas.browse import TileDetails
from canvas.cache_patterns import CachedCall
from canvas.metrics import Metrics
from canvas.models import Content, Comment, Category
from canvas.shortcuts import r2r_jinja
from canvas.util import base36encode
from canvas.view_guards import require_staff, require_user
from canvas.view_helpers import redirect_trailing, CommentViewData, tile_render_options
from configuration import Config

urlpatterns = []
api = api_decorator(urlpatterns)

def landing(request, **kwargs):
    category = Category.get(name=MONSTER_GROUP)
    sort = 'new'
    kwargs['offset'] = request.GET.get('offset', 0)
    show_pins = False

    nav = browse.Navigation.load_json_or_404(
        kwargs,
        sort=sort,
        category=category,
        mobile=request.is_mobile,
        replies_only=True,
        public_only=True,
    )

    front_data = {
        'tiles': browse.get_browse_tiles(request.user, nav),
        'render_options': tile_render_options(sort, show_pins),
    }

    # Overrides the default nav category that gets set in a context processor.
    request.nav_category = category

    sort_types = []
    if sort in ['active', 'new']:
        sort_types.extend([
            ('active threads', '/x/%s/active' % category.name),
            ('new posts', '/x/%s/new' % category.name)
        ])
        active_sort_url = '/x/%s/%s' % (category.name, sort)

    nav_data = nav.dump_json()

    front_data.update(locals())
    front_data['nav_category'] = category.details()
    front_data['DOMAIN'] = settings.DOMAIN

    return r2r_jinja('monster/landing.html', front_data)

@require_user
def create(request):
    ctx = {
        'request': request,
        'monster_group': MONSTER_GROUP,
        'monster_content': Content.all_objects.get(id=Content.SMALL_DRAW_FROM_SCRATCH_PK).details(),
    }
    return r2r_jinja('monster/create.html', ctx)

def random(request):
    part = MonsterPart.get_random_new_monster(request.user)
    skip = 'skip' in request.GET
    if part:
        if skip:
            Metrics.skip_monster.record(request, monster_id=part.id)
        else:
            Metrics.random_monster_complete.record(request, monster_id=part.id)
        return HttpResponseRedirect('/monster/{0}/complete'.format(base36encode(part.id)))
    else:
        Metrics.no_more_monsters.record(request)
    ctx = {'request':request}
    return r2r_jinja('monster/nomore.html', ctx)

@redirect_trailing
def view(request, short_id, option=None):
    from apps.monster.jinja_tags import monster_image_tile

    view_data = CommentViewData(request, short_id)
    main_comment = view_data.op_comment
    replies = [Comment.details_by_id(cid) for cid in view_data.reply_ids]
    has_replies = len(replies) > 0
    complete_link = option and (option == 'complete')
    if complete_link and request.user.is_anonymous():
        fact.record('monster_start_flow', request, {'monster_id': short_id})
    reply_id = None

    if option:
        try:
            reply_id = int(option)
        except ValueError:
            pass

    (
        (main_comment,),
        replies
    ) = CachedCall.many_multicall(
        [main_comment],
        replies,
    )

    replies = [reply for reply in replies if not reply.is_collapsed]

    monster_part = MonsterPart.get_by_comment(main_comment)
    main_comment_details = main_comment
    main_comment = TileDetails(main_comment)

    made_bottom = False
    made_top = main_comment.comment.real_author == request.user.username

    linked_monster_footer_image = ""
    current_monster_index = 0

    for i in range(len(replies)):
        reply = replies[i]
        if reply_id is not None and reply.id == int(reply_id):
            current_monster_index = i
        elif reply.real_author == request.user.username and reply_id is None:
            current_monster_index = i
            made_bottom = True

    try:
        if (has_replies
                and replies[current_monster_index].reply_content
                and replies[current_monster_index].reply_content.footer):
            linked_monster_footer_image = replies[current_monster_index].reply_content.footer['name']
    except (AttributeError, IndexError):
        pass

    made_part = made_top or made_bottom

    if made_part:
        CompletedMonsterSet(request.user).sadd(main_comment.comment.id)

    can_make_bottom = (not made_part) and complete_link
    can_invite = made_top

    # incomplete monster without an invite link, send to monster index
    if not has_replies and not complete_link and not can_invite:
        return HttpResponseRedirect('/monster')

    ctx = {
        'can_invite': can_invite,
        'can_make_bottom': can_make_bottom,
        'current_monster_index': current_monster_index,
        'domain': settings.DOMAIN,
        'made_bottom': made_bottom,
        'made_part': made_part,
        'made_top': made_top,
        'main_comment': main_comment,
        'monster_content': main_comment.comment.reply_content,
        'og_image_url': linked_monster_footer_image.replace("https", "http", 1),
        'monster_group': MONSTER_GROUP,
        'monster_name': main_comment.comment.title,
        'replies': MonsterTileDetails.from_shared_op_details_with_viewer_stickers(request.user, main_comment_details, replies),
        'request': request,
        'short_id': main_comment.comment.short_id(),
        'start_content': Content.all_objects.get(id=Content.SMALL_DRAW_FROM_SCRATCH_PK).details(),
    }

    return r2r_jinja('monster/view.html', ctx)

@public_api_method
@require_user
def api_browse_monsters(request, payload=None):
    """
    accepts posted json in the following format
    {'offset': 0, 'count': 9}

    returns client sanitized comment details
    """
    if not payload:
        payload = {'offset':0, 'count':9}

    offset = payload['offset']
    count = 9

    category = Category.get(name=MONSTER_GROUP)
    sort = 'new'

    nav = browse.Navigation.load_json_or_404(
        payload,
        sort=sort,
        category=category,
        mobile=request.is_mobile,
        replies_only=True,
        public_only=True,
        offset=payload['offset'],
        count=payload['count'],
    )

    data = {
        'monsters': mobile_details_from_queryset(browse.get_front_comments(request.user, nav)),
    }

    return data

@public_api_method
@require_user
def api_monster_details(request, short_id, payload={}):
    view_data = CommentViewData(request, short_id)
    main_comment = view_data.op_comment
    replies = [Comment.details_by_id(cid) for cid in view_data.reply_ids]
    has_replies = len(replies) > 0

    (
        (main_comment,),
        replies
    ) = CachedCall.many_multicall(
        [main_comment],
        replies,
    )

    treplies = []
    made_bottom = False
    for reply in replies:
        cur = reply.to_client()
        if reply.real_author == request.user.username:
            cur['current_user_authored'] = made_bottom = True
        treplies.append(cur)

    ctx = {
        'top': main_comment,
        'bottoms': treplies,
        'current_user_made_bottom': made_bottom,
        'current_user_made_top': main_comment.real_author == request.user.username,
        'start_content': Content.all_objects.get(id=Content.SMALL_DRAW_FROM_SCRATCH_PK).details(),
    }

    return ctx
