from django.shortcuts import get_object_or_404

from apps.canvas_auth.models import User
from apps.suggest.models import get_most_stickered_unfollowed_users
from canvas import bgwork
from canvas.api_decorators import api_decorator
from canvas.metrics import Metrics
from canvas.models import Comment
from canvas.view_guards import require_user
from django.conf import settings

urlpatterns = []
api = api_decorator(urlpatterns)

@api('follow_user')
@require_user
def follow_user(request, user_id):
    Metrics.follow_user.record(request, user_id=user_id)
    user_to_follow = get_object_or_404(User, pk=user_id)
    request.user.follow(user_to_follow)

    @bgwork.defer
    def update_stickered_by_user():
        get_most_stickered_unfollowed_users(request.user).force()

    @bgwork.defer
    def achievements():
        if len(user_to_follow.redis.followers.smembers()) >= 10:
            user_to_follow.kv.achievements.achieve('ten_followers')

        if len(request.user.redis.following.smembers()) >= 10:
            request.user.kv.achievements.achieve('following_ten')

@api('unfollow_user')
@require_user
def unfollow_user(request, user_id):
    canvas_user = User.objects.get(username=settings.CANVAS_ACCOUNT_USERNAME)
    if user_id == canvas_user.id:
        raise PermissionDenied("Canvas cannot be unfollowed.")

    Metrics.unfollow_user.record(request, user_id=user_id)
    user_to_unfollow = get_object_or_404(User, pk=user_id)
    request.user.unfollow(user_to_unfollow)

    @bgwork.defer
    def update_stickered_by_user():
        get_most_stickered_unfollowed_users(request.user).force()

@api('follow_thread')
@require_user
def follow_thread(request, comment_id):
    Metrics.follow_thread.record(request, comment_id=comment_id)
    comment = get_object_or_404(Comment, pk=comment_id)
    comment.followers.sadd(request.user.id)
    request.user.follow_thread(comment)

@api('unfollow_thread')
def unfollow_thread(request, comment_id):
    Metrics.unfollow_thread.record(request, comment_id=comment_id)
    comment = get_object_or_404(Comment, pk=comment_id)
    comment.followers.srem(request.user.id)
    request.user.unfollow_thread(comment)

