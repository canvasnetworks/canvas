from django.http import HttpResponse, HttpResponseRedirect

from apps.canvas_auth.models import User
from apps.logged_out_homepage.models import ThreadPreview
from canvas import fact
from canvas.api_decorators import api_decorator
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff


urlpatterns = []
api = api_decorator(urlpatterns)

@api('render_thread_preview')
@require_staff
def render_thread_preview(request, short_id):
    thread_preview = ThreadPreview.get_by_short_id(short_id)    
    
    ctx = {
        'thread': thread_preview,
        'admin_view': True,
        'show_curation_info': False,
    }

    return HttpResponse(render_jinja_to_string('logged_out_homepage/thread_preview.html', ctx))

