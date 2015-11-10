import datetime
import re
from urlparse import urlparse

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404

from apps.comment_hiding.redis_models import remove_hidden_comment_ids
from apps.features import feature_flags as features
from canvas import knobs
from canvas.cache_patterns import CachedCall
from canvas.models import get_mapping_id_from_short_id, Comment, Content, Category, ContentUrlMapping, Visibility
from canvas.redis_models import RateLimit
from canvas.templatetags.helpers import TemplateComment
from canvas.util import page_divide, paginate
from configuration import Config
from django.conf import settings

def check_rate_limit(request, username):
    rate_limit = 10
    return (not RateLimit('login:' + request.META['REMOTE_ADDR'], rate_limit).allowed()
            or not RateLimit('login:' + username, rate_limit).allowed())

def get_next(request):
    nexts = [request.GET.get('next'), request.POST.get('next'), request.META.get('HTTP_REFERER'), '/']
    for next_ in nexts:
        if not next_:
            continue

        url = urlparse(next_)

        invalid_nexts = ['search', 'reset', 'login', 'signup'] + settings.SHORT_CODES
        if re.match('^/(%s)' % '|'.join(invalid_nexts), url.path):
            continue

        # Prevent XSS via data: or javascript: URLs.
        if url.scheme and url.scheme not in ['http', 'https']:
            continue

        return next_

def top_url(category_name, year=None, month=None, day=None):
    url = '/x/%s/' % category_name
    if year:
        url += 'top/%s' % year
        if month:
            url += '/%s' % month
            if day:
                url += '/%s' % day
    return url

def top_timeperiod_urls(category_name):
    now = datetime.datetime.today()
    yesterday = now - datetime.timedelta(days=1)

    return [
        ('right now', top_url(category_name)),
        ('today', top_url(category_name, now.year, now.month, now.day)),
        ('yesterday', top_url(category_name, yesterday.year, yesterday.month, yesterday.day)),
        ('this month', top_url(category_name, now.year, now.month)),
        ('this year', top_url(category_name, now.year)),
    ]

def tile_render_options(sort, show_pins):
    return {
        'should_group_by_thread': sort == 'hot',
        'show_activity':          sort == 'pinned',
        'show_pins':              show_pins,
        'show_timestamp':         sort in ['pinned', 'active', 'new'],
    }

def wrap_comments(comment_list, cls=None):
    """ `comment_list` must be an iterable containing Comment instances. """
    if not cls:
        cls = CommentDetails
    return [cls(d) for d in CachedCall.multicall([cmt.details for cmt in comment_list])]

def redirect_trailing(view):
    """ Strip and redirect requests with certain trailing characters left by bad URL parsers. """
    IGNORE_CHARS = ",./"

    def wrapped(request, *args, **kwargs):
        if request.META['PATH_INFO'][-1] in IGNORE_CHARS:
            return HttpResponseRedirect(request.META['PATH_INFO'].rstrip(IGNORE_CHARS))
        return view(request, *args, **kwargs)
    return wrapped


class CommentViewData(object):
    def __init__(self, request, short_id, page=None, gotoreply=None):
        try:
            mapping_id = get_mapping_id_from_short_id(short_id)
        except ValueError:
            raise Http404

        self.request = request
        self.short_id = short_id
        self.page = page
        try:
            self.gotoreply = int(gotoreply)
        except TypeError:
            self.gotoreply = None

        _op_comment = get_object_or_404(Comment.published, id=mapping_id)

        # Get relevant OP data.
        _op_content = _op_comment.reply_content
        op_content = _op_content.details() if _op_content else None

        op_comment = _op_comment.details
        op_category = _op_comment.category.details() if _op_comment.category else Category.ALL.details()

        linked_comment = op_comment
        _linked_comment = _op_comment

        reply_ids = list(_op_comment.get_replies().values_list('id', flat=True))

        # Remove user-hidden comments.
        reply_ids = remove_hidden_comment_ids(request.user, reply_ids)

        # Pagination.
        explicit_page_view = bool(page)
        num_replies = len(reply_ids)
        if gotoreply is not None:
            gotoreply = int(gotoreply)
            try:
                page = page_divide(reply_ids.index(gotoreply)+1, knobs.COMMENTS_PER_PAGE)
                # If going to a reply on the last page, show 'current'.
                if reply_ids.index(gotoreply) + 1 >= num_replies - knobs.COMMENTS_PER_PAGE:
                    page = 'current'
            except ValueError:
                page = '1'

            # Grab the gotoreply's content for metadata
            _linked_comment = Comment.objects.get_or_none(id=gotoreply)
            if _linked_comment:
                linked_comment = _linked_comment.details
        elif page is None:
            page = '1'

        self.page_reply_ids, self.page_current, self.page_next, self.page_last = paginate(
                reply_ids, page=page, per_page=knobs.COMMENTS_PER_PAGE)
        self.page_penultimate = self.page_last - 1
        # Make it easy for Django to do a for loop on the page numbers.
        pages = xrange(1, self.page_last + 1)

        self.op_comment     = op_comment
        self._op_comment    = _op_comment
        self.op_content     = op_content
        self._op_content    = _op_content
        self.op_category    = op_category
        self.linked_comment = linked_comment
        self._linked_comment = _linked_comment
        self.page           = page
        self.pages          = pages
        self.per_page       = knobs.COMMENTS_PER_PAGE
        self.num_replies    = num_replies
        self.reply_ids      = reply_ids
        self.explicit_page_view = explicit_page_view
        self.is_author = request.user == _op_comment.author

    @property
    def recent_reply_ids(self):
        recent_reply_ids = []
        if self.page_current < self.page_last:
            if (self.page_current == self.page_penultimate):
                num_recent = min(3, len(self.reply_ids) % self.per_page)
            else:
                num_recent = 3
            recent_reply_ids = self.reply_ids[self.num_replies - num_recent:]
        return recent_reply_ids

    def top_reply_ids(self, force_show=False):
        """ `force_show` if True will return as many top reply IDs as we have. """
        num_top = min(self.num_replies / Config['posts_per_top_reply'], Config['maximum_top_replies'])
        min_top_replies = Config['minimum_top_replies']
        top_reply_ids = []
        # Avoid even hitting redis if we know we aren't going to use the data.
        if force_show or num_top >= min_top_replies and not self.explicit_page_view:
            top_reply_ids = self._op_comment.top_replies
            if force_show:
                top_reply_ids = top_reply_ids[:]
            else:
                top_reply_ids = top_reply_ids[:num_top]
            if not force_show and len(top_reply_ids) < min_top_replies:
                top_reply_ids = []

        top_reply_ids = remove_hidden_comment_ids(self.request.user, top_reply_ids)

        return top_reply_ids

    def get_text_reply_ids(self):
        """ Returns replies with text, sorted by id """
        if not self._linked_comment:
            return []
        replies = Comment.objects.filter(replied_comment=self._linked_comment)
        return [ids[0] for ids in replies.exclude(reply_text='').order_by('id').values_list('id')]

    def thread_context(self):
        top_reply_ids = self.top_reply_ids(force_show=features.thread_new(self.request))

        ctx = {
            'short_id': self.short_id,
            'page': self.page,
            'gotoreply': self.gotoreply,

            'viewer_is_staff': self.request.user.is_authenticated() and self.request.user.is_staff,
            'viewer_is_thread_author': self.is_author,
            'root': '/p/',

            'op_content': self.op_content,
            'op_category': self.op_category,
            'page': self.page,
            'per_page': self.per_page,
            'num_replies': self.num_replies,
            'reply_ids': self.reply_ids,
            'pages': self.pages,
            'page_reply_ids': self.page_reply_ids,
            'page_current': self.page_current,
            'page_next': self.page_next,
            'page_last': self.page_last,
            'page_penultimate': self.page_penultimate,
            'explicit_page_view': self.explicit_page_view,

            # Recent replies.
            'recent_reply_ids': self.recent_reply_ids,

            'top_reply_ids': top_reply_ids,
        }

        # Get all the replies in one query, then create the appropriate lists.
        _all_replies = Comment.visible.in_bulk(self.page_reply_ids + self.recent_reply_ids + top_reply_ids)
        _recent_replies = [_all_replies[cid] for cid in self.recent_reply_ids]
        _top_replies = filter(bool, [_all_replies.get(cid) for cid in top_reply_ids])
        _replies = [_all_replies[cid] for cid in self.page_reply_ids]

        replyable = [self._op_comment] + _replies + _recent_replies + _top_replies

        # Get all comment ids (ids so 0 queries) that any of these comments are replies to, that aren't in this
        # page, so we can render them on hover.
        replied_ids = ([reply.replied_comment_id for reply in replyable
                        if (reply.replied_comment_id
                            and reply.replied_comment_id not in [r.id for r in replyable])])

        ctx.update({
            'replied_ids': replied_ids,
            'replyable': replyable,
        })

        recent_replies = [reply.details for reply in _recent_replies]
        replies = [Comment.details_by_id(reply.id) for reply in _replies]
        replied = [Comment.details_by_id(cid) for cid in replied_ids]
        top_replies = [reply.details for reply in _top_replies]

        if self.request.user.is_authenticated():
            ctx['user_infos'] = {'pinned': self.request.user.id in self._op_comment.pins()}
            if self.request.user.is_staff:
                ctx['admin_infos'] = {self._op_comment.id: self._op_comment.admin_info}
                # For replies we only use the username, so grab those all in one query and put them in admin_infos.
                ctx['usernames'] = Comment.visible.filter(id__in=_all_replies.keys()).values('id', 'author__username')
                for reply_dict in ctx['usernames']:
                    ctx['admin_infos'][reply_dict['id']] = {'username': reply_dict['author__username']}

        ctx['replies_channel'] = self._op_comment.replies_channel.sync()

        # Get relevant sidebar data
        remix_of, reply_to = [], []
        # Remix of
        if self._op_content and self._op_content.remix_of:
            op_remix_of_caption = self._op_content.remix_of.first_caption
            if op_remix_of_caption:
                remix_of = [op_remix_of_caption.details]
            ctx['op_remix_of_caption'] = op_remix_of_caption
        # Reply to
        if self._op_comment.parent_comment and self._op_comment.parent_comment.is_visible():
            reply_to = [self._op_comment.parent_comment.details]

        (
            (op_comment,),
            (linked_comment,),
            remix_of,
            reply_to,
            replies,
            recent_replies,
            top_replies,
            replied,
        ) = CachedCall.many_multicall(
            [self.op_comment],
            [self.linked_comment],
            remix_of,
            reply_to,
            replies,
            recent_replies,
            top_replies,
            replied,
        )

        op_comment.is_my_post = bool(self._op_comment.author == self.request.user)
        op_comment.moderated = op_comment.visibility not in Visibility.public_choices

        linked_comment = TemplateComment(linked_comment, is_op=(linked_comment.id == op_comment.id),
                                        request=self.request, title=op_comment.title)

        if self.page_current == 1 and op_comment.has_content():
            first_comment_with_content = op_comment
        else:
            first_comment_with_content = None
            for reply in replies:
                if reply.has_content():
                    first_comment_with_content = reply
                    break

        last_comment_with_content = None
        for reply in reversed(replies):
            if reply.has_content():
                last_comment_with_content = reply
                break

        comment_to_expand = first_comment_with_content
        if self.gotoreply:
            comment_to_expand = linked_comment

        ctx.update({
            'op_comment': op_comment,
            'linked_comment': linked_comment,
            'remix_of': remix_of,
            'reply_to': reply_to,
            'replies': replies,
            'recent_replies': recent_replies,
            'top_replies': top_replies,
            'top_remixes': [reply for reply in top_replies if reply.has_content()],
            'replied': replied,

            'linked_comment': linked_comment,
            'fb_metadata': linked_comment.shareable_metadata(),
            'large_thread_view': len(replies) >= 50,
            'title': getattr(op_comment, 'title', None),

            'first_comment_with_content': first_comment_with_content,
            'last_comment_with_content': last_comment_with_content,
            'comment_to_expand': comment_to_expand,
        })

        return ctx

