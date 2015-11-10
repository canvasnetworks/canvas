from django.conf.urls.defaults import *
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404

from apps.canvas_auth.models import User, AnonymousUser
from canvas import util
from canvas.url_util import re_slug
import canvas.models

urlpatterns = patterns('apps.invite_remixer.views',
    url(re_slug('invite_id') + '/?$', 'invite', name='invite_url'),
)

DELIMITER = '-'

def invite_id(user, comment_id=None):
    keys = [user.id]
    if comment_id is not None:
        keys.append(comment_id)

    return DELIMITER.join([util.base36encode(e) for e in keys])

def invite_get_arg(*args, **kwargs):
    return 'invite=' + invite_id(*args, **kwargs)

def absolute_invite_url(*args, **kwargs):
    return 'http://example.com' + invite_url(*args, **kwargs)

def invite_url(*args, **kwargs):
    """
    Returns an invite URL to use for thread pages or /. Unique to user, thread, and channel.

    If `comment` is None, it will share the homepage.

    Format for thread invites:
        USER_ID-COMMENT_ID

    Format for homepage invites:
        USER_ID
    """
    id_ = invite_id(*args, **kwargs)
    return reverse('invite_url', kwargs={'invite_id': id_})

def reverse_invite_id(invite_id):
    """
    `invite_id` is the slug portion of an invite URL.

    Returns a pair of `(user, url,)`
    """
    keys = invite_id.split(DELIMITER)
    keys = [util.base36decode(e) for e in keys]

    user_id = keys.pop(0)
    user = get_object_or_404(User, pk=user_id)

    try:
        comment_id = keys.pop(0)
        comment = get_object_or_404(canvas.models.Comment, pk=comment_id)
        url = comment.get_absolute_url()
    except IndexError:
        url = '/'

    return (user, url,)

