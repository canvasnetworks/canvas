from django.shortcuts import get_object_or_404

from apps.suggest.models import get_suggested_tags, get_most_stickered_unfollowed_users
from canvas import bgwork
from canvas.api_decorators import api_decorator
from canvas.exceptions import ServiceError
from canvas.metrics import Metrics
from canvas.view_guards import require_staff, require_POST, require_user

urlpatterns = []
api = api_decorator(urlpatterns)

@api('hide_suggested_user')
@require_user
def hide_suggested_user(request, user_id):
    request.user.redis.muted_suggested_users.sadd(user_id);
    @bgwork.defer
    def update_calls():
        get_most_stickered_unfollowed_users(request.user).force()
    return {}

@api('hide_suggested_tag')
@require_user
def hide_suggested_tag(request, tag):
    request.user.redis.muted_suggested_tags.sadd(tag)
    @bgwork.defer
    def update_calls():
        get_suggested_tags(request.user).force()
    return {}
