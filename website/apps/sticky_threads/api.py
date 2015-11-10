from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response

from apps.canvas_auth.models import User
from canvas import fact
from canvas.models import Comment
from canvas.api_decorators import api_decorator
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff
from services import Services

urlpatterns = []
api = api_decorator(urlpatterns)

@api('render_sticky_thread_preview')
@require_staff
def render_sticky_thread_preview(request, short_id):
    from apps.sticky_threads.models import StickyThread, ThreadPreview

    thread_preview = ThreadPreview.get_by_short_id(short_id)

    ctx = {
        'thread': thread_preview,
        'admin_view': True,
        'show_curation_info': False,
    }

    return HttpResponse(render_jinja_to_string('sticky_threads/thread_preview.html', ctx))

@api('sticky_comment')
@require_staff
def sticky_comment(request, comment_id, text):
    from apps.sticky_threads.models import StickyThread, update_sticky_thread_cache

    comment = get_object_or_404(Comment.all_objects, pk=comment_id)

    sticky = StickyThread.get_or_create(comment)
    sticky.curator = request.user
    sticky.timestamp = Services.time.time()
    sticky.text = text
    sticky.save()

    update_sticky_thread_cache()

    return {'info': comment.admin_info}

