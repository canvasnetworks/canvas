from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

from apps.share_tracking.models import ShareTrackingUrl
from canvas import fact
from canvas.api_decorators import api_decorator
from canvas.util import base36decode_or_404

def shared_url(request, share_id):
    share = get_object_or_404(ShareTrackingUrl, id=base36decode_or_404(share_id))
    share.record_view(request)
    return HttpResponseRedirect(share.redirect_url)

urlpatterns = []
api = api_decorator(urlpatterns)

@api('create')
def share_create(request, url, channel):
    share = ShareTrackingUrl.create(request.user, url=url, channel=channel)
    fact.record('create_share_url', request, dict(url=url, channel=channel, share=share.id))

    return {
        'share_url': share.url,
        'share_get_arg': share.get_arg,
        'share_id': share.id,
    }

