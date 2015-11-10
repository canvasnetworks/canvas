from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from apps.canvas_auth.models import User
from apps.feed import jinja_tags
from apps.feed.redis_models import feed_for_user
from canvas import knobs
from canvas.api_decorators import api_decorator
from canvas.metrics import Metrics
from canvas.view_guards import require_user

urlpatterns = []
api = api_decorator(urlpatterns)

@api('items')
@require_user
def feed_items(request, earliest_timestamp_cutoff):
    feed_items = feed_for_user(request.user, earliest_timestamp_cutoff=earliest_timestamp_cutoff)

    Metrics.feed_infinite_scroll.record(request)

    return HttpResponse(u''.join([jinja_tags.feed_item({'request': request}, item) for item in feed_items]))

