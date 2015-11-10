from django.http import HttpResponseRedirect

from apps.invite_remixer.urls import reverse_invite_id
from canvas.metrics import Metrics

def invite(request, invite_id):
    inviter, url = reverse_invite_id(invite_id)

    homepage_invite = url == '/'
    Metrics.visit_from_invite.record(request, inviter=inviter.id, invite_url=url, homepage_invite=homepage_invite)

    request.session['inviter'] = inviter.id

    return HttpResponseRedirect(url)

