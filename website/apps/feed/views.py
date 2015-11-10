from canvas import knobs
from canvas.shortcuts import r2r_jinja
from canvas.view_guards import require_user, require_staff
from services import Services

@require_user
def feed(request):
    from apps.feed.redis_models import feed_for_user, sticky_threads

    sticky_items = sticky_threads(request.user)
    feed_items = feed_for_user(request.user, items_to_skip=sticky_items)

    request.user.kv.feed_last_viewed.set(Services.time.time())
    request.user.kv.feed_unseen.set(0)

    show_feed_tutorial = not request.user.kv.saw_feed_tutorial.get()
    request.user.kv.saw_feed_tutorial.set(True)

    ctx = {
        'sticky_threads': sticky_items,
        'items': feed_items,
        'show_feed_tutorial': show_feed_tutorial,
    }
    return r2r_jinja('feed/feed.html', ctx, request)

