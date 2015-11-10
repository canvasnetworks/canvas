from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, Http404

from apps.canvas_auth.models import User
from apps.invite_remixer import urls
from apps.invite_remixer.models import RemixInvites
from canvas import fact
from canvas.api_decorators import api_decorator
from canvas.metrics import Metrics
from canvas.models import Comment
from canvas.util import base36decode_or_404
from canvas.exceptions import ServiceError

urlpatterns = []
api = api_decorator(urlpatterns)

@api('invite_url', async=False)
def invite_url(request, comment_id=None):
    invite_url = urls.absolute_invite_url(request.user, comment_id=comment_id)
    invite_get_arg = urls.invite_get_arg(request.user, comment_id=comment_id)
    return {'invite_url': invite_url, 'invite_get_arg': invite_get_arg}

@api('invite_canvas_user_to_remix')
def invite_canvas_user_to_remix(request, username, comment_id):
    try:
        invitee = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        raise ServiceError("Cannot find user by that username")

    comment = get_object_or_404(Comment, id=comment_id)
    comment.remix_invites.invite(request.user, invitee)
    Metrics.invite_remixer.record(request, invitee=invitee.id, comment=comment_id)

@api('invite_canvas_user_to_complete_monster')
def invite_canvas_user_to_complete_monster(request, username, comment_id):
    try:
        invitee = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        raise ServiceError("Cannot find user by that username")

    comment = get_object_or_404(Comment, id=comment_id)
    comment.remix_invites.invite(request.user, invitee, type='monster')
    Metrics.invite_remixer.record(request, invitee=invitee.id, comment=comment_id, type='monster')

@api('all_mobile_monster_completion_invites')
def all_mobile_monster_completion_invites(request):
    return {'invites': request.user.remix_invites.mobile_monster_invites()}

