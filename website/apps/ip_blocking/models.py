from datetime import date

from django.db.models import *

from apps.canvas_auth.models import User
from canvas.models import BaseCanvasModel
from canvas.util import UnixTimestampField
from services import Services


class IPBlock(BaseCanvasModel):
    ip = IPAddressField(blank=False, unique=True, db_index=True)
    moderator = ForeignKey(User, null=True, limit_choices_to={'is_staff': True})
    timestamp = UnixTimestampField()
    note = TextField()

    class Meta:
        verbose_name_plural = 'IP blocks'
        verbose_name = 'IP block'

def is_ip_blocked(request):
    """ Returns whether the given request's IP is blocked. """
    try:
        IPBlock.objects.get(ip=request.META['REMOTE_ADDR'])
    except IPBlock.DoesNotExist:
        return False
    else:
        return True

