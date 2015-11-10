from jinja2 import Markup
from canvas.templatetags.jinja_base import (global_tag, filter_tag, render_jinja_to_string,
                                            jinja_context_tag, update_context)

@jinja_context_tag
def submit_quest_form(context):
    ctx = {}
    return Markup(render_jinja_to_string('submit_quest/_submit_quest_form.html', update_context(context, ctx)))

