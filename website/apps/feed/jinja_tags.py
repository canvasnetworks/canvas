from jinja2 import Markup, contextfunction

from apps.features import feature_flags as features
from canvas.templatetags.jinja_base import jinja_context_tag, render_jinja_to_string

@jinja_context_tag
def feed_item(context, item):
    request = context['request']

    ctx = {
        'item': item,
        'comment': item['comment'],
        'request': request,
        'viewer_sticker': item['viewer_sticker'],
        'lazy_content': features.lazy_content(request),
    }
    return Markup(render_jinja_to_string('feed/_feed_item.html', ctx))

