from collections import OrderedDict
from functools import partial
import itertools

from apps.comment_hiding.redis_models import is_dismissable
from canvas import stickers, knobs, util
from canvas.details_models import CommentDetails
from canvas.redis_models import redis, RedisLastBumpedBuffer
from django.conf import settings


class _KeyedFeedBufferBase(RedisLastBumpedBuffer):
    def __init__(self, key_id, size):
        key = self.get_key(key_id)
        super(_KeyedFeedBufferBase, self).__init__(key, size, getter=self._GETTER)

    @classmethod
    def get_key(cls, key_id):
        return cls._KEY.format(key_id)

    def __contains__(self, member):
        return redis.zrank(self.key, member) is not None


class UserFeedSourceBuffer(_KeyedFeedBufferBase):
    """ Holds Comment IDs. """
    _KEY = 'user:{}:feed_source'
    _GETTER = int

    def bump(self, comment):
        """
        Takes a Comment or CommentDetails instance.

        Will safely reject comments that aren't visible in the feed.
        """
        if hasattr(comment, 'details'):
            comment = comment.details()

        item = {
            'type': 'post',
            'comment': comment,
        }

        if not visible_in_feed(item):
            return

        super(UserFeedSourceBuffer, self).bump(comment.id)

class ThreadFeedSourceBuffer(_KeyedFeedBufferBase):
    """ Holds Comment IDs """
    _KEY = 'comment:{}:feed_source'
    _GETTER = int

    def bump(self, comment):
        """
        Takes a Comment or CommentDetails instance.

        Will safely reject comments that aren't visible in the feed.
        """
        if hasattr(comment, 'details'):
            comment = comment.details()

        item = {
            'type': 'thread',
            'comment': comment,
        }

        if not visible_in_feed(item):
            return

        super(ThreadFeedSourceBuffer, self).bump(comment.id)


class UserFeedPromotionBuffer(_KeyedFeedBufferBase):
    """ Holds CommentSticker IDs. """
    _KEY = 'user:{}:feed_promotion'
    _GETTER = util.loads

    def bump(self, comment_sticker):
        """ Will safely reject stickers that aren't epic enough. """
        if comment_sticker.cost < knobs.FEED_PROMOTION_STICKER_COST_THRESHOLD:
            return

        data = {
            'username': comment_sticker.user.username,
            'sticker_type_id': comment_sticker.type_id,
            'comment_id': comment_sticker.comment.id,
        }
        super(UserFeedPromotionBuffer, self).bump(util.backend_dumps(data), coerce=False)


def _tighten_earliest_timestamp_cutoff(earliest_timestamp_cutoff):
    if earliest_timestamp_cutoff is None:
        return
    return float(earliest_timestamp_cutoff) - 0.00001

def visible_in_feed(item, earliest_timestamp_cutoff=None):
    comment = item['comment']
    if not comment.has_content():
        return False
    if comment.category in settings.HIDDEN_GROUPS:
        return False

    try:
        if float(item['ts']) > float(earliest_timestamp_cutoff):
            return False
    except (KeyError, TypeError,):
        pass

    return comment.is_visible()


def not_self_authored(item, username=None):
    comment = item['comment']
    return username != comment.real_author

def sticky_threads(user):
    from apps.sticky_threads.models import get_sticky_threads_from_cache

    hidden_comments = map(int, user.redis.hidden_comments.smembers())
    items = [{'type': 'sticky_thread', 'comment': CommentDetails.from_id(id_), 'comment_id': id_, 'text': text}
             for id_, text in get_sticky_threads_from_cache()
             if id_ not in hidden_comments]

    for item in items:
        _add_viewer_sticker_to_item(item, user)

    return items

def _promotion_stickers(following_ids):
    feed_promotion_keys = [UserFeedPromotionBuffer.get_key(user_id) for user_id in following_ids]

    return [(util.loads(promotion), score,)
            for promotion, score
            in redis.zunion(feed_promotion_keys, withscores=True, transaction=False)]

def _promotion_stickers_iterator(following_ids):
    """
    Iterates over comment_id, group pairs.

    group is a list of pairs of sticker, timestamp
    """
    for comment_id, group in itertools.groupby(_promotion_stickers(following_ids), lambda e: e[0]['comment_id']):
        yield comment_id, list(group)

def promoted_comments(user, earliest_timestamp_cutoff=None, comments_to_skip=set()):
    following_ids = user.redis.following.smembers()

    earliest_timestamp_cutoff = _tighten_earliest_timestamp_cutoff(earliest_timestamp_cutoff)

    # Get top sticker and earliest sticker per comment.
    promotions = []
    for comment_id, group in _promotion_stickers_iterator(following_ids):
        if comment_id in comments_to_skip:
            continue

        top, _      = max(group, key=lambda e: stickers.get(e[0]['sticker_type_id']).cost)
        _, first_ts = min(group, key=lambda e: e[1])

        if earliest_timestamp_cutoff is not None and float(first_ts) > float(earliest_timestamp_cutoff):
            continue

        promotions.append({
            'type': 'promotion',
            'comment_id': comment_id,
            'ts': first_ts,
            'sticker_type_id': top['sticker_type_id'],
            'username': top['username'],
        })

    return promotions

def users_promoted_comment_at(user_ids, comment):
    """
    Returns the unix timestamp of when `comment` was first promoted by one of `user_ids`, or `None` if they haven't.
    """
    first_ts = None
    for comment_id, group in _promotion_stickers_iterator(user_ids):
        if comment_id == comment.id:
            _, first_ts = min(group, key=lambda e: e[1])
            break
    return first_ts

def _add_viewer_sticker_to_item(item, user):
    from canvas.models import CommentSticker
    item['viewer_sticker'] = CommentSticker.get_sticker_from_user(item['comment'].id, user)

def feed_for_user(user, earliest_timestamp_cutoff=None, per_page=knobs.FEED_ITEMS_PER_PAGE, items_to_skip=set()):
    following_ids = user.redis.following.smembers()
    followed_thread_ids = user.redis.followed_threads.smembers()

    if not following_ids and not followed_thread_ids:
        return []

    feed_source_keys = [UserFeedSourceBuffer.get_key(user_id) for user_id in following_ids]
    feed_thread_source_keys = [ThreadFeedSourceBuffer.get_key(thread_id) for thread_id in followed_thread_ids]

    thread_posts = [{'type': 'thread', 'comment_id': id_, 'ts': score}
             for id_, score in
             redis.zunion(feed_thread_source_keys,
                          withscores=True, transaction=False,
                          max_score=_tighten_earliest_timestamp_cutoff(earliest_timestamp_cutoff))]

    posts = [{'type': 'post', 'comment_id': id_, 'ts': score}
             for id_, score in
             redis.zunion(feed_source_keys,
                          withscores=True, transaction=False,
                          max_score=_tighten_earliest_timestamp_cutoff(earliest_timestamp_cutoff))]

    posts += thread_posts

    promotions = promoted_comments(user,
                                   earliest_timestamp_cutoff=earliest_timestamp_cutoff,
                                   comments_to_skip=set(post['comment_id'] for post in posts))

    # Sort by recency.
    items = sorted(itertools.chain(posts, promotions), key=lambda e: float(e['ts']), reverse=True)

    # Skip items as requested and skip comments the user has hidden.
    hidden_comments = user.redis.hidden_comments.smembers()
    comments_to_skip = set(str(item['comment_id']) for item in items_to_skip) | hidden_comments

    # Remove dupes.
    items = OrderedDict((str(item['comment_id']), item,) for item in items
                        if str(item['comment_id']) not in comments_to_skip).values()

    # Pagination.
    items = items[:per_page]

    # Promote comment_id to CommentDetails.
    details = CommentDetails.from_ids([item['comment_id'] for item in items])
    for i, item in enumerate(items):
        item['comment'] = details[i]

    # Hide hidden threads.
    items = user.redis.hidden_threads.filter_comments(items, comment_key=lambda item: item['comment'])

    # Prune items that shouldn't show up in this feed.
    items = filter(partial(visible_in_feed, earliest_timestamp_cutoff=earliest_timestamp_cutoff), items)
    items = filter(partial(not_self_authored, username=user.username), items)

    # Determine whether each item is dismissable by user.
    def item_is_dismissable(item):
        if item['type'] == 'promotion' and item['username'].lower() == 'canvas':
            return False
        return item['type'] != 'sticky_thread' and is_dismissable(item['comment'], user)

    for item in items:
        item['is_dismissable'] = item_is_dismissable(item)

    # Add viewer_sticker to items.
    for item in items:
        _add_viewer_sticker_to_item(item, user)

    return items

