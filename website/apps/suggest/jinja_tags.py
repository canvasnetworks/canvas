import random
import re
from time import time

from django.utils.safestring import mark_safe
from jinja2 import Markup

from apps.suggest.models import get_suggested_tags, get_most_stickered_unfollowed_users
from canvas import template
from canvas.cache_patterns import CachedCall
from canvas.templatetags.jinja_base import (global_tag, filter_tag, render_jinja_to_string,
                                            jinja_context_tag, update_context)

register = template.Library()

chrome = re.compile('chrome', re.I)

@jinja_context_tag
def suggestion_widget(context, type=None):
    request = context['request']
    browser = request.META['HTTP_USER_AGENT'] if 'HTTP_USER_AGENT' in request.META else ''
    user = request.user

    tags = get_suggested_tags(user)()
    users = get_most_stickered_unfollowed_users(user)()

    has_tags = len(tags) > 0
    has_users = len(users) > 0
    using_chrome = chrome.search(browser) is not None

    def get_type():
        types = ['invite']
        if has_users: types += ['people']
        if has_tags: types += ['tags']
        if using_chrome: types += ['chrome']
        return random.choice(types)

    try:
        ttype = get_type()
    except IndexError:
        return Markup('')

    if ttype == 'tags':
        ctx = { 'tags': tags, 'type': ttype }
        return Markup(render_jinja_to_string('suggest/suggest_tags_widget.html',
            update_context(context, ctx)))

    elif ttype == 'people':
        ctx = { 'users': users, 'type': ttype }
        return Markup(render_jinja_to_string('suggest/suggest_people_widget.html',
            update_context(context, ctx)))

    elif ttype == 'invite':
        ctx = { 'type': ttype }
        return Markup(render_jinja_to_string('suggest/suggest_invite_widget.html',
            update_context(context, ctx)))

    elif ttype == 'chrome':
        ctx = { 'type': ttype }
        return Markup(render_jinja_to_string('suggest/suggest_extension_widget.html',
            update_context(context, ctx)))

