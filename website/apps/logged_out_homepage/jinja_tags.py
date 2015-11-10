from jinja2 import Markup, contextfunction

from canvas.templatetags.jinja_base import (global_tag, filter_tag, render_jinja_to_string,
                                            jinja_context_tag, update_context)

@global_tag
def render_homepage():
    from apps.logged_out_homepage.models import cached_homepage
    return Markup(cached_homepage())

