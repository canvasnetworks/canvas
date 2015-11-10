from apps.invite_remixer.jinja_tags import invite_remixers
from canvas import template

register = template.Library()

register.simple_tag(invite_remixers)

