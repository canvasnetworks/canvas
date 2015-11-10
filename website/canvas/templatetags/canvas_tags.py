# -*- coding: utf-8 -*-

import bleach
import datetime
import os.path
import re
import time
import urllib
import urlparse
import uuid

from django import template
from django.conf import settings
from django.template.defaultfilters import pluralize, yesno
from django.utils.functional import memoize
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from canvas import util, economy, stickers
from canvas.models import SpecialCategory, Category, Comment, Visibility, CommentFlag
from services import Services
from django.conf import settings

register = template.Library()

@register.filter
def get_value(dict_object, key):
    """ Looks things up in a dictionary. """
    if not dict_object:
        return None
    return dict_object.get(key, None)

@register.filter
def js_bool(value):
    """ Similar to yesno:"true,false,false" """
    if not value:
        return "false"
    return "true"

# Encode all '<'s as \u003c and '>'s as \u003e to prevent <!-- ... --> and </script> from breaking our pages
@register.filter
def to_json(things):
    """ 
    If the model/object defines a "to_client" then call it first.
    This way objects can implement the "to_client" interface to return a dictionary
    representation of themselves to be serialized as json.
    """
    return util.js_safety(util.client_dumps(things))

@register.filter
def ellipsis_after(text, length):
    """ Truncates text and adds ellipses at the end. Does not truncate words in the middle. """
    if not text or len(text) <= length:
        return text
    else:
        return text[:length].rsplit(' ', 1)[0]+u"\u2026"

@register.filter
def is_in_experiment(request, experiment_name):
    try:
        experiment_name, branch = experiment_name.split(',')
    except ValueError:
        branch = 'experimental'
    return request.experiments.is_in(experiment_name, branch_name=branch)

@register.filter
def get_labs(kv, key):
    """ We need this filter because lab values have semicolons in them. """
    return int(kv.get("labs:"+str(key), 0))

@register.simple_tag
def news_img(url):
    token = os.path.basename(urlparse.urlparse(url).path)
    if "reply" in url:
        post_id = int(token)
    else:
        post_id = util.base36decode_or_404(token)
        
    img_url = Comment.details_by_id(post_id)()['reply_content']['thumbnail']['name']
    return "<a href='%s'><img src='http://example.com/ugc/%s'></a>" % (url, img_url)

@register.filter
def sub_header(subheader):
    substitutions = {
        "hot": "popular",
        "active": "new"
    }
    return substitutions.get(str(subheader).lower(), None) or subheader

@register.inclusion_tag('widget/stickers.django.html', takes_context=True)
def sticker_palette(context):
    context['store_items']= stickers.get_purchasable(context['request'].user)
    return context

@register.simple_tag
def static_url(relative_url):
    return "/static/%s" % str(relative_url)
    
@register.filter
def pretty_unixtime(t):
    return time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(t))

@register.simple_tag
def raw_html(path):
    def get_content(path):
        import os.path
        basedir = os.path.join(settings.PROJECT_PATH, 'templates') #TODO this sucks.
        f = file(os.path.join(basedir, path), 'r')
        try:
            content = f.read()
        finally:
            f.close()
        return mark_safe(content)

    if settings.MEMOIZE_RAW_HTML:
        return memoize(get_content, {}, 1)(path)
    return get_content(path)

@register.simple_tag
def empty_gif():
    return "/static/img/0.gif"

class CenterNode(template.Node):
    start = """<table width="100%" height="100%" border="0" cellspacing="0" cellpadding="0" style="position: absolute;"><tr><td align="center" valign="middle" style="text-align: center;">"""
    end = """</td></tr></table>"""
    
    def __init__(self, nodelist):
        self.nodelist = nodelist
        
    def render(self, context):
        output = self.nodelist.render(context)
        return self.start + output + self.end
    
@register.tag
def center(parser, token):
    nodelist = parser.parse(('endcenter',))
    parser.delete_first_token()
    return CenterNode(nodelist)

