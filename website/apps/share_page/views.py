from django.http import HttpResponseRedirect

import apps.threads.views
from canvas.view_helpers import redirect_trailing, CommentViewData

@redirect_trailing
def share_detail(request, *args, **kwargs):
    if request.user.is_authenticated():
        view_data = CommentViewData(request, *args, **kwargs)
        return HttpResponseRedirect(view_data.linked_comment().url)

    return apps.threads.views.logged_out_thread_view(request, *args, **kwargs)

