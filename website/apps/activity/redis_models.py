from datetime import date
import itertools

from django.conf import settings
from django.db.models import *

from apps.activity.base_activity import BaseActivity
from apps.canvas_auth.models import User
from canvas import util
from canvas.redis_models import RedisLastBumpedBuffer
from drawquest.apps.drawquest_auth.details_models import UserDetails
from services import Services


class StickerActivity(BaseActivity):
    TYPE = 'sticker'
    FORCE_ANONYMOUS = True

    @classmethod
    def _from_sticker(cls, comment_sticker):
        from canvas.details_models import CommentDetails
        comment_details = CommentDetails.from_id(comment_sticker.comment_id)
        data = {
            'comment_sticker_type_id': comment_sticker.type_id,
            'details_url': comment_details.linked_url,
        }
        if comment_details.reply_content:
            try:
                data['thumbnail_url'] = comment_details.reply_content.get_absolute_url_for_image_type('small_square')
            except KeyError:
                pass
        return data

    @classmethod
    def from_sticker(cls, actor, comment_sticker):
        return cls(cls._from_sticker(comment_sticker), actor=actor)


class EpicStickerActivity(StickerActivity):
    TYPE = 'epic_sticker'
    FORCE_ANONYMOUS = False

    @classmethod
    def from_sticker(cls, actor, comment_sticker):
        data = cls._from_sticker(comment_sticker)
        data['reward_stickers'] = comment_sticker.sticker.cost

        message = comment_sticker.epic_message
        if message:
            #TODO delete 'tooltip' once we switch to the new activity feed
            data['tooltip'] = u'"{0}" - from {1}'.format(message, comment_sticker.user.username)
            data['personal_message']  = message

        return cls(data, actor=actor)


class LevelUpActivity(BaseActivity):
    TYPE = 'level_up'
    FORCE_ANONYMOUS = False


class FollowedByUserActivity(BaseActivity):
    TYPE = 'followed_by_user'
    FORCE_ANONYMOUS = False

    @classmethod
    def from_user(cls, actor, followee):
        data = {
            'details_url': '/user/{0}'.format(actor.username),
            'is_actor_anonymous': False,
            'followee': UserDetails.from_id(followee.id),
        }
        return cls(data, actor=actor)

    def followee_is_following_actor(self):
        return User.objects.get(id=self._data['followee']['id']).is_following(self.actor['id'])


class _FromCommentMixin(object):
    @classmethod
    def from_comment(cls, actor, comment):
        comment_details = comment.details()
        data = {
            'details_url': comment_details.linked_url,
            'is_actor_anonymous': comment.anonymous,
            'thread_title': comment.thread.op.title,
        }
        if comment_details.reply_content:
            try:
                data['thumbnail_url'] = comment_details.reply_content.get_absolute_url_for_image_type('small_square')
            except KeyError:
                pass
        return cls(data, actor=actor)


class RemixInviteActivity(BaseActivity, _FromCommentMixin):
    TYPE = 'remix_invite'


class ThreadPromotedActivity(BaseActivity, _FromCommentMixin):
    TYPE = 'thread_promoted'
    FORCE_ANONYMOUS = False


class PostPromotedActivity(BaseActivity, _FromCommentMixin):
    TYPE = 'post_promoted'
    FORCE_ANONYMOUS = False


class MonsterRemixInviteActivity(BaseActivity):
    TYPE = 'remix_invite_monster'

    @classmethod
    def from_comment(cls, actor, comment):
        comment_details = comment.details()
        data = {
            'details_url': "/monster/{0}/complete".format(comment_details.short_id()),
            'is_actor_anonymous': comment.anonymous,
            'thumbnail_url': '/static/img/tiny_monster_mascot.png',
        }
        return cls(data, actor=actor)


class ThreadReplyActivity(BaseActivity, _FromCommentMixin):
    TYPE = 'thread_reply'


class RemixActivity(ThreadReplyActivity):
    TYPE = 'remix'


class ReplyActivity(ThreadReplyActivity):
    TYPE = 'reply'


class DailyFreeStickersActivity(BaseActivity):
    TYPE = 'daily_free_stickers'
    FORCE_ANONYMOUS = False


def _load_activity_types():
    from django.conf import settings
    from django.core import exceptions
    from django.utils.importlib import import_module

    types = []
    for type_path in settings.ACTIVITY_TYPE_CLASSES:
        try:
            dot = type_path.rindex('.')
        except ValueError:
            raise exceptions.ImproperlyConfigured("%s isn't a module" % type_path)
        type_module, type_classname = type_path[:dot], type_path[dot+1:]
        try:
            mod = import_module(type_module)
        except ImportError, e:
            raise exceptions.ImproperlyConfigured('Error importing activity type %s: "%s"' % (type_module, e))
        try:
            type_class = getattr(mod, type_classname)
        except AttributeError:
            raise exceptions.ImproperlyConfigured('Activity type module "%s" does not define a "%s" class'
                                                    % (type_module, type_classname))

        types.append(type_class)

    return types


class ActivityStream(object):
    ACTIVITY_TYPES = {cls.TYPE: cls for cls in _load_activity_types()}

    def __init__(self, user_id, stream_size=1000, activity_types=ACTIVITY_TYPES):
        self._user_id = user_id
        self._activity_types = activity_types
        self._buffer = RedisLastBumpedBuffer('user:{}:stream_v6'.format(user_id), stream_size,
                                             getter=self._make_activity)
        self._read = RedisLastBumpedBuffer('user:{}:stream_read'.format(user_id), stream_size)

    def _make_activity(self, activity_id):
        from apps.activity.models import Activity
        activity_data = Activity.details_by_id(activity_id)()
        try:
            return self._activity_types[activity_data['activity_type']](activity_data)
        except KeyError:
            return None

    def __iter__(self):
        for item in self._buffer:
            if item is not None:
                yield item

    def valid_activity_type(self, activity_type):
        return activity_type in self.ACTIVITY_TYPES

    def iter_until(self, timestamp):
        """ Returns an iterator over the activities up until `timestamp`. """
        return itertools.dropwhile(lambda activity: activity.timestamp >= float(timestamp), self._buffer)
    
    def _invalidate_cache(self):
        if settings.PROJECT == 'drawquest':
            from apps.activity import api
            api.activity_stream_items.delete_cache(None, None, user=self._user_id)

    def push(self, activity_item):
        from apps.activity.models import Activity

        if not hasattr(activity_item, 'id'):
            dbactivity = Activity.from_redis_activity(activity_item)
            id_ = dbactivity.id
        else:
            id_ = activity_item.id
        self._buffer.bump(id_, coerce=False)

        self._invalidate_cache()

    def mark_read(self, activity_id):
        from canvas.models import UserRedis
        user_redis = UserRedis(self._user_id)

        activity = self._make_activity(activity_id)

        try:
            if (activity_id not in self._read
                    and activity_id in set(item.id for item in self._buffer)
                    and float(user_redis.user_kv.hget('activity_stream_last_viewed')) < float(activity.timestamp)):
                user_redis.user_kv.hincrby('activity_stream_unseen', -1)
        except TypeError:
            pass

        self._read.bump(activity_id)

    def mark_all_read(self):
        from canvas.models import UserRedis
        user_redis = UserRedis(self._user_id)

        user_redis.user_kv.hset('activity_stream_last_viewed', Services.time.time())
        user_redis.user_kv.hset('activity_stream_unseen', 0)
        user_redis.activity_stream_channel.publish('activity_stream_viewed')

    def has_read(self, activity_id):
        activity_id = int(activity_id)

        from canvas.models import UserRedis
        user_redis = UserRedis(self._user_id)

        activity = self._make_activity(activity_id)

        if activity_id in self._read:
            return True

        try:
            return float(user_redis.user_kv.hget('activity_stream_last_viewed')) >= float(activity.timestamp)
        except TypeError:
            return False

