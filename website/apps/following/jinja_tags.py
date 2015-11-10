from jinja2 import Markup, contextfunction

from canvas.templatetags.jinja_base import jinja_context_tag

@jinja_context_tag
def viewer_is_following(context, user):
    viewer = context['request'].user
    return viewer.is_following(user)

