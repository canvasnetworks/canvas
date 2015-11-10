# -*- coding: utf-8 -*-

import datetime
import math
import os.path
import re
import time
import urllib
import urlparse
import uuid as uuid_

import bleach
from django.contrib.humanize.templatetags import humanize
from django.template import defaultfilters
from django.utils.html import escape, strip_tags
from django.utils.safestring import mark_safe
from jinja2 import Markup, contextfunction

from apps.activity.redis_models import DailyFreeStickersActivity
from apps.activity.jinja_tags import activity_stream_item
from apps.canvas_auth.models import User
from apps.tags.models import get_tracked_tags
from canvas import stickers, knobs, util, economy, template
from canvas.cache_patterns import CachedCall
from canvas.details_models import CommentDetails, ContentDetails
from canvas.models import Category, Comment, Visibility, SpecialCategory, CommentFlag
from canvas.templatetags.jinja_base import (global_tag, filter_tag, render_jinja_to_string,
                                            jinja_context_tag, update_context)
from canvas.templatetags.helpers import TemplateComment
from canvas.view_helpers import top_timeperiod_urls
from services import Services
from django.conf import settings

register = template.Library()

DEFAULT_AVATAR_COUNT = 6

@filter_tag
def pluralize(condition, argstr=",s"):
    one, many = argstr.split(',')
    try:
        condition = len(condition)
    except TypeError:
        pass
    return one if condition == 1 else many

@global_tag
def comment_is_pinned(comment_details, viewer):
    """
    `viewer` should be request.user - the user viewing the comment.

    Returns "pinned" if pinned, else None.
    """
    if not isinstance(comment_details, CommentDetails):
        comment_details = CommentDetails(comment_details)
    return 'pinned' if comment_details.is_pinned(viewer) else None

@global_tag
def timestamp():
    return Markup(str(time.time()))

##############################
# Used for content dimensions.
def _wh(content_data, ratio):
    return dict((dimension, int(content_data[dimension] / ratio),)
                for dimension in ['width', 'height'])

def _fit_inside(fit_w, fit_h, content_data):
    rw = float(content_data['width'])  / fit_w
    rh = content_data['height'] / fit_h
    ratio = max(1, rw, rh)
    return _wh(content_data, ratio)

def _fit_height(fit_h, content_data):
    ratio = float(content_data['height']) / fit_h
    return _wh(content_data, ratio)

def _fit_width(fit_w, content_data):
    ratio = float(content_data['width']) / fit_w
    return _wh(content_data, ratio)

def _size_attrs(content_data, fit_w=None, fit_h=None):
    if fit_w is None and fit_h is None:
        # Do nothing
        return {'width': content_data['width'], 'height': content_data['height']}
    elif fit_w is None:
        return _fit_height(fit_h, content_data)
    elif fit_h is None:
        return _fit_width(fit_w, content_data)
    else:
        return _fit_inside(fit_w, fit_h, content_data)

###############################
# For sizing content assuming
# a container to catch overflow
# Must supply fit_w and fit_h
###############################
def _size_attrs_overflow(content_data, fit_w, fit_h):
    rw = float(content_data['width'])  / fit_w
    rh = float(content_data['height']) / fit_h
    ratio = min(rw, rh)
    return _wh(content_data, ratio)

@global_tag
def content_fit(comment_or_content, fit_w, fit_h, *image_types, **kwargs):
    """
    Renders an html snippet (includes an img tag) for `content_details`.

    `image_types`:
        Could be "column", "stream" for example. Image types are tried in order,
        and the first one that exists for an image is used.
    """
    lazy = kwargs.pop('lazy', False)

    if hasattr(comment_or_content, 'reply_content'):
        details = comment_or_content.reply_content
        visibility = comment_or_content.visibility
    else:
        details = comment_or_content
        visibility = True
    if not isinstance(details, ContentDetails):
        details = ContentDetails(details)

    for image_type in image_types:
        try:
            data = details[image_type]
            url = details.get_absolute_url_for_image_type(image_type)
            wh = _size_attrs(data, fit_w, fit_h)
        except (AttributeError, KeyError, IndexError,):
            # For now, we just show blank images when the content is missing, until we fix the thumbnailer.
            url = str(type)
            wh = {'width': 100, 'height': 100}
        else:
            break
    attribs = {
        'url': url,
        'width': wh['width'],
        'height': wh['height'],
        # @TODO: Note the @comment here is a dict. The current version of the details does not store
        # is_visbile. Hence, we're duplicating the is_visibile code here.
        #TODO just wrap with CommentDetails and call is_visible on it.
        'alt': escape(getattr(details, 'remix_text', None) if visibility == Visibility.PUBLIC else ""),
        'classes': '',
        'extra': '',
    }

    if lazy:
        attribs.update({
            'url': '/static/img/0.gif',
            'extra': 'data-original="{}"'.format(url),
            'classes': 'lazy',
        })

    tag = u'<img class="ugc_img {classes}" src="{url}" width="{width}" height="{height}" alt="{alt}" {extra}>'.format(**attribs)
    return Markup(tag)

@global_tag
def content(comment_or_content, *image_types, **kwargs):
    """
    Renders an html snippet (includes an img tag) for `content_details`.

    `image_types`:
        Could be "column", "stream" for example. Image types are tried in order,
        and the first one that exists for an image is used.
    """
    return content_fit(comment_or_content, None, None, *image_types, **kwargs)

def _avatar(url, size, fit_w, fit_h, username):
    wh = _size_attrs_overflow(size, fit_w, fit_h)
    return Markup("""
        <img class="user_avatar ugc_img" src="%(url)s" width="%(width)s" height="%(height)s" alt="%(alt)s">
        """ % {
            'url': url,
            'size_width': fit_w,
            'size_height': fit_h,
            'width': wh['width'],
            'height': wh['height'],
            'alt': username + "'s profile image",
    })

def _default_avatar_url(key):
    idx = int(key) % DEFAULT_AVATAR_COUNT
    return '/static/img/default_avatar_{}.png'.format(idx)

@global_tag
def avatar_url(user):
    """ DO NOT CALL THIS FOR ANONYMOUS POSTS. """
    key = 'column'
    avatar, = CachedCall.multicall([
        User.avatar_by_username(user.username),
    ])
    if key in avatar:
        url = avatar[key]['name']
    else:
        key = user.id if user.is_authenticated() else 0
        url = _default_avatar_url(key)
    return url

@global_tag
def header_avatar(username):
    return _square_avatar(username, 'tiny_square', 22, 22)

@global_tag
def tiny_avatar(username):
    return _square_avatar(username, 'tiny_square', 30, 30)

@global_tag
def small_avatar(username):
    return _square_avatar(username, 'small_square', 50, 50)

@global_tag
def big_avatar(username):
    return _square_avatar(username, 'medium_square', 150, 150)

def _square_avatar(username, image_type, width, height):
    avatar, = CachedCall.multicall([
        User.avatar_by_username(username),
    ])
    if image_type in avatar:
        url = avatar[image_type]['name']
        size = avatar[image_type]
    else:
        key = reduce(lambda acc, x: ord(x) + acc, username, 0)
        url = _default_avatar_url(key)
        size = {'width':width, 'height':height}

    return _avatar(url, size, width, height, username)


@global_tag
def content_size(content_details, image_type):
    data = content_details[image_type]
    try:
        wh = _size_attrs(data)
    except KeyError:
        wh = {'width': 0, 'height': 0}

    return wh

@global_tag
def mobile_tile(comment):
    return Markup(render_jinja_to_string("mobile/tile.html", {'comment': comment}))

def _relative_timestamp(timestamp):
    """ Only returns the humanized time delta, without the HTML which relative_timestamp adds. """
    now = Services.time.time()
    delta_s = now - timestamp

    units = ((60, 'a moment ago'),
             (60*60, 'minute'),
             (60*60*24, 'hour'),
             (60*60*24*7, 'day'),
             (60*60*24*30, 'week'),
             (60*60*24*365, 'month'),
             ('infinity', 'year'),)

    for index, t in enumerate(units):
        cutoff, unit = t
        if cutoff == 'infinity' or delta_s < cutoff:
            if index == 0:
                return unit
            val = int(delta_s // units[index - 1][0]) # Divide by the previous cutoff.
            return str(val) + ' ' + unit + pluralize(val) + ' ago'

@global_tag
def relative_timestamp(timestamp):
    human_time = _relative_timestamp(timestamp)
    return Markup(u'<span class="rel-timestamp" data-timestamp="{0}">{1}</span>'.format(timestamp, human_time))


_GROUP_LINK_PATTERN = re.compile(r'((?:^|\s))\#(\w{3,})')
_SAFE_URI_CHARS = '~@#$&()*!+=:;,.?/\'' # Equivalent to javascript's encodeURI

@global_tag
def ugc_text(text, max_length=knobs.POST_TEXT_TRUNCATION_LENGTH,
             should_oembed=False, linkify=True, truncation_markup=u'…'):
    # When using this, you can't specify keyword arguments (until Django 1.3), use them as positional args.
    # They serve only to provide defaults.
    def _linkify(text, href):
        safe_href = urllib.quote(unicode(href).encode('utf-8'), safe=_SAFE_URI_CHARS)
        attrs = {
            'href': safe_href,
            'title': safe_href,
            'target': '_blank',
        }
        return u'<a {0}>{1}</a>'.format(u' '.join(u'{0}="{1}"'.format(key, val) for key,val in attrs.iteritems()),
                                        text)

    def linkify_group(match):
        #TODO make group 404s show a page asking if you want to create the group.
        group = match.group(2)
        return match.group(1) + _linkify(u'#' + group, u'/x/' + group)

    # Remove <tag> <shenanigans/>
    text = strip_tags(text)

    # Escape any HTML entities.
    text = escape(text)

    if len(text) > max_length:
        #TODO split on a word.
        text = text[:max_length] + truncation_markup

    # Enter means newline bitch
    text = text.replace('\n', '<br>\n')

    # Linkify links.
    if linkify:
        text = bleach.linkify(text, nofollow=True, target='_blank')

        # Replace all #foobar forms with http://example.com/x/foobar,
        # but not '#', '#1', '#1-ocle', et cetera.
        text = _GROUP_LINK_PATTERN.sub(linkify_group, text)

        #TODO linkify @names

    # Escape Django template tokens for jinja_adapter funkiness. Nasty. Delete once we move all over to Jinja.
    text = text.replace('{{', '&#123;' * 2)
    text = text.replace('}}', '&#125;' * 2)
    text = text.replace('{%', '&#123;%')
    text = text.replace('%}', '%&#125;')
    text = text.replace('{#', '&#123;#')
    text = text.replace('#}', '#&#125;')

    ugc_text_id = 'ugc_text_' + uuid_.uuid4().hex

    span_classes = 'ugc_text'
    return Markup(u'<span id="{0}" class="{1}">{2}</span>'.format(ugc_text_id, span_classes, text))

@filter_tag
@global_tag
def to_json(things):
    """
    If the model/object defines a "to_client" then call it first.

    This way objects can implement the "to_client" interface to return a dictionary representation of themselves to
    be serialized as json.
    """
    return util.js_safety(util.client_dumps(things), django=False)

@global_tag
def uuid():
    return uuid_.uuid4().hex

@filter_tag
def to_escaped_json(things):
    return util.js_safety(util.client_dumps(things), django=False, escape_html=True)

@filter_tag
def to_escaped_comment_details_json(comment_details):
    """ Escapes Django template language tokens too. """
    old_text = comment_details.reply_text
    text = old_text.replace('{{', '\\u007b' * 2).replace('}}', '\\u007d' * 2)
    text = text.replace('{%', '\\u007b%').replace('%}', '%\\u007d')
    text = text.replace('{#', '\\u007b#').replace('#}', '#\\u007d')
    comment_details.reply_text = text
    ret = to_escaped_json(comment_details)
    comment_details.reply_text = old_text
    return ret


def image_tile(context, tile, render_options, nav_category, template='comment/explore_tile.html'):
    request = context['request']
    user = request.user

    if not hasattr(tile, 'comment'):
        raise TypeError("A tile should be an instance of TileDetails or LastReplyTileDetails; something that "
                        "has a .comment. Received a %s" % type(tile))
    comment = tile.comment

    new_activity = False
    if render_options.get('show_activity') and render_options.get('show_pins') and comment.last_reply_time:
        pinned_lastviewed = user.kv.pinned_lastviewed.get() or 1303426306. # When we launched pinned.
        new_activity = pinned_lastviewed < float(comment.last_reply_time)

    def nav_aware(url):
        default_category = Category.get_default(request.user).details()
        # If we don't have a nav_category (user / about page) it should be the default for this user.
        _nav_category = nav_category or default_category
        if _nav_category['name'] != default_category['name']:
            url += "?nav=%s" % _nav_category['name']
        return url

    #TODO probably change TemplateComment to TemplateTile instead.
    # This is weird - we pass tile to the template too, but tile.comment != comment now.
    comment = TemplateComment(tile.comment, request_context=context)

    float_sticker = getattr(comment, 'reply_content_id', None) and comment.reply_text

    sticky_text = getattr(tile, 'text', None)

    return render_jinja_to_string(template, locals())

@register.context_tag
def render_jinja(context, jinja_template_name):
    return render_jinja_to_string(jinja_template_name, context)

@jinja_context_tag
def disposition_tile(context, tile_renderer, tile, render_options={}, nav_category={}):
    from apps.monster.jinja_tags import monster_image_tile

    tile_renderer = {
        'monster_image_tiles'   : monster_image_tile,
        'explore_tiles'         : explore_tile,
    }[tile_renderer]
    render_options['image_type'] = 'explore_column'
    return tile_renderer(context, tile, render_options, nav_category)

@register.context_tag
def explore_tiles(context, tiles, render_options, nav_category={}):
    return Markup(mark_safe(u''.join(explore_tile(context, tile) for tile in tiles)))

@jinja_context_tag
def explore_tile(context, tile, render_options={}, nav_category={}):
    comment = TemplateComment(tile.comment, request_context=context)
    sticky_text = getattr(tile, 'text', None)
    viewer_sticker = tile.viewer_sticker
    viewer = context['request'].user
    remixer_count = comment.thread.author_count
    return Markup(render_jinja_to_string('/comment/explore_tile.html', locals()))

@jinja_context_tag
def jinja_thread_reply(context, comment_details, template='threads/reply.html', is_expanded=False):
    opts = {
        'reply': TemplateComment(comment_details, request_context=context),
        'is_expanded': is_expanded,
    }
    return Markup(render_jinja_to_string(template, update_context(context, opts)))

@register.context_tag
def jinja_thread_comment(context, comment_details, fullsize):
    context.update({
        'comment'   : TemplateComment(comment_details, request_context=context, is_op=bool(fullsize)),
        'fullsize'  : fullsize,
        'show_tags' : True,
    })
    return render_jinja_to_string('comment/jinja_thread_comment.html', context)

@register.context_tag
def jinja_thread_comments(context, comments_details):
    # This exists because apparently it is non-trivially faster than iterating in a Django template.
    #
    # (It was actually for clarity and simplicity - having a template file just to call a tag in an iterator
    # feels heavier and more indirect than needed. There may be a perf benefit as well, but that wasn't
    # my primary motivation. --alex)
    return mark_safe(u''.join((jinja_thread_comment(context, details, 0) for details in comments_details)))

@register.context_tag
@jinja_context_tag
def thread_pagination(context):
    return Markup(mark_safe(render_jinja_to_string('threads/pagination.html', context)))

@jinja_context_tag
def jinja_giant_image_tile(context, tile):
    render_options = {
        'image_type': "giant",
        'image_tile_classes': "giant",
        'autoplay': True,
        'show_author': True,
        'show_caption': True,
        'show_stickers': True,
        'show_remix': True,
    }
    return Markup(image_tile(context, tile, render_options, 0, 'comment/simplified_image_tile.html'))

@jinja_context_tag
def jinja_giant_monster_image_tile(context, tile):
    render_options = {
        'image_type': "giant",
        'image_tile_classes': "giant",
        'autoplay': True,
        'show_author': False,
        'show_caption': False,
        'show_stickers': False,
        'show_remix': False,
    }
    return Markup(image_tile(context, tile, render_options, 0, 'comment/simplified_image_tile.html'))


@register.context_tag
def jinja_column_image_tile(context, tile):
    render_options = {
        'image_type': "column",
        'show_stickers': True,
        'show_remix': True,
    }
    return image_tile(context, tile, render_options, 0, 'comment/simplified_image_tile.html')

@register.context_tag
def jinja_small_image_tile(context, tile):
    render_options = {
        'image_type': 'thumbnail',
        'image_tile_classes': 'small',
        'disable_animate_in_place': True,
    }
    return image_tile(context, tile, render_options, 0, 'comment/simplified_image_tile.html')

@register.context_tag
def jinja_share_page_tile(context, tile):
    if settings.PROJECT == 'canvas':
        image_type = 'small_column'
    elif settings.PROJECT == 'drawquest':
        image_type = 'activity'

    render_options = {
        'image_type'    : image_type,
        'autoplay'      : False,
        'show_author'   : False,
        'show_caption'  : False,
        'show_stickers' : False,
        'show_remix'    : False,
    }
    return image_tile(context, tile, render_options, 0, 'comment/share_page_tile.html')

@jinja_context_tag
def jinja_thread_page_tile(context, tile):
    if settings.PROJECT == 'canvas':
        image_type = 'small_column'
    elif settings.PROJECT == 'drawquest':
        image_type = 'activity'

    render_options = {
        'image_type': image_type,
        'autoplay': False,
        'show_author': False,
        'show_caption': False,
        'show_stickers': False,
        'show_remix': False,
    }
    return Markup(image_tile(context, tile, render_options, 0, 'comment/simplified_image_tile.html'))

@register.context_tag
def jinja_popup_image_tile(context, tile):
    render_options = {
        'image_type'    : 'stream',
        'autoplay'      : False,
        'show_author'   : False,
        'show_caption'  : False,
        'show_stickers' : True,
        'show_remix'    : False,
    }
    return image_tile(context, tile, render_options, 0)

@register.context_tag
def jinja_small_image_tiles(context, tiles):
    return mark_safe(u''.join((jinja_small_image_tile(context, tile) for tile in tiles)))

@register.context_tag
def jinja_share_page_tiles(context, tiles):
    return mark_safe(u''.join((jinja_share_page_tile(context, tile) for tile in tiles)))

@register.context_tag
def jinja_site_header(context):
    # Group list is current category + following + top, without duplicates.
    request = context['request']
    user = request.user

    if user.is_authenticated():
        economy.grant_daily_free_stickers(request.user)
        template_name = 'header/logged_in.html'
    else:
        template_name = 'header/logged_out.html'

    return mark_safe(render_jinja_to_string(template_name, context))

@register.simple_tag
def daily_sticker_activity_json(user):
    activity = None
    if user.kv.has_unseen_daily_free_stickers.get():
        user.kv.has_unseen_daily_free_stickers.delete()
        activity = DailyFreeStickersActivity({
            'reward_stickers': knobs.DAILY_FREE_STICKERS,
        }, actor=user)
        activity = activity_stream_item(activity, user)
    return util.js_safety(util.client_dumps(activity))

@register.context_tag
def jinja_sidebar(context):
    followed_tags = context.get('followed_tags')
    current_tag = context['nav_tag']

    def which_nav(path):
        if path.startswith('/feed') or path == '/':
            return 'feed'
        elif path.startswith('/monster'):
            return 'monster'
        elif path.startswith('/x/everything'):
            return 'explore'
        return ''

    context.update({
        'current_nav': which_nav(context['request'].path),
    })

    if followed_tags is not None:
        context['tracked_tags'] = get_tracked_tags(context['request'].user, followed_tags, current_tag)

    return mark_safe(render_jinja_to_string('sidebar/sidebar.html', context))

@register.context_tag
def jinja_sticker_pack(context):
    context['store_items']= stickers.get_purchasable(context['request'].user)
    return mark_safe(render_jinja_to_string('sticker_pack/sticker_pack.html', context))

@jinja_context_tag
def jinja_thread_preview(context, thread, admin_view=False):
    ctx = {
        'thread': thread,
        'admin_view': admin_view,
        'show_curation_info': admin_view and bool(getattr(thread, 'curator', None)),
    }
    return Markup(render_jinja_to_string('logged_out_homepage/thread_preview.html', update_context(context, ctx)))

@jinja_context_tag
def jinja_sticky_thread_preview(context, thread, admin_view=False):
    ctx = {
        'thread': thread,
        'admin_view': admin_view,
        'show_curation_info': admin_view and bool(getattr(thread, 'curator', None)),
    }
    return Markup(render_jinja_to_string('sticky_threads/thread_preview.html', update_context(context, ctx)))

@jinja_context_tag
def jinja_thread_preview(context, thread, admin_view=False):
    ctx = {
        'thread': thread,
        'admin_view': admin_view,
        'show_curation_info': admin_view and bool(getattr(thread, 'curator', None)),
    }
    return Markup(render_jinja_to_string('logged_out_homepage/thread_preview.html', update_context(context, ctx)))

@global_tag
def news_img(url):
    token = os.path.basename(urlparse.urlparse(url).path)
    if "reply" in url:
        post_id = int(token)
    else:
        post_id = util.base36decode_or_404(token)

    try:
        comment_details = Comment.details_by_id(post_id)()
        img_url = comment_details.reply_content['thumbnail']['name']
        url = comment_details.url
    except (KeyError, Comment.DoesNotExist):
        img_url = ""

    return "<a href='%s'><img class='content' src='%s'></a>" % (url, img_url)

@global_tag
def get_img_url(url, image_size="thumbnail"):
    token = os.path.basename(urlparse.urlparse(url).path)
    if "reply" in url:
        post_id = int(token)
    else:
        post_id = util.base36decode_or_404(token)

    try:
        img_url = Comment.details_by_id(post_id)().reply_content[image_size]['name']
    except (KeyError, Comment.DoesNotExist):
        img_url = ""
    return img_url

@global_tag
def sticker_image(sticker, image_size="small", classes=""):
    """ `sticker` can be a sticker name or ID. """
    sticker = stickers.get(sticker)
    return Markup(u'<span class="sticker_container {0} {1} {2}" data-type_id="{3}"></span>'.format(image_size, sticker.name, classes, sticker.type_id))

@global_tag
def compressed(type, name):
    from apps.mobile.signals import compressed_files
    path = compressed_files.get(type, name)
    if path is None:
        raise Exception("CSS file not found for " + name)
    if type == 'js':
        return Markup(u'<script src="{0}"></script>'.format(path))
    elif type == 'css':
        return Markup(u'<link rel="stylesheet" href="{0}">'.format(path))
    else:
        raise Exception("Unknown typo %r" % type)

@filter_tag
def naturalday(value):
    return humanize.naturalday(value, "F j")

@filter_tag
def timestamp_to_datetime(ts):
    return datetime.datetime.fromtimestamp(ts)

@global_tag
@register.simple_tag
def og_type(ttype='post'):
    return "{}:{}".format(settings.FACEBOOK_NAMESPACE, ttype)

@global_tag
def share_comment(comment):
    return Markup(render_jinja_to_string("share/_share_comment.html", {'comment': comment}))
