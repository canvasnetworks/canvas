from apps.invite_remixer.urls import reverse_invite_id
from canvas.metrics import Metrics
from canvas.util import Base36DecodeException


class TrackInviteMiddleware(object):
    def process_request(self, request):
        invite_id = request.GET.get('invite')
        if not invite_id:
            return

        try:
            inviter, url = reverse_invite_id(invite_id)
        except Base36DecodeException:
            return
        
        Metrics.visit_from_invite.record(request, inviter=inviter.id, invite_url=url, homepage_invite=homepage_invite)

        request.session['inviter'] = inviter.id

