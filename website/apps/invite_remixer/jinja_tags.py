import uuid

from django.utils.safestring import mark_safe
from jinja2 import Markup, contextfunction

from canvas import template
from apps.invite_remixer.urls import absolute_invite_url
from canvas.templatetags.jinja_base import global_tag, render_jinja_to_string
register = template.Library()

@register.simple_tag
@global_tag
def invite_remixers(viewer, comment):
    invite_url = absolute_invite_url(viewer, comment_id=comment.id)
    context = {
        'comment'   : comment,
        'uuid'      : uuid.uuid4(),
        'invite_url': invite_url,
    }
    return mark_safe(Markup(render_jinja_to_string('comment/invite_remixers.html', context)))

