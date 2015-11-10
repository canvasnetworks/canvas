from django.shortcuts import get_object_or_404

from apps.canvas_auth.models import User
from apps.suggest.models import get_suggested_tags
from apps.tags.models import Tag
from canvas import bgwork, models
from canvas.api_decorators import api_decorator
from canvas.exceptions import ServiceError
from canvas.metrics import Metrics
from canvas.view_guards import require_staff, require_POST, require_user
from services import Services

urlpatterns = []
api = api_decorator(urlpatterns)

@api('follow_tag')
@require_user
def follow_tag(request, tag):
    Metrics.follow_tag.record(request, tag=tag)
    request.user.redis.followed_tags.zadd(tag, Services.time.time())

    @bgwork.defer
    def update_suggested_tags():
        get_suggested_tags(request.user).force()

    return {}

@api('unfollow_tag')
@require_user
def unfollow_tag(request, tag):
    Metrics.unfollow_tag.record(request, tag=tag)
    request.user.redis.followed_tags.zrem(tag)

    @bgwork.defer
    def update_suggested_tags():
        get_suggested_tags(request.user).force()

    return {}

@api('update_comment_tags')
@require_user
def update_comment_tags(request, comment_id, tags):
    comment = get_object_or_404(models.Comment, pk=comment_id)
    if request.user.is_staff or request.user == comment.author:
        new_tags = set(tags)
        original = comment.tags.smembers()

        # tags to remove
        for t in (original - new_tags):
            Tag(t).untag_comment(comment)
            comment.tags.srem(t)

        # tags to add
        for t in (new_tags - original):
            Tag(t).tag_comment(comment)
            comment.tags.sadd(t)

        comment.details.force()
        ret_tags = []
        for t in comment.tags.smembers():
            ret_tags += [{
                'name': t,
                'url': Tag(t).get_absolute_url(),
            }]

        return {'tags': ret_tags}

    else:
        raise ServiceError("Permission denied")

