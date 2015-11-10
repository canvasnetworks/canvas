from jinja2 import Markup, contextfunction

from canvas.templatetags.jinja_base import (global_tag, filter_tag, render_jinja_to_string,
                                            jinja_context_tag, update_context)

@jinja_context_tag
def quest_preview(context, quest_preview, admin_view=False, already_saved=False):
    ctx = {
        'quest_preview': quest_preview,
        'admin_view': admin_view,
        'show_curation_info': admin_view and bool(getattr(quest_preview, 'curator', None)),
        'already_saved': already_saved,
    }

    return Markup(render_jinja_to_string('quests/quest_preview.html', update_context(context, ctx)))

