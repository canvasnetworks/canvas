from django.http import Http404

from apps.client_details.models import ClientDetailsBase
from apps.public_api.util import long_id, short_id
from apps.threads.details_models import ThreadDetails
from canvas import stickers, util, browse
from canvas.cache_patterns import CachedCall
from canvas.details_models import ContentDetails, CommentDetails, ContentDetails
from canvas.models import Comment, User, AnonymousUser, Category
from canvas.redis_models import RealtimeChannel
from django.conf import settings

class _PublicAPIObjectMixin(object):
    TO_CLIENT_WHITELIST = [
        'api_url',
    ]


class PublicAPIContentDetails(ClientDetailsBase):
    TO_CLIENT_WHITELIST = [
        ('timestamp', False, 'int_timestamp'),
        'remix_text',
        ('original', False, 'public_original'),
        ('remix_of_giant_url', True, 'public_remix_of_giant_url'),
        ('small_square', True, 'public_small_square'),
        ('thumbnail', True, 'public_thumbnail'),
        ('stream', True, 'public_stream'),
        ('small_column', True, 'public_small_column'),
        ('column', True, 'public_column'),
        ('giant', True, 'public_giant'),
        ('mobile', True, 'public_mobile'),
        ('footer', True, 'public_footer'),
    ]

    def int_timestamp(self):
        return int(self.timestamp)

    def url(self, content):
        return "https://{0}/ugc/{1}".format(settings.UGC_HOST, content)

    def public_content(self, content):
        return {
            'width': content['width'],
            'height': content['height'],
            'url': self.url(content['name']),
        }

    def public_original(self):
        return self.public_content(self.original) if self.original else None

    def public_remix_of_giant_url(self):
        return self.url(self.remix_of_giant_url) if self.remix_of_giant_url else None

    def public_small_square(self):
        return self.public_content(self.small_square) if self.small_square else None

    def public_thumbnail(self):
        return self.public_content(self.thumbnail) if self.thumbnail else None

    def public_stream(self):
        return self.public_content(self.stream) if self.stream else None

    def public_small_column(self):
        return self.public_content(self.small_column) if self.small_column else None

    def public_column(self):
        return self.public_content(self.column) if self.column else None

    def public_giant(self):
        return self.public_content(self.giant) if self.giant else None

    def public_mobile(self):
        return self.public_content(self.mobile) if self.mobile else None

    def public_footer(self):
        return self.public_content(self.footer) if self.footer else None


class PublicAPIGroupDetails(ClientDetailsBase, _PublicAPIObjectMixin):
    TO_CLIENT_WHITELIST = _PublicAPIObjectMixin.TO_CLIENT_WHITELIST + [
        'group',
        'url',
        'posts',
    ]

    def __init__(self, params):
        if isinstance(params, basestring):
            self.group = params
            self.skip = 0
        else:
            self.group = params['group']
            self.skip = params['skip']
        group = Category.get(self.group)
        if group is None:
            raise Http404
        self.posts = self.public_posts()

    def public_posts(self):
        nav = browse.Navigation.load_json_or_404({
            'category': self.group,
            'offset': self.skip,
            'public_api': True,
            'sort': 'new',
        })
        posts = browse.get_front_comments(AnonymousUser(), nav)
        return [BriefPublicAPICommentDetails(x.details().to_dict()).to_client() for x in posts]

    def url(self):
        return "https://{0}/x/{1}".format(settings.DOMAIN, self.group)

    def api_url(self):
        return "https://{0}/public_api/groups/{1}".format(settings.DOMAIN, self.group)

class PublicAPIUserDetails(ClientDetailsBase, _PublicAPIObjectMixin):
    TO_CLIENT_WHITELIST = _PublicAPIObjectMixin.TO_CLIENT_WHITELIST + [
        'user',
        'posts',
    ]

    def __init__(self, params):
        if isinstance(params, basestring):
            self.user = params
            self.skip = 0
        else:
            self.user = params['user']
            self.skip = params['skip']
        self.posts = self.public_posts()

    def public_posts(self):
        nav = browse.Navigation.load_json_or_404({
            'userpage_type': 'new',
            'user': self.user,
            'offset': self.skip,
            'public_api': True,
        })
        posts = browse.get_user_data(AnonymousUser(), nav)
        return [BriefPublicAPICommentDetails(x.comment.to_dict()).to_client() for x in posts]

    def api_url(self):
        return "https://{0}/public/users/{1}".format(settings.DOMAIN, self.user)


class BriefPublicAPICommentDetails(CommentDetails, _PublicAPIObjectMixin):
    TO_CLIENT_WHITELIST = _PublicAPIObjectMixin.TO_CLIENT_WHITELIST + [
        ('id', False, 'post_id'),
        'title',
        'category',
        'author_name',
        'parent_comment',
        'thread_op_id',
        ('timestamp', False, 'int_timestamp'),
        ('url', False, 'absolute_url'),
    ]

    def __init__(self, details):
        super(BriefPublicAPICommentDetails, self).__init__(details)
        self.replies = Comment.visible.filter(parent_comment__id=self.id).order_by('id')

    def post_id(self):
        return short_id(self.id)

    def thread_op_id(self):
        return short_id(self.thread_op_comment_id)

    def brief_replies(self):
        ids = [x for x in self.replies.values_list('id', flat=True)]
        calls = [Comment.details_by_id(id, promoter=BriefPublicAPICommentDetails) for id in ids]
        return CachedCall.multicall(calls, skip_decorator=True)

    def api_url(self):
        return "https://{0}/public_api/posts/{1}".format(settings.DOMAIN, self.post_id())

    def int_timestamp(self):
        return int(self.timestamp)

    def absolute_url(self):
        return "https://{0}{1}".format(settings.DOMAIN, self.url)


class PublicAPICommentDetails(BriefPublicAPICommentDetails):
    TO_CLIENT_WHITELIST = BriefPublicAPICommentDetails.TO_CLIENT_WHITELIST + [
        ('caption', False, 'reply_text'),
        ('parent_url', False, 'absolute_parent_url'),
        ('share_page_url', False, 'absolute_share_page_url'),
        ('reply_to', False, 'replied_comment'),
        ('stickers', False, 'sorted_sticker_counts'),
        'reply_content',
        'top_sticker',
        'external_content',
        ('replies', False, 'brief_replies'),
    ]

    def absolute_parent_url(self):
        if not self.parent_url:
            return None
        return "https://{0}{1}".format(settings.DOMAIN, self.parent_url)

    def absolute_share_page_url(self):
        return "https://{0}{1}".format(settings.DOMAIN, self.share_page_url)

    @property
    def reply_content(self):
        if self._d.get('reply_content'):
            return PublicAPIContentDetails(self._d['reply_content'])
        return {}



