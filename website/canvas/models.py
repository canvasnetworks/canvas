from collections import defaultdict
import datetime
import hmac
import string
import time
import urllib

from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError
from django.db.models import *
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from facebook import GraphAPI, GraphAPIError
from django.conf import settings

import apps.feed.realtime
from apps.activity.redis_models import ActivityStream
from apps.canvas_auth.models import User, AnonymousUser
from apps.feed.redis_models import UserFeedSourceBuffer, UserFeedPromotionBuffer, ThreadFeedSourceBuffer
from apps.comment_hiding.redis_models import HiddenComments, HiddenThreads
from apps.invite_remixer.models import RemixInvites
from apps.tags.models import Tag
from apps.user_settings.signals import user_email_changed
from canvas import signals
from canvas.redis_models import (redis, RedisLastBumpedBuffer, RedisSortedSet, RedisKey, RealtimeChannel, DateKey,
                                 UserNotificationQueue, RedisHash, RedisCachedHash, HashSlot, hint, hfloat, hstr,
                                 hbool, RedisSet)
from canvas import bgwork, util, experiments, stickers, knobs, comment as comment_logic
from canvas.cache_patterns import CachedCall, cacheable, memoize, invalidates_cache, DoesNotExist
from canvas.exceptions import ServiceError
from canvas.experiments import RequestExperiments, UserExperimentsBackend
from canvas.metrics import Metrics
from canvas.notifications.actions import Actions
from canvas.notifications.notification_models import UserNotificationsSubscription
from canvas.util import UnixTimestampField, Now
from configuration import Config
from services import Services


class BaseCanvasModel(Model):
    """ Base class for all Canvas Models. """
    class Meta:
        abstract = True

    def to_client(self):
        """
        A default way to serialize a model into a dictionary for the purposes of sending data down to the client.

        Override this to make your own serialization scheme.
        """
        dictionary = {}
        # Loop through the fields.
        for field in self._meta.get_all_field_names():
            try:
                # Sometimes exceptions are raised. We do not care about their type.
                dictionary[field] = self.__getattribute__(field)
            except:
                pass
        return dictionary

    def __unicode__(self):
        return unicode(self.to_client())


def get_system_user():
    return User.objects.get_or_none(username='canvas') or User.objects.get(id=1)

def get_mapping_id_from_short_id(short_id):
    return util.base36decode_or_404(short_id)

def send_sticker(comment_sticker):
    """ Notifies the recipient about the sticker their post received, and gives them credit for it. """
    from canvas import economy

    # Bailout if this is a no-value sticker.
    if comment_sticker.sticker.value <= 0:
        return

    recipient = comment_sticker.comment.author

    if comment_sticker.sticker.is_epic():
        # Credit for epic stickers happens when the user acknowledges the on-screen
        # notification.
        Actions.epic_stickered(comment_sticker.user, comment_sticker)
    elif comment_sticker.sticker.is_star():
        Actions.starred(comment_sticker.user, comment_sticker)
    else:
        Actions.stickered(comment_sticker.user, comment_sticker)

    try:
        CommentStickerLog.objects.get(user=comment_sticker.user, comment=comment_sticker.comment)
    except CommentStickerLog.DoesNotExist:
        economy.credit_received_sticker(recipient, comment_sticker.type_id)

def send_invite_email(code, email, inviter=None, invited=None, extra_message="", user=None):
    if inviter and invited:
        subject = "%s %s has personally invited you to join Example.com" % (inviter.first_name, inviter.last_name)
        inviter_name = inviter.first_name
    elif user:
        subject = "%s has personally invited you to join Example.com" % (user.username)
        inviter_name = user.username
    else:
        subject = "You have been invited to Example.com"
        invite_name = None

    text = render_to_string('email/invite.django.txt', locals())
    html = render_to_string('email/invite.django.html', locals())

    mail = EmailMultiAlternatives(subject, text, 'Canvas Invites <invites@example.com>', [email])
    mail.attach_alternative(html, "text/html")
    try:
        mail.send()
    except:
        if user:
            raise ServiceError("Send failed")
        else:
            # Not in a request, reraise the original exception
            raise

def manager_queryset_wrapper(method_name):
    def _manager_method(self, *args, **kwargs):
        return getattr(self.get_query_set(), method_name)(*args, **kwargs)
    setattr(Manager, method_name, _manager_method)

for method_name in ('get_or_none', 'get_first_or_none', 'in_bulk_list'):
    manager_queryset_wrapper(method_name)

def _get_or_none(self, **kwargs):
    try:
        return self.get(**kwargs)
    except self.model.DoesNotExist:
        return None
QuerySet.get_or_none = _get_or_none

def _get_first_or_none(self, **kwargs):
    return self[:1].get_or_none(**kwargs)
QuerySet.get_first_or_none = _get_first_or_none

@util.iterlist
def in_bulk_list(self, ids):
    results_dict = self.in_bulk(ids)
    for id_ in ids:
        row = results_dict.get(int(id_))
        if row is not None:
            yield row
QuerySet.in_bulk_list = in_bulk_list


class UserRedis(object):
    """ For logged-in users. """
    def __init__(self, user_id, staff=False):
        self.pinned_bump_buffer = RedisLastBumpedBuffer('user_pinned:%s:bumped' % user_id, 30*6)
        self.pinned_posts_channel = RealtimeChannel('user_pinned:%s' % user_id, 20)
        self.channel = RealtimeChannel('user:%s:rt' % user_id, 20)
        self.experiments = RequestExperiments(UserExperimentsBackend(user_id, staff), user_id=user_id)
        self.user_kv = RedisHash('user:%s:info' % user_id)
        self.notifications = UserNotificationQueue(user_id, self.channel)
        self.top_posts = RedisLastBumpedBuffer('user:%s:top_posts' % user_id, 30*30)
        self.top_anonymous_posts = RedisLastBumpedBuffer('user:%s:top_posts:anon' % user_id, 30*30)
        self.ip_history = RedisLastBumpedBuffer('user:%s:ip_history' % user_id, 1000)

        self.activity_stream = ActivityStream(user_id)
        self.activity_stream_channel = RealtimeChannel('user_activity:{}'.format(user_id), 20)

        self.followers = RedisSet('user:{}:followers'.format(user_id))
        self.following = RedisSet('user:{}:following'.format(user_id))

        self.followed_tags = RedisSortedSet('user:{}:followed_tags'.format(user_id), getter=str)
        self.followed_tags_info = RedisHash('user:{}:followed_tags_info'.format(user_id))

        self.followed_threads = RedisSet('user:{}:followed_threads'.format(user_id))

        self.hidden_comments = HiddenComments(user_id)
        self.hidden_threads = HiddenThreads(user_id)

        self.feed_source = UserFeedSourceBuffer(user_id, 1000)
        self.feed_promotion = UserFeedPromotionBuffer(user_id, 400)

        # A set of threads ids that the user does not want to receive emails about anymore.
        self.muted_threads = RedisSet('user:%s:email_muted_threads' % user_id)
        self.muted_suggestions = RedisSet('user:{}:muted_suggestions'.format(user_id))
        self.muted_suggested_tags =  RedisSet('user:{}:muted_suggested_tags'.format(user_id))
        self.muted_suggested_users =  RedisSet('user:{}:muted_suggested_users'.format(user_id))

        #TODO split DrawQuest's UserRedis into a different object, configurable in settings.
        from drawquest.apps.palettes.models import UserPalettes
        self.palettes = UserPalettes(user_id)
        self.coin_channel = RealtimeChannel('user:{}:rt_coins'.format(user_id), 5)

    def mute_thread(self, comment):
        """ Adds the id of the comment's original post to the muted threads set. """
        thread = comment.thread.op
        self.muted_threads.sadd(comment.id)


def valid_slug(raw):
    raw = raw.lstrip('#').strip()
    allowed = string.letters + string.digits + '_'
    def process(c):
        if c in allowed:
            return c
        elif c in string.whitespace:
            return '_'
        else:
            return ''

    return (''.join(map(process, raw)))[:20]


class ContentUrlMapping(Model):
    """ We use this table's PK as a non-PK auto_inc col for Content, basically. """


def manager(fun):
    class SimpleManager(Manager):
        def get_query_set(self):
            return fun(Manager.get_query_set(self))
    return SimpleManager


class Visibility(object):
    # These are also hardcoded in comments.js, and maybe other places now

    PUBLIC = 0
    HIDDEN = 1
    DISABLED = 2
    UNPUBLISHED = 3
    CURATED = 4

    choices = (
       (PUBLIC, 'Visible'),
       (HIDDEN, 'Hide from browse pages'),
       (DISABLED, 'Disabled'),
       (UNPUBLISHED, 'Unpublished'),
       (CURATED, 'Hide from popular page')
    )

    short_names = ['public', 'hidden', 'disabled', 'unpublished', 'curated']

    curated_choices = [PUBLIC]
    visible_choices = [PUBLIC, HIDDEN, CURATED]
    public_choices = [PUBLIC, CURATED]
    invisible_choices = [DISABLED, UNPUBLISHED]

    q_public = Q(visibility__in=public_choices)
    q_visible = Q(visibility__in=visible_choices)

    CuratedManager = manager(lambda q: q.filter(visibility__in=Visibility.curated_choices))
    PublicOnlyManager = manager(lambda q: q.filter(Visibility.q_public))
    VisibleOnlyManager = manager(lambda q: q.filter(Visibility.q_visible))
    UnmoderatedOnlyManager = manager(lambda q: q.filter(visibility__in=[Visibility.PUBLIC, Visibility.UNPUBLISHED]))
    PublishedOnlyManager = manager(lambda q: q.exclude(visibility=Visibility.UNPUBLISHED))

    @classmethod
    def is_visible(cls, visibility):
        return visibility in [cls.PUBLIC, cls.CURATED]


class BrowseManager(Manager):
    def get_query_set(self):
        return (super(BrowseManager, self)
            .get_query_set()
            .exclude(category__name__in=settings.HIDDEN_GROUPS)
            .filter(visibility__in=Visibility.public_choices))


class VisibleBrowseManager(Manager):
    def get_query_set(self):
        return (super(VisibleBrowseManager, self)
            .get_query_set()
            .exclude(category__name__in=settings.HIDDEN_GROUPS)
            .filter(visibility__in=Visibility.visible_choices))


class CuratedBrowseManager(Manager):
    def get_query_set(self):
        return (super(CuratedBrowseManager, self)
            .get_query_set()
            .exclude(category__name__in=settings.HIDDEN_GROUPS)
            .filter(visibility__in=Visibility.curated_choices))


class VisibleModel(BaseCanvasModel):
    """
    An abstract model for things that we need to toggle the visibility for, such as as comments, groups .. etc.
    """
    class Meta:
        abstract = True

    visibility = IntegerField(default=Visibility.PUBLIC, choices=Visibility.choices)

    # The "default manager" depends on the definition order of managers - it's the first one.
    #
    # This is a different concept from "MyModel.objects" which corresponds to the default manager
    # only if MyModel.objects is not explicitly defined.
    #
    # It's also a different concept from "automatic managers" (also known as "plain managers") which
    # Django will create for things such as related models.
    all_objects = Manager() # Don't move this. Needs to be first to be the default manager.
    objects = public = Visibility.PublicOnlyManager()
    visible = Visibility.VisibleOnlyManager()
    published = Visibility.PublishedOnlyManager()
    unmoderated = Visibility.UnmoderatedOnlyManager()
    curated = Visibility.CuratedManager()

    def hide_if_unpublished(self):
        """ Allow promoting something to hidden if it was otherwise unpublished. """
        if self.visibility == Visibility.UNPUBLISHED:
            self.visibility = Visibility.HIDDEN
            self.save()

    def get_visibility_short_name(self):
        return Visibility.short_names[self.visibility]

    @property
    def is_public(self):
        return self.visibility == Visibility.PUBLIC

    def is_visible(self):
        return self.visibility not in (Visibility.DISABLED, Visibility.UNPUBLISHED)

    def publish(self):
        if self.visibility == Visibility.UNPUBLISHED:
            self.visibility = Visibility.PUBLIC
            self.save()


class ExternalContent(BaseCanvasModel):
    """
    External content associated with a Canvas comment.

    This allows us to support YouTube video/audio to run alongside an animated gif.
    """
    # Content types. For now, we only support YouTube.
    CONTENT_CHOICES = (
        ('yt', 'youtube'),
        ('vm', 'vimeo')
    )

    # Note that having a 2-char field restricts the choices to 38x38
    content_type = CharField(max_length=2, choices=CONTENT_CHOICES)
    source_url = CharField(max_length=4000, default='', blank=True, null=True)
    # A many-to-one relationship. This way we can get ExternalContent from a Comment.
    parent_comment = ForeignKey('Comment', related_name="external_content")
    # We store type specific details in this field.
    # For example, for YouTube videos, we store the start and end times and
    # the id.
    # This is a basic implementation of a JSON field.
    _data = TextField(default="{}")

    def details(self):
        return util.loads(self._data)

    def _set_details(self, new_details_dict):
        #@TODO: Add in-object caching dict.
        self._data = util.dumps(new_details_dict)

    def _get_data(self, key):
        """ Gets data from inside the details dict. """
        return self.details().get(key)

    def _set_data(self, key, value):
        """ Sets datum inside the details dict. """
        details = self.details()
        details[key] = value
        self._set_details(details)

    @classmethod
    def _make_property(cls, key):
        """ Hackery because overriding __setattr__ for models causes weird errors in Django. """
        return property(lambda self: self._get_data(key),
                        lambda self, value: self._set_data(key, value))

    def __eq__(self, other):
        return isinstance(other, ExternalContent) and self.id == other.id

    def to_client(self):
        data = self.details()
        data.update(dict(source_url=self.source_url))
        return data

    @classmethod
    def from_dict(cls, external_content_dict):
        """
        A simple factory method for the specialized content types.

        Returns an unsaved ExternalContent
        """
        if not external_content_dict:
            return

        class_map = {"yt": YouTubeContent}
        external_content_type = external_content_dict.get("type")

        # Bail out if we do not know this type
        #TODO shouldn't this raise an exception?
        if external_content_type not in class_map:
            return

        # Instantiate and set the details
        # Note that the model is not saved. The calling method should set the parent comment
        # and save it.
        external_content = class_map.get(external_content_type)()
        #TODO: We need some validation logic. For example, ensure that end_time > start_time for YouTube content.
        external_content._set_details(external_content_dict)
        external_content.content_type = external_content_type
        if external_content_dict.get("source_url", None):
            external_content.source_url = external_content_dict.get("source_url")

        # Loop through the dict and set the properties, such as source_url and content_type
        for key, value in external_content_dict.items():
            try:
                setattr(external_content, key, value)
            except AttributeError:
                pass
        return external_content

    #TODO: Add in-object caching
    @property
    def proxy(self):
        """
        There is no way to return a set of heterogenuous proxy models.
        http://stackoverflow.com/questions/3910936/django-heterogeneous-queryset-proxy-models

        So this returns the specific proxy for this instance's type (provided by from_dict).
        """
        details = self.details()
        details['type'] = self.content_type
        details['source_url'] = self.source_url
        return ExternalContent.from_dict(details)

    @invalidates_cache(lambda self: self.parent_comment.details)
    def save(self):
        """ We override this to invalidate the cache on the parent comment. """
        return super(ExternalContent, self).save()


class YouTubeContent(ExternalContent):
    """ A proxy for ExternalContent that provides a YouTube specific interface. """
    class Meta:
        proxy = True

    # Start and end times of this video clip.
    start_time = ExternalContent._make_property("start_time")
    end_time = ExternalContent._make_property("end_time")

    @property
    def loop_length(self):
        return float(self.end_time) - float(self.start_time)


class Content(VisibleModel):
    id = CharField(max_length=40, blank=False, null=False, primary_key=True)
    url_mapping = ForeignKey(ContentUrlMapping, blank=True, null=True)
    remix_of = ForeignKey('self', related_name='remixes', null=True, blank=True)
    stamps_used = ManyToManyField('self', related_name='used_as_stamp', symmetrical=False, blank=True)

    alpha = BooleanField()
    animated = BooleanField()

    timestamp = UnixTimestampField()
    ip = IPAddressField(default='0.0.0.0')

    source_url = CharField(max_length=4000, default='', blank=True)
    remix_text = CharField(max_length=1000, default='', blank=True)

    SMALL_DRAW_FROM_SCRATCH_PK = 'e4ffb3bcdb44f6f62fa50e77b4897c1ade346a34'
    DRAW_FROM_SCRATCH_PK = '63a1d01c5df1b60f94e4457b11cd98d8129d656c'

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Content) and self.id == other.id

    @property
    def details_key(self):
        """
        This is a key used by the thumbnailer to store image meta data in Redis.  See thumbnailer.create_content.
        """
        return ('content:' + self.id + ':details').encode('ascii')

    def _get_details(self, skip_remix_of_urls=False):
        """
        skip_remix_of_urls will avoid triggering a recursive call to _get_details
        solves this issue: https://sentry.example.com/group/1340
        """
        # Get the details from Redis.
        raw = redis.get(self.details_key)
        if not raw:
            from canvas.thumbnailer import Thumbnailer
            # This is a bandaid fix for the thumbnailer not having created a thumbnailed version of this image.
            #TODO: Show a "Ooops... something is wrong with this image" for images that the thumbnailer failed for.
            details = dict(map(lambda key: (key, defaultdict(lambda: None)), Thumbnailer.META.keys()))
        else:
            details = util.loads(raw)

        details['id'] = self.id
        details['timestamp'] = self.timestamp

        if self.remix_of:
            first_caption = self.remix_of.first_caption
            if first_caption:
                details['remix_of_first_caption_url'] = first_caption.get_absolute_url()

        for size in ['giant', 'thumbnail']:
            key = 'remix_of_' + size + '_url'
            if self.remix_of:
                if not skip_remix_of_urls:
                    details[key] = self.remix_of._get_details(skip_remix_of_urls=True).get(size, {}).get('name')

        details['remix_text'] = self.remix_text
        return details

    @property
    def details(self):
        if settings.PROJECT == 'canvas':
            from canvas.details_models import ContentDetails
        elif settings.PROJECT == 'drawquest':
            from drawquest.details_models import ContentDetails

        return CachedCall(
            "content:%s:full_details_v19" % self.id,
            self._get_details,
            24*60*60,
            promoter=ContentDetails,
        )

    @property
    def short_id(self):
        return util.base36encode(self.url_mapping_id)

    @property
    def first_caption(self):
        """ Returns the first Comment, where this content was used. """
        result = self.used_in_comments.filter(Visibility.q_visible).order_by('id')[:1]
        if result:
            return result[0]

    @property
    def admin_info(self):
        return {
            'id': self.id,
            'visibility': self.get_visibility_short_name(),
        }

    @classmethod
    def get_appropriate_manager(cls, user):
        if user.is_authenticated() and user.is_staff:
            return 'all_objects'
        else:
            return 'visible_browse_objects'

    def is_remix(self):
        return bool(self.remix_of)

    def publish(self, request):
        if self.visibility == Visibility.UNPUBLISHED:
            self.visibility = Visibility.PUBLIC
            self.save()

            Metrics.publish.record(
                request,
                content=self.id,
                remix_of=self.remix_of_id,
                stamps_used=list(self.stamps_used.values_list('id', flat=True)),
                alpha=self.alpha,
                animated=self.animated,
                upload_ts=self.timestamp,
                upload_ip=self.ip,
                source_url=self.source_url,
                remix_text=self.remix_text,
            )

    def moderate_and_propagate(self, visibility, user, undoing=False):
        self.visibility = visibility
        self.save()

        # Push out this visibility to all comments that use it.
        for comment in self.used_in_comments.all():
            comment.moderate_and_save(visibility, user, undoing)


class CategoryMixin(object):
    disabled = False
    posts_channel = property(lambda self: RealtimeChannel('cat:%s' % self.name, 20))
    bumped_buffer = property(lambda self: RedisLastBumpedBuffer('cat:%s:bumped' % self.name, 30*30))
    popular = property(lambda self: RedisLastBumpedBuffer('cat:%s:popular' % self.name, 30*18))
    top = property(lambda self: DateKey(lambda key: RedisLastBumpedBuffer(key, 30*30), 'cat:%s:' % self.name, ':top'))

    __eq__ = lambda self, other: isinstance(other, CategoryMixin) and self.name == other.name
    __hash__ = lambda self: hash(self.name)

    def merge_top_scores(self, day=None):
        """
        Merges daily top scores into monthly and monthly into yearly top scores for this group for the given day
        and the 365 days before it.

        If `day` is `None`, defaults to today.
        """
        if not day:
            day = Services.time.today()
        # Merge today + last 365 days
        days = [day - datetime.timedelta(n) for n in range(366)]

        months = defaultdict(list)
        for day in days:
            months[(day.year, day.month)].append(day)

        years = defaultdict(list)

        for (year, month) in months.keys():
            years[year].append(month)

        for (year, month), days in months.iteritems():
            dest = self.top.month(datetime.date(year, month, 1))
            source_keys = [self.top.day(day).key for day in days]
            redis.zunionstore(dest.key, source_keys, aggregate='max')
            dest.truncate(2)

        for year, year_months in years.iteritems():
            dest = self.top.year(datetime.date(year, 1, 1))
            source_keys = [self.top.month(datetime.date(year, month, 1)).key for month in year_months]
            redis.zunionstore(dest.key, source_keys, aggregate='max')
            dest.truncate(5)


class SpecialCategory(CategoryMixin):
    special = True

    def __init__(self, name):
        if not isinstance(name, str):
            raise Exception("SpecialCategory name must be string")
        self.name = name

    def details(self):
        return {
            'description': "",
            'id': None,
            'name': self.name,
            'special': True,
            'url': '/x/%s' % self.name,
        }

    def followed(self, user):
        return False

class DisabledCategory(object):
    disabled = True

class Category(VisibleModel, CategoryMixin):
    special = False
    ALL = SpecialCategory('everything')
    MY = SpecialCategory('following')
    redis_following = RedisSortedSet('cat:all:following_v1')

    specials = [ALL, MY]
    blocked_names = ([ALL.name, MY.name,
                      'all', 'moot', 'nsfw', 'xxx', 'porn', 'fag', 'fags', 'faggot', 'admin', 'administrator',
                      'admins', 'mods', 'moderators', 'staff', 'public', 'private', 'anonymous', 'raff_ruse'])
    FOUND_LIMIT = 10

    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)

    name = CharField(max_length=20, unique=True)
    description = CharField(max_length=140)

    # A Unix timestamp of when this group was created.
    founded = FloatField(default=1298956320) # when we added the initial categories :]

    founder = ForeignKey(User, related_name="founded_groups", blank=True, null=True, default=None)
    moderators = ManyToManyField(User, related_name="moderated_categories")

    def get_absolute_url(self):
        return u'/x/' + self.name

    def validate(self):
        name_min, name_max, desc_min, desc_max = 3, 20, 10, 140
        if len(self.name) < name_min or len(self.name) > name_max:
            return 'Group name must between %s and %s characters.' % (name_min, name_max)
        if len(self.description) < desc_min or len(self.description) > desc_max:
            return 'Group description must be between %s and %s characters.' % (desc_min, desc_max)
        if not self.name.replace("_", "").isalnum():
            return 'Group name can only contain letters, numbers, and underscores.'
        if not self.name == self.name.lower():
            return 'Group names must be all lowercase.'
        if self.name.lower() in self.blocked_names:
            return 'Sorry, ' + self.name + ' is not allowed as a group name.'

    def can_moderate(self, user):
        return (user == self.founder) or (user in self.moderators.all())

    def can_modify(self, user):
        return user == self.founder

    def can_disable(self, user):
        return user.is_authenticated() and user.is_staff

    def followed(self, user):
        return FollowCategory.objects.filter(category=self, user=user).exists()

    @property
    def founded_readable(self):
        return datetime.datetime.fromtimestamp(self.founded).strftime("%B %d, %Y")

    def __repr__(self):
        return "<Category: %s>" % self.name

    @property
    def pretty_name(self):
        return self.name.replace('_', ' ').title()

    @classmethod
    def get(cls, name):
        if not name:
            return None

        for special in cls.specials:
            if special.name == name:
                return special

        category = cls.all_objects.get_or_none(name=name)
        if category and category.visibility == Visibility.DISABLED:
            return DisabledCategory()
        return category

    @classmethod
    def get_default(cls, user):
        if user.has_lab('root_is_following'):
            return cls.MY
        return cls.ALL

    def _details(self):
        follow_count = self.followers.count()
        # Update the following score for this group.
        Category.redis_following.zadd(self.id, follow_count)
        return {
            'description': self.description,
            'followers': follow_count, # appropriately forced.
            'founded': self.founded,
            'founded_readable': self.founded_readable,
            'founder': self.founder.username if self.founder else 'nobody',
            'id': self.id,
            'name': self.name,
            'posts': Comment.objects.filter(category=self).count(), # not forced, since posts are common. low cache timeout should handle this though.
            'pretty_name': self.pretty_name,
            'special': False,
            'url': '/x/%s' % self.name,
        }

    @staticmethod
    def details_by_id(category_id):
        return CachedCall(
            "category:%s:details_v7" % category_id,
            lambda: Category.all_objects.get(id=category_id)._details(),
            15*60,
        )

    @property
    def details(self):
        return Category.details_by_id(self.id)

    @classmethod
    @cacheable('category:top_v2')
    def get_top(cls):
        TOP_SIZE = 15
        top_ids = cls.redis_following[:TOP_SIZE*2]
        query = cls.public.filter(id__in=top_ids).values_list('id', flat=True)
        return list(query[:TOP_SIZE])

    @classmethod
    @cacheable('category:whitelisted_v2')
    def get_whitelisted(cls):
        whitelisted = Config['featured_groups'] + Config['additional_whitelisted_groups']
        return list(cls.objects.filter(name__in=whitelisted).values_list('id', flat=True))

    @classmethod
    def get_top_details(cls):
        return [cat.details() for cat in cls.curated.in_bulk_list(cls.get_top())]


class FollowCategory(BaseCanvasModel):
    user = ForeignKey(User, db_index=True, related_name="following")
    category = ForeignKey(Category, related_name="followers")

    class Meta:
        unique_together = ('user', 'category',)


class Thread(object):
    """ Represents a thread of comments. """
    def __init__(self, op_comment):
        """ Takes the parent / OP comment instance. """
        self.op = op_comment

    @classmethod
    def from_comment(cls, comment):
        """ `comment` can be either the parent comment, or any comment within the thread. """
        if comment.parent_comment_id:
            return cls(comment.parent_comment)
        else:
            return cls(comment)

    @property
    def feed_source(self):
        return ThreadFeedSourceBuffer(self.op.id, 100)

    def get_reply_count(self):
        return self.op.replies.count()


class Comment(VisibleModel):
    """
    `parent_comment` is the comment's OP. If `parent_comment` is null, the comment is an OP. The converse is not
    necessarily true.

    `reply_content` is the image you're commenting with, or the OP's image

    `replied_comment` is where we store the comment you clicked "Reply" on, so we can show the smart hovers for
    @ replies.
    """
    # quick hack to get the correct default manager for Comment. see the comments in VisibleModel.
    #TODO the cleaner way to do this is to use ABCs for managers, and multiinherit from them -
    # the first ABC is used to find the default manager.
    all_objects = Manager() # Don't move this, it must be the first manager defined here.

    browse_objects = BrowseManager()
    visible_browse_objects = VisibleBrowseManager()
    curated_browse_objects = CuratedBrowseManager()

    # @deprecated: We do not use parent_content anymore.
    # @todo: Schedule a migration to remove it from db.
    parent_content = ForeignKey(Content, related_name='comments', null=True, blank=True)

    parent_comment = ForeignKey('self', related_name='replies', null=True, blank=True, default=None)
    # Creation time for a comment.
    timestamp = UnixTimestampField(default=0)
    reply_content = ForeignKey(Content, related_name='used_in_comments', null=True, blank=True)
    reply_text = CharField(max_length=2000, blank=True)
    replied_comment = ForeignKey('self', null=True, blank=True, default=None)
    category = ForeignKey(Category, related_name='comments', null=True, blank=True, default=None)

    author = ForeignKey(User, blank=True, null=True, default=None, related_name='comments')
    title = CharField(max_length=knobs.POST_TITLE_MAX_LENGTH, blank=True)
    ip = IPAddressField(default='0.0.0.0')
    anonymous = BooleanField()

    score = FloatField(db_index=True, default=0)
    judged = BooleanField(default=False)

    ot_hidden = BooleanField(default=False)

    # DrawQuest.
    posted_on_quest_of_the_day = BooleanField(default=False)

    popular_replies = property(lambda self: RedisLastBumpedBuffer("comment:%s:replies:popular" % self.id, 100))
    top_replies = property(lambda self: RedisLastBumpedBuffer("comment:%s:replies:top" % self.id, 100))

    redis_score = property(lambda self: RedisKey("comment:%s:score" % self.id))
    tags = property(lambda self: RedisSet("comment:{}:tags".format(self.id)))

    DOWNVOTES_REQUIRED = 3

    @classmethod
    def create_and_post(cls, request, author, is_anonymous, category, reply_content,
                        reply_text=u'', parent_comment=None, replied_comment=None, pin=True, curate=False,
                        external_content=None, fact_metadata=None, title='', tags=[],
                        posted_on_quest_of_the_day=False):
        """ Returns a new Comment instance. """
        # Although this is a model method that takes a `request` instance, the `request` is not used for anything
        # but metrics-related code. It should stay this way - as long as it's not used for other things, our views
        # won't bleed over into models (past the extent that they do from this). Aside from that, this is all
        # model-related code, so it lives here.

        # Clamp the length of the text to the max of 2000 chars.
        reply_text = reply_text[:2000]

        comment = cls(
            parent_comment=parent_comment,
            reply_content=reply_content,
            reply_text=reply_text,
            replied_comment=replied_comment,
            anonymous=is_anonymous,
            author=author,
            ip=request.META['REMOTE_ADDR'],
            category=category,
            timestamp=Now(),
            title=title,
            posted_on_quest_of_the_day=posted_on_quest_of_the_day,
        )

        # A comment requires either an image or text.
        if not (comment.reply_content or comment.reply_text):
            raise ServiceError('Invalid post.')

        if curate:
            comment.visibility = Visibility.CURATED

        # If the content was disabled, make this also disabled. 404 for the naughty user.
        banned_content = reply_content and reply_content.visibility == Visibility.DISABLED

        if banned_content:
            comment.visibility = reply_content.visibility

        # update tags
        if len(tags) == 0 and comment.category is not None:
            tags.append(comment.category.name)

        applicable_tags = set(tags)
        if comment.parent_comment is not None:
            applicable_tags = comment.parent_comment.tags.smembers().union(applicable_tags)

        # set a category if needed before the save
        if 'stamps' in applicable_tags and category is None:
            comment.category = Category.objects.get(name='stamps')

        comment.save()

        # do this after the save when we have an id
        for tag in applicable_tags:
            Tag(tag).tag_comment(comment)
            comment.tags.sadd(tag)

        # And then we have to fetch the object from the database again to get the result of the previous step.
        comment = cls.all_objects.get(pk=comment.id)

        if parent_comment:
            author.redis.followed_threads.sadd(parent_comment.id)
        else:
            author.redis.followed_threads.sadd(comment.id)

        if external_content:
            external_content.parent_comment = comment
            external_content.save()

        def after_post_work():
            cat_all = Category.ALL
            frame = {
                'comment_id': comment.id,
                'timestamp': comment.timestamp,
                'reply_content_id': comment.reply_content_id,
            }

            # Push new content into popular (so if it's empty it gets something)
            comment.update_score()

            if settings.FEED_ENABLED:
                author.redis.feed_source.bump(comment)
                apps.feed.realtime.publish_new_comment(comment)

            if reply_content:
                # Publish relevant objects if they were previously unpublished.
                reply_content.publish(request)

                # Metrics for various reply types.
                if reply_content.remix_of_id == Content.DRAW_FROM_SCRATCH_PK:
                    Metrics.draw_from_scratch.record(request)
                elif reply_content.remix_of_id:
                    Metrics.remix.record(request)

                else:
                    Metrics.image_reply.record(request)

                # Core remix action metric alarms.
                if reply_content.remix_text:
                    Metrics.remix_text_used.record(request)
                if reply_content.stamps_used:
                    Metrics.remix_stamp_used.record(request)
            else:
                # Metric for a text-only reply.
                Metrics.text_reply.record(request)

            cat_all.posts_channel.publish(frame)

            if category is not None:
                category.posts_channel.publish(frame)
                Metrics.group_post.record(request)

            if settings.FEED_ENABLED:
                comment.thread.feed_source.bump(comment.details())

            if parent_comment:
                parent_comment_details = parent_comment.details.force()

            if settings.PROJECT == 'canvas':
                if parent_comment:
                    # reply_count needs to be updated.
                    comment_logic.update_realtime(parent_comment_details)

                    parent_comment.replies_channel.publish(frame)
                    # Replies bump parents.
                    if parent_comment.category:
                        parent_comment.category.bumped_buffer.bump(parent_comment.id, comment.timestamp)
                    cat_all.bumped_buffer.bump(parent_comment.id, comment.timestamp)

                    # Bump any user pins.
                    for user_id in set(parent_comment.pins()):
                        user_redis = UserRedis(user_id)
                        # Users DO bump their own pins, so it shows up in Pinned immediately.
                        user_redis.pinned_bump_buffer.bump(parent_comment.id, comment.timestamp)
                        # But we shouldn't publish to the channel in that case.
                        if user_id != author.id:
                            user_redis.pinned_posts_channel.publish(frame)
                            user_redis.user_kv.hincrby('pinned_unseen', 1)
                else:
                    # OP bumps itself.
                    if comment.category:
                        comment.category.bumped_buffer.bump(comment.id, comment.timestamp)
                    cat_all.bumped_buffer.bump(comment.id, comment.timestamp)
                    Metrics.op.record(request)

            Metrics.post.record(
                request,
                comment=comment.id,
                anonymous=comment.anonymous,
                parent_comment=comment.parent_comment_id,
                reply_content=comment.reply_content_id,
                reply_text=comment.reply_text,
                replied_comment=comment.replied_comment_id,
                category=comment.category_id,
                meta=fact_metadata,
            )

            #
            # Begin less important things that can fail without consequences to post integrity.
            #
            match_text = reply_text
            if reply_content:
                match_text += " " + reply_content.remix_text

            match_text = match_text.lower()

            if util.has_flagged_words(match_text):
                comment.add_flag(get_system_user())

            # Auto-curate replies that are reposts or have a curated parent.
            if parent_comment:
                if (comment.details().repost_count > 0
                        or parent_comment.visibility in [Visibility.CURATED, Visibility.HIDDEN]):
                    comment.moderate_and_save(Visibility.CURATED, get_system_user())

            if "helvetica" in match_text:
                request.user.kv.achievements.achieve('hipster')

        bgwork.defer(after_post_work)

        return comment

    @property
    def thread(self):
        return Thread.from_comment(self)

    @property
    def thread_op_comment_id(self):
        return self.details().thread_op_comment_id

    @property
    def footer(self):
        from realtime.footer import CommentFooter
        return CommentFooter(self)

    @property
    def remix_invites(self):
        return RemixInvites(self)

    def is_monster_top(self, mobile=False):
        return self.details().is_monster_top(mobile=mobile)

    def is_monster_bottom(self, mobile=False):
        return self.details().is_monster_bottom(mobile=mobile)

    def make_non_anonymous(self, user):
        if user != self.author:
            raise PermissionDenied()

        self.anonymous = False
        self.save()
        self.details.force()
        self.update_score()

    @classmethod
    def unjudged_flagged(cls):
        # Use the published manager so we don't see deleted posts.
        return cls.published.filter(judged=False, flags__undone=False).distinct()

    @classmethod
    def unjudged(cls):
        return cls.published.filter(judged=False)

    def add_flag(self, user, ip='0.0.0.0'):
        """ Flags a comment. This might change its visibility. """
        # If this user has already flagged this comment, that's an error.
        if (not user.is_staff
                and CommentFlag.objects.filter(user=user, comment=self, undone=False).count()):
            if settings.PROJECT == 'canvas':
                raise ServiceError('Already flagged.')
            else:
                return

        # Immediately create the flag, to tighten the race condition of allowing multiple.
        flag = CommentFlag(
            comment=self,
            type_id=0,
            timestamp=time.time(),
            ip=ip,
            user=user,
            undone=False,
        )
        flag.save()

        # Handle good and bad flaggers.
        if redis.sismember("user:flags_curate", user.id):
            self.moderate_and_save(Visibility.CURATED, user, flagging=True)
        elif redis.sismember("user:flags_ignored", user.id):
            flag.undone = True
            flag.save()

        # If this is a staff user flagging, consider it unjudged so it can be rejudged in the queue.
        if user.is_authenticated() and user.is_staff:
            self.judged = False
            self.save()

        CommentFlag.update_channel()

        self.details.force()
        return flag

    @property
    def pinnable_comment(self):
        return self.parent_comment or self

    def add_pin(self, user, auto=False):
        """ `auto` means that we pinned this for the user, the user didn't explicitly elect to pin it. """
        # Already pinned.
        if user.id in self.pins():
            return None

        pin = CommentPin(
            comment=self.pinnable_comment,
            timestamp=time.time(),
            user=user,
            auto=auto,
        )
        pin.save()
        self.pinnable_comment.pins.force()
        return pin

    def remove_pin(self, user):
        CommentPin.objects.filter(comment=self.pinnable_comment, user=user).delete()
        self.pinnable_comment.pins.force()
        user.redis.pinned_bump_buffer.remove(self.pinnable_comment.id)

    def moderate_and_save(self, visibility, user, undoing=False, flagging=False):
        self.visibility = visibility

        # If we are moderating because of a flag, we don't want to flag or judge.
        # Also if we are unpublishing (deleting) a post, the flagging/judging logic doesn't apply.
        if not (flagging or visibility == Visibility.UNPUBLISHED):
            # If this person can moderate flagged, consider it judged, otherwise flag it.
            if user.can_moderate_flagged:
                self.judged = not undoing
            else:
                self.add_flag(user)
        self.save()

        CommentModerationLog.append(user=self.author, comment=self, moderator=user, visibility=visibility)

        self.visibility_changed()

    def mark_offtopic(self, user, offtopic=True):
        """
        Marks this comment as offtopic (or marks it as not offtopic, if `offtopic` is False).

        The given `user` is the one marking it as such.
        """
        if not (self.category and self.category.can_moderate(user)):
            raise ServiceError("Insufficient Privileges: You're not a referee for this group.")

        self.ot_hidden = offtopic

        if offtopic and self.visibility == Visibility.PUBLIC:
            self.visibility = Visibility.HIDDEN
        elif not offtopic and not self.judged and self.visibility == Visibility.HIDDEN:
            self.visibility = Visibility.PUBLIC

        self.save()
        self.visibility_changed()

    def visibility_changed(self):
        # The visibility of this can change the parent's reply_count and last_reply_id.
        self.force_parent_details()
        self.details.force()
        self.update_score()

        if self.visibility not in [Visibility.PUBLIC, Visibility.CURATED]:
            self.author.redis.feed_source.remove(self.id)

        signals.visibility_changed.send(Comment, instance=self)

    def get_score(self):
        details = self.details()

        tdelta = time.time() - details.timestamp + 10 * 60
        sticker_scores = [stickers.details_for(k).value * v for k, v in details.sticker_counts.items()]
        top_score = sum(sticker_scores)

        time_weight = ((tdelta ** 1.6) if tdelta > 0 else 1)
        repost_weight = details.repost_count + 1.0
        pop_score = top_score * 1000000 / (time_weight * repost_weight)

        visibility = getattr(details, 'visibility', None)
        if visibility in Visibility.invisible_choices:
            top_score = pop_score = -1

        return top_score, pop_score

    def update_score(self):
        top_score, pop_score = self.get_score()

        my_score = pop_score
        self.redis_score.set(my_score)

        if self.parent_comment_id:
            self.parent_comment.popular_replies.bump(self.id, pop_score)
            self.parent_comment.top_replies.bump(self.id, top_score)
            (_, pop_score), = self.parent_comment.popular_replies.with_scores[0:1]
            pop_id = self.parent_comment.id
        else:
            pop_id = self.id

        # Bump our thread with our thread's highest score
        # Possible optimization: Don't bump if my pop_score is lower than the thread's top pop_score
        # (maybe unnecessary update?)

        if self.reply_content_id:
            Category.ALL.popular.bump(pop_id, pop_score if self.visibility != Visibility.CURATED else -1)
            Category.ALL.top.day(self.timestamp).bump(self.id,
                                                      top_score if self.visibility != Visibility.CURATED else -1)

            if self.category:
                self.category.popular.bump(pop_id, pop_score)
                self.category.top.day(self.timestamp).bump(self.id, top_score)

            for tag in self.tags.smembers():
                for tag in self.tags.smembers():
                    Tag(tag).popular.bump(pop_id, pop_score)
                Tag(tag).top.day(self.timestamp).bump(self.id, top_score)

        if self.author:
            # Some old comments have no author
            other_top = (self.author.redis.top_posts if self.anonymous else self.author.redis.top_anonymous_posts)
            personal_top = (self.author.redis.top_anonymous_posts if self.anonymous
                            else self.author.redis.top_posts)
            personal_top.bump(self.id, top_score)
            other_top.bump(self.id, -1)

        return my_score

    def _get_url(self, prefix='p'):
        url = settings.CANVAS_SUB_SITE + '{0}/'.format(prefix) + util.base36encode(self.id)
        parent_url = self.get_parent_url(prefix=prefix)
        if parent_url:
            url = parent_url + '/reply/' + str(self.id)
        elif not url:
            # This post has no parent, nor a url (it was disabled / deleted), let's gracefully fall back.
            url = settings.CANVAS_SUB_SITE
        return url

    def get_absolute_url(self):
        return self._get_url()

    def get_parent_url(self, prefix='p'):
        if self.parent_comment_id and not self.parent_comment.is_unviewable():
            return settings.CANVAS_SUB_SITE + '{0}/'.format(prefix) + util.base36encode(self.parent_comment.id)

    def get_share_page_url(self):
        return self._get_url(prefix='d')

    def get_replies(self):
        return Comment.visible.filter(parent_comment=self).order_by('id')

    def get_deep_replies(self):
        """ Returns the entire nested tree of @replies beginning with this comment, flatly in a list. """
        comments = Comment.visible.filter(parent_comment=self.thread.op).order_by('id')
        parent_ids = set([self.id])
        replies = []
        for comment in comments:
            if comment.replied_comment_id in parent_ids:
                parent_ids.add(comment.id)
                replies.append(comment)
        return replies

    def get_remixes(self):
        """ Returns comments that remix this comment's content. """
        content = self.reply_content
        if content:
            return Comment.objects.filter(reply_content__remix_of=content).order_by('id')

    def get_sticker_counts(self):
        """ Returns a dict of counts per sticker ID. """
        return dict(CommentSticker.objects.filter(comment=self).values_list('type_id').annotate(
                count=Count('id'))) or defaultdict(lambda: 0)

    def get_sticker_from_user(self, user):
        """ Returns a Sticker instance for the one `user` gave to this comment, if any. """
        return self.get_sticker_from_user_for_comment_id(self.id, user)

    @classmethod
    def get_sticker_from_user_for_comment_id(self, comment_id, user):
        return CommentSticker.get_sticker_from_user(comment_id, user)

    def validate_sticker(self, user, sticker_type_id, skip_dupe_check=False, skip_self_check=False):
        details = stickers.details_for(sticker_type_id)

        # No stickering a moderated post.
        if self.visibility not in Visibility.public_choices:
            raise ServiceError("Moderated post.")

        # If this sticker isn't active, it can't be used anymore.
        if details.is_unusable:
            if details.seasonal:
                raise ServiceError("Seasonal is out of season")
            else:
                raise ServiceError("Invalid sticker.")

        # If this is the user of the comment they are posting, that isn't allowed.
        if not skip_self_check and self.author == user:
            raise ServiceError("No self stickering.")
        # If this user has already stickered this comment, that's an error.
        # Perform this as close to the CommentSticker creation as possible for less raciness.
        existing_sticker = self.get_user_sticker(user)
        if not skip_dupe_check and existing_sticker:
            verb = 'stickered' if settings.PROJECT == 'canvas' else 'starred'
            raise ServiceError("Already {}.".format(verb))

    def sticker(self, user, sticker_type_id, skip_dupe_check=False, skip_self_check=False, epic_message=None,
                ip='0.0.0.0'):
        """ Stickers this comment. Returns the number of remaining stickers of the given type. """
        if epic_message is None:
            epic_message = ''

        self.validate_sticker(user, sticker_type_id,
                              skip_dupe_check=skip_dupe_check, skip_self_check=skip_self_check)

        details = stickers.details_for(sticker_type_id)

        remaining = None
        sticker_details = stickers.details_for(sticker_type_id, user)
        if sticker_details.is_limited:
            from canvas import economy
            try:
                remaining = economy.consume_sticker(user, sticker_type_id)
            except economy.BusinessError, be:
                raise ServiceError(*be.args)

        comment_sticker = CommentSticker(
            comment=self,
            type_id=sticker_type_id,
            timestamp=time.time(),
            ip=ip,
            user=user,
            epic_message=epic_message,
        )
        comment_sticker.save()

        comment_sticker.force_cache()
        details = self.details.force()
        comment_logic.update_realtime(details)

        self.update_score()

        if self.author != user:
            # Bookmarklet stickers are self-stickered, and stars may be.
            send_sticker(comment_sticker)

        if settings.FEED_ENABLED:
            user.redis.feed_promotion.bump(comment_sticker)
            bgwork.defer(lambda: apps.feed.realtime.publish_promoted_comment(comment_sticker, user))

        # Create *after* send_sticker, which checks for this existance before crediting.
        comment_sticker_log = CommentStickerLog.objects.get_or_create(
            comment=self,
            user=user,
        )

        return remaining

    def downvote(self, user, downvote_sticker_type=None, ip='0.0.0.0'):
        """
        Handles downvoting a comment.

        You can pass a different sticker type as `downvote_type` to accomodate "seen this" etc.

        Returns the number of times this was downvoted (since staff get 3 votes per downvote).
        """
        if downvote_sticker_type is None:
            downvote_sticker_type = stickers.downvote.type_id
        is_staff = user.is_authenticated() and user.is_staff
        sticker_count = 3 if is_staff else 1
        for _ in xrange(sticker_count):
            self.sticker(user, downvote_sticker_type, skip_dupe_check=is_staff, ip=ip)
        return sticker_count

    def is_downvoted(self, sticker_counts=None):
        scores = defaultdict(int)
        if sticker_counts is None:
            sticker_counts = self.get_sticker_counts()

        for type_id, count in sticker_counts.iteritems():
            if stickers.details_for(type_id).value < 0:
                scores['downvotes'] += count
            else:
                scores['upvotes'] += count
        return scores['downvotes'] >= scores['upvotes'] + self.DOWNVOTES_REQUIRED

    def is_inappropriate(self):
        if self.is_offtopic() and not self.judged:
            return False
        return self.visibility == Visibility.HIDDEN

    def is_disabled(self):
        return self.visibility == Visibility.DISABLED

    def is_removed(self):
        return self.visibility == Visibility.UNPUBLISHED

    def is_visible(self):
        return Visibility.is_visible(self.visibility)

    def is_unviewable(self):
        return self.visibility in [Visibility.DISABLED, Visibility.UNPUBLISHED]

    def is_offtopic(self):
        return self.ot_hidden

    def is_collapsed(self):
        return (self.is_inappropriate()
                or self.is_offtopic()
                or self.is_downvoted()
                or self.is_disabled()
                or self.is_removed())

    def force_parent_details(self):
        """ Forces the details of the parent comment to be re-fetched. """
        if self.parent_comment:
            self.parent_comment.details.force()

    def get_user_sticker(self, user):
        if user.is_authenticated():
            return self.stickers.filter(user=user)[:1]

    @property
    def author_name(self):
        return 'Anonymous' if self.anonymous else self.author.username

    @property
    def real_author(self):
        """ Do not leak this field to the client. """
        return self.author.username

    def _details(self):
        # JSON sent to client, don't expose private details here.
        if self.replied_comment:
            replied_comment = {
                'id': self.replied_comment.id,
                'author_name': self.replied_comment.author_name,
                'url': self.replied_comment.get_absolute_url(),
            }
        else:
            replied_comment = None

        replies = self.get_replies()
        # The last reply should not be a curated reply, though replies just used the public manager.
        try:
            last_reply = replies.order_by('-id')[0]
        except IndexError:
            last_reply = None

        reply_content_details = self.reply_content.details().to_backend() if self.reply_content else {}

        sticker_counts = self.get_sticker_counts()

        repost_count = 0
        # Text replies and audio remixes are not reposts.
        if self.reply_content_id and not self.external_content.count():
            repost_count = Comment.published.filter(reply_content=self.reply_content, id__lt=self.id).count()

        tags = list(self.tags.smembers())
        if len(tags) == 0 and self.category is not None:
            self.tags.sadd(self.category.name)
            tags.append(self.category.name)

        thread_author_count = self.replies.values_list('author_id', flat=True).distinct().count()

        return {
            'author_id': self.author.id,
            'author_name': self.author_name,
            'real_author': self.real_author,
            'category': self.category.name if self.category else None,
            'category_pretty_name': self.category.pretty_name if self.category else None,
            'category_url': self.category.get_absolute_url() if self.category else None,
            'flag_counts': dict(CommentFlag.objects.filter(comment=self, undone=False).values_list('type_id').annotate(count=Count("id"))),
            'id': self.id,
            'external_content': [ec.proxy.to_client() for ec in self.external_content.all()],

            'is_collapsed': self.is_collapsed(),
            'is_disabled': self.is_disabled(),
            'is_downvoted': self.is_downvoted(sticker_counts=sticker_counts), #TODO -> CommentDetails
            'is_inappropriate': self.is_inappropriate(),
            'is_offtopic': self.is_offtopic(),
            'is_removed': self.is_removed(),

            'is_remix': self.reply_content and self.reply_content.remix_of and self.reply_content.remix_of.id != Content.DRAW_FROM_SCRATCH_PK,
            'judged': self.judged,
            'last_reply_id': last_reply.id if last_reply else None,
            'last_reply_time': last_reply.timestamp if last_reply else self.timestamp,
            'ot_hidden': self.is_offtopic(),
            'parent_id': self.parent_comment_id,
            'parent_url': self.get_parent_url(),
            'replied_comment': replied_comment,
            'reply_content': reply_content_details,
            'reply_content_id': self.reply_content_id,
            'reply_count': replies.count(),
            'reply_text': self.reply_text,
            'repost_count': repost_count,
            'share_page_url': self.get_share_page_url(),
            'staff': (not self.anonymous) and self.author.is_staff,
            'sticker_counts': sticker_counts,
            'tags': tags,
            'thread_author_count': thread_author_count,
            'thread_op_comment_id': self.thread.op.id,
            'timestamp': self.timestamp,
            'title' : self.title,
            'url': self.get_absolute_url(),
            'visibility': self.visibility,
        }

    @staticmethod
    def details_by_id(comment_id, promoter=None, ignore_not_found=False):
        from canvas.details_models import CommentDetails
        if promoter is None:
            promoter = CommentDetails
        def decorator(cached):
            cached.parent_comment = None
            if getattr(cached, 'parent_id', None):
                parent_details = Comment.details_by_id(cached.parent_id)(skip_decorator=True)
                cached.parent_comment = {'id': parent_details.id, 'reply_count': parent_details.reply_count}
            return cached

        def inner_call():
            try:
                return Comment.all_objects.get(id=comment_id)._details()
            except Comment.DoesNotExist as dne:
                if ignore_not_found:
                    return None
                raise dne

        return CachedCall(
            "comment:%s:details_v52" % comment_id,
            inner_call,
            24*60*60,
            decorator=decorator,
            promoter=promoter,
        )

    @property
    def details(self):
        return Comment.details_by_id(self.id)

    @property
    def flagged_details(self):
        #TODO: create a more elegant role syystem for comment detail types
        from canvas.details_models import FlaggedCommentDetails
        return Comment.details_by_id(self.id, promoter=FlaggedCommentDetails)

    @staticmethod
    def pins_by_id(comment_id):
        return CachedCall(
            "comment:%s:pins_v2" % comment_id,
            lambda: tuple(CommentPin.objects.filter(comment=comment_id).values_list('user_id', flat=True))
        )

    @property
    def pins(self):
        return Comment.pins_by_id(self.id)

    @property
    def followers(self):
        return RedisSet('comment:{}:followers'.format(self.id))

    @property
    def admin_info(self):
        return {
            'id': self.id,
            'score': self.score,
            'visibility': self.get_visibility_short_name(),
            'username': self.author.username if self.author else '__NONE__',
        }

    replies_channel = property(lambda self: RealtimeChannel('c:%s' % self.id, 20))

    def __repr__(self):
        return "<Comment id: %s details: %r>" % (self.id, self._details())


class InviteCode(BaseCanvasModel):
    code = CharField(max_length=32, unique=True, blank=False)
    invitee = ForeignKey(User, related_name="invited_from", blank=True, null=True, default=None)
    inviter = ForeignKey(User, related_name="sent_invites", blank=True, null=True, default=None)

    alphabet = string.letters + string.digits

    @classmethod
    def generate(cls, inviter=None):
        code = util.random_token(32)
        ic = cls(code=code, inviter=inviter)
        ic.save()
        return ic


class FacebookInvite(BaseCanvasModel):
    fb_message_id = CharField(max_length=255, unique=True)
    invited_fbid = CharField(max_length=255)

    invitee = ForeignKey(User, related_name="facebook_invited_from", blank=True, null=True, default=None)
    inviter = ForeignKey(User, related_name="facebook_sent_invites", blank=True, null=True, default=None)

    @classmethod
    def get_invite(cls, fb_uid):
        return cls.objects.filter(invited_fbid=fb_uid).order_by('-id').get_first_or_none()


class CommentSticker(BaseCanvasModel):
    comment = ForeignKey(Comment, db_index=True, related_name='stickers')
    type_id = IntegerField()
    timestamp = UnixTimestampField()
    ip = IPAddressField()
    user = ForeignKey(User, db_index=True, blank=True, null=True, default=None)
    epic_message = CharField(max_length=knobs.STICKER_MESSAGE_MAX_LENGTH, blank=True, default='')

    @property
    def sticker(self):
        return stickers.get(self.type_id)

    @property
    def cost(self):
        return stickers.get(self.type_id).cost

    def __repr__(self):
        d = dict(comment=str(self.comment), type_id=self.type_id)
        return str(d)

    def force_cache(self):
        self._stickers_on_comment(self.comment_id).force()

    @classmethod
    @memoize(key=lambda cls, comment_id: 'comment:{}:sticker_details_v1'.format(comment_id), time=7*24*60*60)
    def _stickers_on_comment(cls, comment_id):
        comment = Comment.all_objects.get(id=comment_id)
        return dict((str(sticker.user_id), sticker.type_id,) for sticker in comment.stickers.all())

    @classmethod
    def get_sticker_from_user(cls, comment_id, user):
        """ Returns a `Sticker` instance. Tries to avoid hitting the DB. """
        if user.is_authenticated():
            type_id = cls._stickers_on_comment(comment_id)().get(str(user.id))
            if type_id is not None:
                return stickers.get(type_id)


class CommentStickerLog(BaseCanvasModel):
    comment = ForeignKey(Comment, db_index=True)
    user = ForeignKey(User, db_index=True)


class CommentFlag(BaseCanvasModel):
    comment = ForeignKey(Comment, db_index=True, related_name='flags')
    type_id = IntegerField()
    timestamp = UnixTimestampField()
    ip = IPAddressField()
    user = ForeignKey(User, related_name='flags')
    undone = BooleanField(db_index=True, default=False)

    flag_channel = RealtimeChannel('flags', 1)

    @classmethod
    def update_channel(cls):
        cls.flag_channel.publish({'flagged': Comment.unjudged_flagged().count()})


class CommentPin(BaseCanvasModel):
    comment = ForeignKey(Comment)
    timestamp = UnixTimestampField()
    user = ForeignKey(User)
    auto = BooleanField(default=False)


class ModerationLog(BaseCanvasModel):
    moderator = ForeignKey(User, null=True)
    timestamp = UnixTimestampField()
    note = TextField()

    class Meta(object):
        abstract = True

    @classmethod
    def append(cls, **kwargs):
        if not 'timestamp' in kwargs:
            kwargs['timestamp'] = Now()
        instance = cls(**kwargs)
        instance.save()

    @property
    def log_link(self):
        return None


class CommentModerationLog(ModerationLog):
    user = ForeignKey(User, related_name='moderated_comments_log')

    comment = ForeignKey(Comment)
    visibility = IntegerField()

    @property
    def visability_name(self):
        return Visibility.short_names[self.visibility]

    log_type = 'comment'
    log_template = 'comment_log_entry.django.html'


class UserModerationLog(ModerationLog):
    user = ForeignKey(User, related_name='moderation_log')

    action = IntegerField()

    log_type = 'user'
    log_template = 'user_log_entry.django.html'

    class Actions(object):
        warn = 1
        confirm_warning = 2
        deactivate_user = 3
        reactivate_user = 4

    @property
    def action_name(self):
        for key, value in UserModerationLog.Actions.__dict__.items():
            if value == self.action:
                return key


class UserWarning(BaseCanvasModel):
    user = ForeignKey(User, related_name='user_warnings')
    issued = UnixTimestampField()
    viewed = UnixTimestampField(default=0)
    confirmed = UnixTimestampField(default=0)
    custom_message = TextField()
    stock_message = IntegerField(default=0)
    comment = ForeignKey(Comment, null=True, blank=True, default=None)
    disable_user = BooleanField(default=False)

    @staticmethod
    def _sandbox_user(user):
        user.redis.user_kv.hset('sandbox', '/warning')

    @classmethod
    def send_stock_comment_warning(cls, comment, stock_id, mod):
        cls(
            user=comment.author,
            comment=comment,
            stock_message=stock_id,
            issued=Now(),
        ).save()

        UserModerationLog.append(
            user=comment.author,
            moderator=mod,
            action=UserModerationLog.Actions.warn,
        )

        cls._sandbox_user(comment.author)
        comment.author.userinfo.details.force()

    @classmethod
    def send_custom_warning(cls, user, message, mod, deactivate_user=False):
        cls(
            user=user,
            custom_message=message,
            issued=Now(),
            disable_user=deactivate_user,
        ).save()

        UserModerationLog.append(
            user=user,
            moderator=mod,
            action=UserModerationLog.Actions.deactivate_user if deactivate_user else UserModerationLog.Actions.warn,
            note="Custom message: " + message,
        )

        cls._sandbox_user(user)
        user.userinfo.details.force()

    def confirm(self):
        self.confirmed = Now()
        self.save()

        UserModerationLog.append(
            user=self.user,
            moderator=self.user,
            action=UserModerationLog.Actions.confirm_warning,
        )

    @property
    def warning_text(self):
        return UserWarningStock.warnings.get(self.stock_message) + self.custom_message


#####################
# Email Subscription

class EmailUnsubscribe(BaseCanvasModel):
    """
    Note that we do not use this model any longer. Email unsubscriptions are handled by UserKV.subscriptions.
    This was a legacy model to hold blacklisted emails. Now emails are tied to a specific user.
    """
    email = CharField(max_length=255, unique=True)


def subscribe_newsletter(email):
    # Find and delete any EmailUnsubscribe objects for this email.
    unsubscribe = EmailUnsubscribe.objects.get_or_none(email=email)
    if unsubscribe:
        unsubscribe.delete()

def unsubscribe_newsletter(email):
    unsubscribe = EmailUnsubscribe.objects.get_or_create(email=email)

def update_unsubscription(sender, old_email=None, new_email=None, user=None, **kwargs):
    """ Updates the corresponding EmailUnsubscribe object, if any, when a user changes their email address. """
    unsubscribe = EmailUnsubscribe.objects.get_or_none(email=old_email)
    if unsubscribe:
        unsubscribe.email = new_email
        unsubscribe.save()
user_email_changed.connect(update_unsubscription, dispatch_uid='update_unsubscription')

def send_email(to_email, from_email, subject, template_name, context):
    # Don't email unsubscribed email addresses.
    if EmailUnsubscribe.objects.filter(email=to_email).exists():
        return False
    # Don't email deactivated users.
    if User.objects.filter(email=to_email, is_active=False).exists():
        return False

    unsub_url =  ("https://example.com/unsubscribe?"
                  + urllib.urlencode({'email': to_email, 'token': util.token(to_email)}))
    context['unsubscribe_url'] = mark_safe(unsub_url)

    text = render_to_string('email/%s.txt' % template_name, context)
    html = render_to_string('email/%s.html' % template_name, context)

    mail = EmailMultiAlternatives(subject, text, from_email, [to_email])
    mail.attach_alternative(html, "text/html")
    try:
        mail.send()
    except Exception, e:
        if hasattr(e, 'error_message') and e.error_message == "Address blacklisted.":
            # This email address has issued a bounce in the last 14 days, Amazon will not let us email them again
            return
        else:
            # Resend once for transient network issues
            mail.send()


class WelcomeEmailRecipient(BaseCanvasModel):
    """ Used to record users who have received the 24-hour digest email. """
    recipient = ForeignKey(User, unique=True)


class UserWarningStock(object):
    warnings = {
        1: "The following post of yours was hidden by a Canvas Team member because it violates the Code of Conduct",
        2: ("The following post of yours has been disabled by a Canvas Team member because it violates the "
            "Code of Conduct"),
    }


class Gender(object):
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2

    @classmethod
    def from_string(cls, string):
        string = string.lower()
        return {
            'male': cls.MALE,
            'female': cls.FEMALE
        }.get(string, cls.UNKNOWN)


class FacebookUser(BaseCanvasModel):
    user = OneToOneField(User, null=True, blank=True)
    fb_uid = BigIntegerField(unique=True, blank=False) # Because this is unique, it can't go into UserInfo
    email = CharField(max_length=255)
    first_name = CharField(max_length=255)
    last_name = CharField(max_length=255)
    last_invited = UnixTimestampField(default=0)
    gender = PositiveSmallIntegerField(default=0)

    def __repr__(self):
        return "<FacebookUser: %s %s (fb_uid: %s)>" % (self.first_name, self.last_name, self.fb_uid)

    def _delete_if_login_revoked(self, fb, fb_user):
        """ Returns whether it was revoked or not. """
        if not fb.fql('SELECT is_app_user FROM user WHERE uid={}'.format(fb_user['id']))[0]['is_app_user']:
            self.delete()
            return True
        return False

    @classmethod
    def create_from_fb_user(cls, fb, fb_user):
        fb_user_info = fb.get_object(fb_user['id'])

        return cls.objects.create(
            fb_uid=fb_user['id'],
            email=fb_user_info.get('email', ''),
            first_name=fb_user_info['first_name'],
            last_name=fb_user_info['last_name'],
            gender=Gender.from_string(fb_user_info.get('gender', '')),
            user=None
        )

    @classmethod
    def save_facebook_user(cls, request):
        fb_user, fb = util.get_fb_api(request)

        cls.create_from_fb_user(fb, fb_user)

    @classmethod
    def _get_fb_user_from_access_token(cls, access_token):
        fb = GraphAPI(access_token)
        try:
            fb_user = fb.get_object('me')
            return fb, fb_user
        except GraphAPIError:
            raise ServiceError("There appears to be an issue communicating with Facebook. "
                               "Please try logging in again.")

    @classmethod
    def create_from_access_token(cls, access_token):
        fb, fb_user = cls._get_fb_user_from_access_token(access_token)
        return cls.create_from_fb_user(fb, fb_user)

    @classmethod
    def get_from_access_token(cls, access_token):
        fb, fb_user = cls._get_fb_user_from_access_token(access_token)
        return cls.objects.get(fb_uid=fb_user['id'])

    @classmethod
    def get_or_create_from_access_token(cls, access_token):
        try:
            return cls.create_from_access_token(access_token)
        except IntegrityError:
            return cls.get_from_access_token(access_token)

    @staticmethod
    def request_invite(request):
        try:
            FacebookUser.save_facebook_user(request)
        except IntegrityError:
            pass

    def notify_friends_of_signup(self, access_token):
        fb = GraphAPI(access_token)
        friends = fb.get_object('me/friends')['data']
        fb_friends = FacebookUser.objects.filter(fb_uid__in=[friend['id'] for friend in friends])
        Actions.facebook_friend_joined(self.user, fb_friends)


class BestOf(BaseCanvasModel):
    comment = ForeignKey(Comment, related_name="best_of")
    timestamp = UnixTimestampField()
    chosen_by = ForeignKey(User)
    category = ForeignKey(Category, related_name="best_of", blank=True, null=True, default=None)


class UserInfo(Model):
    user = OneToOneField(User)
    free_invites = IntegerField(default=10)
    post_anonymously = BooleanField(default=False)
    enable_timeline = BooleanField(default=True)
    enable_timeline_posts = BooleanField(default=False)
    invite_bypass = CharField(max_length=255, blank=True, default='')
    profile_image = ForeignKey('Comment', null=True) # Used by example.com.
    avatar = ForeignKey('Content', null=True) # Used by DrawQuest.
    facebook_id = CharField(max_length=100, blank=True, null=True)
    bio_text = CharField(max_length=2000, blank=True)

    is_qa = BooleanField(default=False)

    @classmethod
    def facebook_is_unused(cls, facebook_id):
        if facebook_id:
            return not cls.objects.filter(facebook_id=facebook_id).exists()
        return True

    @property
    def cache_key(self):
        """ The cache key used to store the details of this object in cache. Bump up the rev as needed. """
        return "userinfo:%s:details_v6" % self.user_id

    @property
    @memoize(key=lambda self: self.cache_key, time=24*60*60)
    def details(self):
        founded = list(self.user.founded_groups.values_list('id', flat=True))
        return {
            'group_mod': Category.objects.filter(founder=self.user).exists(),
            'founded': founded,
            'moderatable': founded + list(Category.objects.filter(moderators=self.user).values_list('id', flat=True)),
            'warnings': self.user.user_warnings.filter(disable_user=False).count(),
            'bans': self.user.user_warnings.filter(disable_user=True).count(),
            'is_staff': self.user.is_staff
        }


def get_content_details_for_items(items):
    contents = set(item.content for item in items)
    details = [content.details() for content in contents if content]
    return [detail for detail in details if detail is not None]


#TODO delete, unused.
class StashContent(BaseCanvasModel):
    content = ForeignKey(Content)
    user = ForeignKey(User, db_index=True)


class RemixPlugin(BaseCanvasModel):
    author = ForeignKey(User)
    timestamp = UnixTimestampField(default=0)
    s3md5 = CharField(max_length=255)

    def get_url(self):
        return '/script/' + util.base36encode(self.id)

    @classmethod
    def get_from_short_id(cls, short_id):
        return get_object_or_404(cls.objects, id=get_mapping_id_from_short_id(short_id))


class APIApp(BaseCanvasModel):
    name = CharField(max_length=255, unique=True)


class APIAuthToken(BaseCanvasModel):
    token = CharField(max_length=40, unique=True)
    user = ForeignKey(User)
    app = ForeignKey(APIApp)

    @classmethod
    def generate(cls, user, app):
        auth_token = cls(token=util.random_token(40), user=user, app=app)
        auth_token.save()
        return auth_token

    @classmethod
    def get_or_generate(cls, user, app):
        return cls.objects.get_or_none(user=user, app=app) or cls.generate(user, app)

    class Meta(object):
        unique_together = ('user', 'app')


class UserAchievementKV(object):
    """
    To add and use a new achievement:
        1. add it to ACHIEVEMENTS below
        2. call user.kv.achievements.achieve(newnumber) where appropriate
        3. check with user.kv.achievements[newnumber].get()
    """
    ACHIEVEMENTS = {
        0: ('hipster',          "Unlocked the hipster sticker",),
        1: ('audio_remixer',    "Created an audio remix",),
        2: ('monster_top',      "Started a monster",),
        3: ('monster_bottom',   "Completed a monster",),
        4: ('ten_followers',    "Gained 10 followers",),
        5: ('following_ten',    "Followed 10 people",),
    }

    #TODO migrate redis data to use names instead of IDs, then we can use this exclusively.
    ACHIEVEMENTS_BY_NAME = dict((v[0], k,) for k,v in ACHIEVEMENTS.items())

    @classmethod
    def DEFINITION(cls):
        return dict(('achievement:%s:achieved' % id, hbool(),) for id in cls.ACHIEVEMENTS)

    def __init__(self, hash):
        self.hash = hash

    def __getitem__(self, achievement_name):
        achievement_id = self.ACHIEVEMENTS_BY_NAME[achievement_name]
        return HashSlot(self.hash, 'achievement:%s:achieved' % achievement_id)

    def by_id(self, achievement_id):
        return self[self.ACHIEVEMENTS[achievement_id][0]]

    def achieve_by_id(self, achievement_id):
        self.by_id(achievement_id).setnx(time.time())

    def achieve(self, achievement_name):
        self.achieve_by_id(self.ACHIEVEMENTS_BY_NAME[achievement_name])


class UserStickerKV(object):
    @classmethod
    def DEFINITION(cls):
        DEFINITION = {}
        for sticker in stickers.get_limited_stickers():
            DEFINITION[cls.make_key(sticker)] = hint(0)

        for sticker in filter(lambda sticker: sticker.is_limited_inventory, stickers.all_stickers()):
            DEFINITION[cls.purchased_marker_key(sticker)] = hint(0)
        return DEFINITION

    def __init__(self, hash):
        self.hash = hash

    @property
    def currency(self):
        """ The currency is the #1 sticker. It has slot #7. """
        return self.__getitem__(7)

    def __getitem__(self, sticker_id):
        # sticker_id could be a Sticker or an int id. Convert it to a sticker.
        sticker = stickers.get(sticker_id)
        return HashSlot(self.hash, 'sticker:%s:count' % sticker.type_id)

    def add_limited_sticker(self, sticker, count=0):
        """ Adds a limited sticker to the user's sticker kv. """
        self.hash.set(UserStickerKV.make_key(sticker), int(count))

    @classmethod
    def purchased_marker_key(cls, sticker):
        """ Encapsulates the string key for a Sticker purchase marker. """
        return "sticker:%s:purchase_count" % sticker.type_id

    def mark_sticker_purchased(self, sticker):
        # Note that we use an integer rather than a bool in case we decide to allow users to purchase
        # more than one sticker, but less than a max. The max can be set in did_purchase.
        self.hash.set(self.purchased_marker_key(sticker), 1)

    def did_purchase(self, sticker):
        """
        Returns True if the user has bought this sticker before.

        This is only useful for limited inventory stickers because we want to restrict them to one per user.
        """
        try:
            return self.hash.get(self.purchased_marker_key(sticker)) > 0
        except KeyError:
            return False

    @classmethod
    def make_key(cls, sticker):
        return "sticker:%s:count" % sticker.type_id

    def get(self, key):
        return self[key]


class BaseUserKV(object):
    def __init__(self):
        self.stickers = UserStickerKV(self)
        self.achievements = UserAchievementKV(self)
        self.subscriptions = UserNotificationsSubscription(self)


# Must come after stickers are statically defined
class UserKV(RedisCachedHash, BaseUserKV):
    """
    Attributes are HashSlots, so you'll need to call .get() to get their value.

    You can also set, increment, and other redis concepts.

    Note the DEFINITION is a CLASS CONSTANT. It serves to provide sane defaults for all possible keys. So do not try
    to change it at runtime except to add new stickers in tests.
    """
    DEFINITION = {
        'post_pending_signup_url': hstr(),
        'daily_free_timestamp': hfloat(),

        'last_sticker_comment_id': hint(),
        'last_sticker_timestamp': hfloat(),
        'last_sticker_type_id': hint(),

        'pinned_lastviewed': hfloat(),
        'pinned_unseen': hint(),

        'feed_last_viewed': hfloat(),
        'feed_unseen': hint(),

        'activity_stream_last_viewed': hfloat(),
        'activity_stream_unseen': hint(),

        'has_unseen_daily_free_stickers': hbool(),

        'secure_only': hbool(),
        'labs:root_is_following': hbool(),
        'labs:hide_reposts': hbool(),
        'labs:hide_userpage_from_google': hbool(),

        'saw_feed_tutorial': hbool(),

        'inviter': hint(),

        'sticker_inbox': hint(),
        'sticker_level': hint(),
        'stickers_received': hint(),

        'time_dilation': hfloat(),
        'time_dilation_start': hfloat(),
        'time_dilation_end': hfloat(),
    }

    # Initialize the keys for limited stickers. The default count is zero.
    DEFINITION.update(UserStickerKV.DEFINITION())
    DEFINITION.update(UserAchievementKV.DEFINITION())
    DEFINITION.update(UserNotificationsSubscription.DEFINITION())

    def __init__(self, user):
        RedisCachedHash.__init__(self, 'user:%s:info' % user.id)
        BaseUserKV.__init__(self)


class LoggedOutSlot(object):
    def __init__(self, default):
        self.default = default

    def get(self):
        return self.default


class LoggedOutKV(BaseUserKV):
    def __init__(self):
        BaseUserKV.__init__(self)

    def __getattr__(self, name):
        return HashSlot(self, name)

    def get(self, key):
        return UserKV.DEFINITION[key][2]


def flagged_comments():
    """ Returns CommentDetails instances with extra private fields exposed to the client. """
    CommentFlag.update_channel()

    # Then regardless, show anything still flagged.
    if settings.PROJECT == 'canvas':
        comments = Comment.unjudged_flagged()
    elif settings.PROJECT == 'drawquest':
        from drawquest.apps.quest_comments.models import QuestComment
        comments = QuestComment.unjudged_flagged()
    comments = comments.order_by('id')

    details = CachedCall.multicall([x.flagged_details for x in comments])

    for comment, detail in zip(comments, details):
        fields = {
            'visibility': comment.get_visibility_short_name(),
            'flag_count': sum(detail.flag_counts.values()),
            'real_username': comment.author.username,
            'first_flag': comment.flags.order_by('-id')[0].timestamp,
            'user_warning_count': comment.author.userinfo.details()['warnings'],
            'user_ban_count': comment.author.userinfo.details()['bans'],
        }
        #TODO this is a hack until we have a better API for extending to_client fields in CommentDetails objects.
        for key, val in fields.iteritems():
            setattr(detail, key, val)
        detail.to_client().update(fields)
    return sorted(details, key = lambda d: -d.flag_count)


# Required for side effects of signal handling
import apps.mobile.signals

