from jinja2 import Markup, contextfunction

from canvas.templatetags.jinja_base import (global_tag, filter_tag, render_jinja_to_string,
                                            jinja_context_tag, update_context)

@global_tag
def activity_stream_item(activity, viewer):
    ctx = {
        'activity': activity,
        'viewer': viewer,
    }
    return Markup(render_jinja_to_string(u'activity/types/{0}.html'.format(activity.TYPE), ctx))

