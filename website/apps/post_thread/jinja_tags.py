from jinja2 import Markup
from canvas.templatetags.jinja_base import (global_tag, filter_tag, render_jinja_to_string,
                                            jinja_context_tag, update_context)

@jinja_context_tag
def post_thread_form(context, show_start_options=True):
    ctx = {
        'show_start_options': bool(show_start_options),
    }
    return Markup(render_jinja_to_string('post_thread/_post_thread_form.html', update_context(context, ctx)))

