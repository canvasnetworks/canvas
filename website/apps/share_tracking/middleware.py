from canvas.util import base36decode, Base36DecodeException
from services import Services

from apps.share_tracking.models import ShareTrackingUrl


class TrackShareViewsMiddleware(object):
    def process_request(self, request):
        share_b36 = request.GET.get('s')
        if not share_b36:
            return
            
        try:
            share_id = base36decode(share_b36)
        except Base36DecodeException:
            return

        stu = ShareTrackingUrl.objects.get_or_none(id=share_id)
        if not stu:
            return
            
        stu.record_view(request)


class TrackClickthroughMiddleware(object):
    def process_request(self, request):
        clickthrough_type = request.GET.get('ct')
        if not clickthrough_type:
            return

        metric = getattr(Services.metrics, clickthrough_type + "_clickthrough", None)

        if not metric:
            return
            
        meta = dict((k,v) for (k,v) in request.GET.items() if k.startswith('ct_'))

        metric.record(request, **meta)

