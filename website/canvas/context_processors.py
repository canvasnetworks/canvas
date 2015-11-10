from canvas import stickers as canvas_stickers, experiments, knobs, last_sticker
from canvas.models import * #TODO delete
from django.conf import settings

def base_context(request):
    """
    `nav_category` gets a default value here, but you can override it by setting a `nav_category` property on the
    `request` object to the value you want.
    """
    user = request.user

    following, following_truncated = [], []
    if user.is_authenticated():
        following = Category.objects.filter(followers__user=user)
        following = following.order_by('name')
        _following = [cat.details() for cat in following]
        _following = sorted(_following, key=lambda cat: cat['followers'], reverse=True)
        _following = _following[:knobs.FOLLOWING_MENU_COLUMNS]
        following_truncated = sorted(_following, key=lambda cat: cat['name'])
    else:
        following = list(Category.objects.filter(id__in=Category.get_whitelisted()).order_by('name'))
    if not following_truncated:
        following_truncated = following

    stickers = canvas_stickers.all_details(user)

    sticker_event = canvas_stickers.get_active_event()

    try:
        draw_from_scratch_content = Content.all_objects.get(id=Content.DRAW_FROM_SCRATCH_PK).details()
    except Content.DoesNotExist:
        draw_from_scratch_content = None

    context = {
        'following': [cat.details() for cat in following],
        'following_truncated': following_truncated,
        'following_menu_length': len(following_truncated),

        'sticker_pack_minimized': bool(request.COOKIES.get('sticker_pack_minimized')),

        'global_stickers': stickers,
        'stickers_primary': canvas_stickers.primary_types,
        'stickers_inventory': canvas_stickers.get_inventory(user),
        'stickers_seasonal': canvas_stickers.get_active_seasonal_stickers(),
        'stickers_sharing': canvas_stickers.sharing_types,
        'stickers_actions': canvas_stickers.get_actions(user),
        'seasonal_event': canvas_stickers.get_active_event(),
        'num1_sticker': canvas_stickers.get('num1'),
        'current_user': user,
        # Note that we grab an empty UserInfo for users that do not already have userinfo.
        #TODO now that we have canvas_auth.models.AnonymousUser, this *should* be unnecessary.
        'current_user_info': user.userinfo if hasattr(user, "userinfo") else UserInfo(),
        'draw_from_scratch_content': draw_from_scratch_content,
        'CANVAS_SUB_SITE': settings.CANVAS_SUB_SITE,
        'PROJECT': settings.PROJECT,
    }

    # The key here can't be the same as in locals, otherwise the key in locals takes precedence in
    # render_to_response.
    get_nav = Category.get(request.GET.get('nav'))
    if get_nav and get_nav.disabled:
        get_nav = None

    if get_nav == Category.MY and not request.user.is_authenticated():
        # Explicit ?nav=following links are meaningless for logged-out users
        get_nav = Category.ALL

    default_category = Category.get_default(request.user)
    try:
        nav_category = request.nav_category
        nav_category_is_default = False
    except AttributeError:
        nav_category = get_nav or default_category
        nav_category_is_default = True

    try:
        nav_tag = request.nav_tag
    except AttributeError:
        nav_tag = None

    context['enable_timeline'] = context['current_user_info'].enable_timeline
    context['enable_timeline_posts'] = context['current_user_info'].enable_timeline_posts

    context['nav_tag'] = nav_tag
    context['nav_category'] = nav_category.details()
    context['nav_category_is_default'] = nav_category_is_default
    context['default_category'] = default_category.details()
    context['follows_category'] = context['nav_category'] in context['following']

    # These sorts are not tied to a group.
    context['personal_sorts'] = ['pinned', 'flagged']
    context['unsticky_sorts'] = context['personal_sorts'] + ['hot', 'stickered']
    context['group_found_limit'] = Category.FOUND_LIMIT

    context['knobs'] = knobs

    context['show_post_thread_button'] = True

    context['fb_namespace'] = settings.FACEBOOK_NAMESPACE

    # Sticker attract mode.
    if request.user.is_authenticated():
        context['show_attract_mode'] = False
    else:
        context['show_attract_mode'] = not 'first_page_view' in request.session
    request.session['first_page_view'] = True

    for setting in ['DEBUG', 'DOMAIN', 'UGC_HOST']:
        context[setting] = getattr(settings, setting)

    #
    # Realtime.
    #

    if nav_category == Category.MY:
        context['category_channel'] = [cat.posts_channel.sync() for cat in following]
    else:
        context['category_channel'] = [nav_category.posts_channel.sync()]

    context['flag_channel'] = ''
    if user.is_authenticated():
        if user.can_moderate_flagged:
            unjudged = Comment.unjudged_flagged().count()
            context['flagged_unjudged'] = unjudged
            context['flag_channel'] = CommentFlag.flag_channel.sync()

        context['user_channel'] = user.redis.channel.sync()
        context['user_pinned_channel']  = user.redis.pinned_posts_channel.sync()
    context['last_sticker'] = last_sticker.get_info(request.user)

    return context

