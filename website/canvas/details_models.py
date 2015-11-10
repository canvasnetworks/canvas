from django.conf import settings

from apps.client_details.models import ClientDetailsBase
from apps.tags.models import Tag
from canvas import stickers
from canvas.cache_patterns import CachedCall
from canvas.redis_models import RealtimeChannel
from canvas.util import base36encode, strip_template_chars


class ContentDetails(ClientDetailsBase):
    UGC_IMAGES = [
        ('tiny_square', True),
        ('small_square', True),
        ('square', True),
        ('medium_square', True),
        ('thumbnail', True),
        ('stream', True),
        ('small_column', True),
        ('column', True),
        ('explore_column', True),
        ('giant', True),
        ('mobile', True),
        ('footer', True),
        'ugc_original',
    ]

    TO_CLIENT_WHITELIST = [
        'id',
        'timestamp',
        'remix_text',
        ('original', True),
        ('remix_of_first_caption_url', True),
        ('remix_of_giant_url', True),
        ('remix_of_thumbnail_url', True),
    ] + UGC_IMAGES

    # TODO: Do this proper, this is a fix for suggest widget
    def to_dict(self):
        return self._d

    def __init__(self, details):
        ClientDetailsBase.__init__(self, details)

        self.ugc_original = details.get('original')

        for size in ['giant', 'thumbnail']:
            attr = 'remix_of_' + size + '_url'
            url = None
            if getattr(self, attr, None):
                url = self.ugc_url(getattr(self, attr))
            setattr(self, attr, url)

        for name in self.UGC_IMAGES:
            if isinstance(name, tuple):
                name, v = name
            if hasattr(self, name):
                val = getattr(self, name)
                setattr(self, name, self.ugc_content(val))

    def ugc_url(self, content):
        if content.startswith("https://"):
            raise Exception("Creating a ContentDetails from to_client dict.")
        protocol = 'https' if settings.UGC_HTTPS_ENABLED else 'http'
        return "{}://{}/ugc/{}".format(protocol, settings.UGC_HOST, content)

    def get_absolute_url_for_image_type(self, image_type):
        try:
            url = self[image_type].get('name', self[image_type].get('url'))
        except (KeyError, IndexError,):
            return ''
        if image_type == 'original':
            return self.ugc_url(url)
        return url

    def ugc_content(self, content):
        if content:
            url = self.ugc_url(content['name'])
            return dict(content, url=url, name=url)

        return {}

    @property
    def all_images(self):
        images = {}
        for name in self.UGC_IMAGES:
            if isinstance(name, tuple):
                name, _ = name
            try:
                images[name] = getattr(self, name)
            except AttributeError:
                pass
        return images

    def is_animated(self):
        try:
            return bool(self._d['original']['animated'])
        except KeyError:
            return False

    def get_absolute_url_for_expanded(self):
        if self.is_animated():
            return self.get_absolute_url_for_image_type('original')
        return self.get_absolute_url_for_image_type('giant')

    #def __getattr__(self, name):
    #    try:
    #        return super(ContentDetails, self).__getattr__(name)
    #    except AttributeError as e:
    #        if name in self.UGC_IMAGES or name == 'original':
    #            return None
    #        raise e

    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError:
            raise IndexError


class CommentDetailsStickersMixin(object):
    def sorted_sticker_counts(self):
        counts = dict([(stickers.details_for(type_id), count) for type_id, count in self._d['sticker_counts'].items()])
        sorted_counts = stickers.sorted_counts(counts)
        count_json = [
            {
                'type_id': sticker.type_id,
                'count': count,
                'name': sticker.name,
            }
            for sticker, count
            in sorted_counts
        ]
        return count_json

    def top_sticker(self):
        try:
            return self.sorted_sticker_counts()[0]
        except IndexError:
            return None


class CommentDetailsRealtimeMixin(object):
    updates_channel = property(lambda self: RealtimeChannel('cu:%s' %  self.id, 5, ttl=24*60*60))


class CommentDetails(ClientDetailsBase, CommentDetailsStickersMixin, CommentDetailsRealtimeMixin):
    TO_CLIENT_WHITELIST = [
        'top_sticker',
        'sorted_sticker_counts',
        'author_name',
        'category',
        'category_pretty_name',
        'category_url',
        'flag_counts',
        'id',
        'external_content',
        'is_collapsed',
        ('is_remix', True, '_is_real_remix'),
        'judged',
        'last_reply_id',
        'last_reply_time',
        'ot_hidden',
        'parent_id',
        'parent_url',
        'replied_comment',
        'reply_content',
        'reply_content_id',
        'reply_count',
        ('reply_text', False, 'ugc_reply_text'),
        'repost_count',
        'share_page_url',
        'short_id',
        'staff',
        'sticker_counts',
        'tags',
        'thread_op_comment_id',
        'timestamp',
        ('title', False, 'ugc_title'),
        'url',
        'visibility',
    ]

    def __init__(self, details):
        super(CommentDetails, self).__init__(details)
        self.pins = None
        self._thread = None

    @property
    def external_content(self):
        return self._d.get('external_content', [])

    #TODO temporary until we nail the new Details API
    # Just needs a separate entry point from to_client,
    # though this will be moved into CachedDetails internals.
    def to_dict(self):
        return self._d

    @classmethod
    def from_id(cls, comment_id):
        """ Does not include user pins. """
        from canvas.models import Comment
        return Comment.details_by_id(comment_id)()

    @classmethod
    def from_ids(cls, comment_ids):
        """ Returns a list of CommentDetails instances. Does not include user pins. """
        from canvas.models import Comment
        details = [Comment.details_by_id(comment_id) for comment_id in comment_ids]
        return CachedCall.many_multicall(details)[0]

    @property
    def tags(self):
        return [Tag(tag) for tag in self._d['tags']]

    @property
    def linked_url(self):
        if self.url:
            hash_ = '' if self.is_op() else '#current'
            return self.url + hash_

    def has_replies(self):
        return self._d.get('last_reply_id') is not None

    def has_small_image(self):
        return self._d['reply_content'].get('small_square') is not None

    def has_content(self):
        return bool(self._d.get('reply_content'))

    def author_is_canvas(self):
        """ Whether this is by the special Canvas user account. Returns `False` if anonymous. """
        return self.author_name.lower() == 'canvas'

    def is_author(self, user):
        return self.author_id == user.id

    def is_op(self):
        return not self.parent_id

    def ugc_reply_text(self):
        return strip_template_chars(self.reply_text)

    def ugc_title(self):
        return strip_template_chars(self.title)

    def is_remix(self):
        content = self._d.get('reply_content')
        if content:
            return bool(content.get('remix_of_giant_url'))
        return False

    def _is_real_remix(self):
        return self._d.get('is_remix')

    def is_animated(self):
        try:
            return bool(self._d['reply_content']['original']['animated'])
        except KeyError:
            return False

    def is_visible(self):
        from canvas.models import Visibility
        return Visibility.is_visible(self.visibility)

    @property
    def is_anonymous(self):
        return self.author_name.lower() == 'anonymous'

    def is_monster_top(self, mobile=False):
        from apps.monster.models import MONSTER_GROUP, MONSTER_MOBILE_GROUP
        group = {True: MONSTER_MOBILE_GROUP, False: MONSTER_GROUP}[mobile]
        return bool(self.category and self.category == group and not self.parent_id)

    def is_monster_bottom(self, mobile=False):
        from apps.monster.models import MONSTER_GROUP, MONSTER_MOBILE_GROUP
        group = {True: MONSTER_MOBILE_GROUP, False: MONSTER_GROUP}
        return bool(self.category and self.category == group and self.parent_id)

    def get_last_reply(self):
        if self._d.get('last_reply_id') is not None:
            return CommentDetails.from_id(self._d['last_reply_id'])

    @property
    def thread(self):
        """ The thread that owns this comment, whether this is an OP or a reply. """
        from apps.threads.details_models import ThreadDetails

        if self._thread is None:
            self._thread = ThreadDetails(self)
        return self._thread

    @property
    def reply_content(self):
        if self._d.get('reply_content'):
            if settings.PROJECT == 'canvas':
                return ContentDetails(self._d['reply_content'])
            elif settings.PROJECT == 'drawquest':
                from drawquest.details_models import ContentDetails as DrawquestContentDetails
                return DrawquestContentDetails(self._d['reply_content'])
        return {}

    @property
    def author_profile_url(self):
        if not self.is_anonymous:
            return '/user/' + self.author_name

    def get_footer_absolute_url(self):
        from realtime.footer import CommentFooter

        protocol = 'https' if settings.HTTPS_ENABLED else 'http'
        return protocol + '://' + settings.UGC_HOST + '/ugc/' + CommentFooter.get_path_from_comment_details(self)

    def get_feed_thumbnail_absolute_url(self):
        return self.reply_content.get_absolute_url_for_image_type('column')

    def get_thumbnail_absolute_url(self):
        if self.reply_content:
            return self.reply_content.get_absolute_url_for_image_type('small_square')
        return '/static/img/text-post.png'

    @property
    def parent_comment(self):
        return self._d.get('parent_comment')

    @parent_comment.setter
    def parent_comment(self, val):
        self._d['parent_comment'] = val

    def short_id(self):
        return base36encode(self._d.get('id'))


class RealtimeCommentDetails(ClientDetailsBase):
    TO_CLIENT_WHITELIST = [
        'sticker_counts',
        'sorted_sticker_counts',
        'top_sticker',
        'reply_count',
        'id',
    ]

    def __init__(self, comment_details):
        for key in self.TO_CLIENT_WHITELIST:
            setattr(self, key, getattr(comment_details, key))


class FlaggedCommentDetails(CommentDetails):
    TO_CLIENT_WHITELIST = [
        'top_sticker',
        'sorted_sticker_counts',
        'author_name',
        'category',
        'category_url',
        'first_flag',
        'flag_counts',
        'flag_count',
        'id',
        'external_content',
        'is_collapsed',
        'is_disabled',
        'is_downvoted',
        'is_inappropriate',
        'is_offtopic',
        'is_removed',
        'judged',
        'last_reply_id',
        'last_reply_time',
        'ot_hidden',
        'parent_id',
        'parent_url',
        'real_username',
        'replied_comment',
        'reply_content',
        'reply_content_id',
        'reply_count',
        'reply_text',
        'repost_count',
        'share_page_url',
        'short_id',
        'staff',
        'sticker_counts',
        'thread_op_comment_id',
        'timestamp',
        'title' ,
        'url',
        'user_ban_count',
        'user_warning_count',
        'visibility',
        'flag_count',
    ]

