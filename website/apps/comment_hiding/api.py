from django.shortcuts import get_object_or_404

from apps.canvas_auth.models import User
from canvas.api_decorators import api_decorator
from canvas.metrics import Metrics
from canvas.models import Comment
from canvas.view_guards import require_user

urlpatterns = []
api = api_decorator(urlpatterns)

@api('hide_comment')
@require_user
def hide_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    request.user.redis.hidden_comments.hide_comment(comment)

    Metrics.downvote_action.record(request, comment=comment.id)
    Metrics.hide_comment.record(request)

@api('hide_thread')
@require_user
def hide_thread(request, comment_id):
    """
    `comment_id` may be the thread OP or any reply in it.

    Also downvotes.
    """
    comment = get_object_or_404(Comment, pk=comment_id)
    request.user.redis.hidden_threads.hide_thread(comment)

    sticker_count = comment.downvote(request.user, ip=request.META['REMOTE_ADDR'])

    Metrics.downvote_action.record(request, count=sticker_count, comment=comment.id)
    Metrics.hide_thread.record(request)

