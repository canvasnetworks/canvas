from django.utils.safestring import mark_safe
from jinja2 import Markup

from canvas import template
from canvas.templatetags.helpers import TemplateComment
from canvas.templatetags.jinja_base import (global_tag, filter_tag, render_jinja_to_string,
                                            jinja_context_tag, update_context)

register = template.Library()

@register.context_tag
def monster_image_tiles(context, tiles, render_options={}, nav_category={}):
    render_options['image_type'] = 'explore_column'
    rendered = [monster_image_tile(context, tile, render_options, nav_category, True) for tile in tiles]
    return mark_safe(u''.join(rendered))

@jinja_context_tag
def monster_image_tile(context, tile, render_options={}, nav_category={}, display_monster=True):
    request = context['request']
    user = request.user

    viewer_sticker = tile.viewer_sticker

    top = TemplateComment(tile.top, request_context=context)
    bottom = TemplateComment(tile.bottom, request_context=context)

    float_sticker = getattr(top, 'reply_content_id', None) and top.reply_text

    template = 'monster/monster_explore_tile.html'

    return Markup(render_jinja_to_string(template, locals()))
