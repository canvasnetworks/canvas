from canvas.exceptions import ServiceError
from canvas.redis_models import RateLimit, redis
from django.conf import settings

def check_star_rate_limit(request, comment):
    from drawquest.apps.stars.models import get_star_sticker
    # Calculate if this user has exceeded the stickering rate limit.
    prefix = 'user:{}:stick_limit:'.format(request.user.id)
    if not RateLimit(prefix+'h', 200, 60*60).allowed() or not RateLimit(prefix+'d', 300, 8*60*60).allowed():
        Metrics.sticker_ratelimit.record(request, sticker_type=get_star_sticker().type_id, comment=comment.id)
        raise ServiceError("Attempting to star too quickly.")

