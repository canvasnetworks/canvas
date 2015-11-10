from django.shortcuts import get_object_or_404

from canvas.api_decorators import api_decorator
from canvas.models import Comment
from canvas.shortcuts import r2r_jinja

urlpatterns = []
api = api_decorator(urlpatterns)

@api('thread_comment_details')
def thread_comment_details(request, comment_id):

    comment = get_object_or_404(Comment, pk=comment_id)
    replies = [c.details() for c in comment.get_deep_replies()]
    remixes = [c.details() for c in comment.get_remixes()]
    ctx = {
        'request': request,
        'replies': replies,
        'remixes': remixes,
    }

    return r2r_jinja('threads/comment_details.html', ctx)

