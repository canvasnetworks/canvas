from datetime import timedelta as td

from django.conf import settings
from django.http import HttpResponse

from apps.activity.models import get_activity_stream_items
from drawquest.api_cache import cached_api
from drawquest.apps.quests import signals
from apps.activity import jinja_tags
from canvas.api_decorators import api_decorator
from canvas.metrics import Metrics
from canvas.view_guards import require_user

urlpatterns = []
api = api_decorator(urlpatterns)

@api('activity_stream')
@require_user
def activity_stream(request, earliest_timestamp_cutoff=None):
    if settings.PROJECT == 'drawquest':
        return HttpResponse('')

    activities = get_activity_stream_items(request.user, earliest_timestamp_cutoff=earliest_timestamp_cutoff)

    Metrics.activity_stream_infinite_scroll.record(request)

    return HttpResponse(u''.join([jinja_tags.activity_stream_item(activity, request.user)
                                  for activity in activities]))

@api('activities')
@require_user
@cached_api(timeout=td(days=1), key=['activities'], add_user_to_key=True)
def activity_stream_items(request):
    activities = get_activity_stream_items(request.user)
    return {'activities': activities}

@api('mark_activity_read')
@require_user
def mark_activity_read(request, activity_id):
    request.user.redis.activity_stream.mark_read(activity_id)

@api('mark_all_activities_read')
@require_user
def mark_all_activities_read(request):
    request.user.redis.activity_stream.mark_all_read()

