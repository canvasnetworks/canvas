import datetime
import math
import time

from django.core.exceptions import PermissionDenied
from django.http import Http404

from apps.comment_hiding.redis_models import remove_hidden_comment_ids, is_dismissable
from apps.tags.models import Tag
from canvas import stickers, util, knobs
from canvas.cache_patterns import CachedCall
from canvas.models import Comment, Category, User, Metrics, Content, Visibility
from canvas.redis_models import redis, gen_temp_key, RedisLastBumpedBuffer, RedisList
from canvas.view_helpers import wrap_comments
from configuration import Config


class TileDetails(object):
    """
    This contains the last reply in a thread, as well as the OP of that thread.

    If the thread only has the OP without any replies, this will contain the details of the OP comment only.
    """
    def __init__(self, comment_details):
        self.pins = None
        self._comment_details = comment_details

    @classmethod
    def from_comment_id(cls, comment_id):
        details = Comment.details_by_id(comment_id)()
        return cls(details)

    @classmethod
    def from_queryset_with_pins(cls, comments):
        """
        Returns a list of tile details.

        This will preload this details object with pins, which is more efficient than loading them on demand.
        """
        # Grab the pin data for this user and these comments.
        details, pins = CachedCall.many_multicall([cmt.details        for cmt in comments],
                                                  [cmt.thread.op.pins for cmt in comments])

        tiles = []
        for cmt, pins in zip(details, pins):
            tile = cls(cmt)
            tile.pins = pins
            tiles.append(tile)
        return tiles

    @classmethod
    def from_queryset_with_viewer_stickers(cls, viewer, comments):
        """
        Returns a list of tile details, preloaded with `viewer_sticker` properties which contain a sticker type ID.
        """
        #TODO use a multicall
        tiles = [cls(cmt.details()) for cmt in comments]

        tiles = []
        for cmt in comments:
            tile = cls(cmt.details())
            tile.viewer_sticker = cmt.get_sticker_from_user(viewer)
            tiles.append(tile)
        return tiles

    @property
    def comment(self):
        """ Contains this tile's comment details. """
        return self._comment_details

    def is_dismissable(self, viewer):
        return is_dismissable(self.comment, viewer)

    def is_pinned(self, viewer):
        """
        `viewer` is the user who will see these comments. It *must* come from a request object,
        in order for `is_authenticated` to make sense. If they're logged out, they won't see pins.
        """
        if not viewer.is_authenticated():
            return False

        if self.pins is None:
            self.pins = Comment.pins_by_id(self._comment_details.thread_op_comment_id)()

        return viewer.id in self.pins


class StickyTileDetails(TileDetails):
    def __init__(self, comment_details, text):
        super(StickyTileDetails, self).__init__(comment_details)
        self.text = text

    @classmethod
    def from_sticky_thread(cls, viewer, comment_id, text):
        comment = Comment.objects.get(id=comment_id)
        tile = cls(comment.details(), text)
        tile.viewer_sticker = comment.get_sticker_from_user(viewer)
        return tile

    def is_dismissable(self, viewer):
        return False


class LastReplyTileDetails(TileDetails):
    def __init__(self, op_comment_details, request=None):
        """
        Takes the details of the OP comment.
        """
        #TODO remove the `request` kwarg once we've resolved the small_square bug which we record below.

        self._last_reply = None
        # self._comment_details will contain the OP, since we're passing it to TileDetails.__init__.
        super(LastReplyTileDetails, self).__init__(op_comment_details)

    @classmethod
    def from_comment_id(cls, op_comment_id):
        return super(LastReplyTileDetails, cls).from_comment_id(op_comment_id)

    @property
    def comment(self):
        """
        The last reply in this tile's thread, which could be the same as the OP if there are no replies. This is the
        main comment that this tile represents.
        """
        if self._last_reply:
            return self._last_reply

        if self._comment_details.has_replies():
            #TODO verify that we should show this 'last reply', that it's not curated or anything
            # (we did this before by checking membership in the 'last_replies' list given by get_front_data)
            self._last_reply = self._comment_details.get_last_reply()
        else:
            self._last_reply = self._comment_details

        return self._last_reply

    @property
    def op(self):
        """ The OP comment's details. """
        return self._comment_details

    def check_for_small_image(self, request):
        """ Checks for missing "small_image" thumbnail. Logs a metric if it is missing. """
        if request and not self.comment.has_small_image():
            Metrics.image_missing.record(request, content_details=self.op.reply_content)

    @property
    def is_reply(self):
        """ If this tile represents a reply as the primary comment, and not an OP, then returns True. """
        return self.comment.id != self.op.id


class Navigation(object):
    valid_sorts = ['active', 'hot', 'top', 'best', 'pinned', 'new', 'archive']
    valid_userpage_types = ['new', 'new_anonymous', 'top', 'top_anonymous', 'stickered']

    def __init__(self, sort=None, year=None, month=None, day=None, offset=0, category=None,
        user=None, userpage_type=None, hot_sort_type=None, mobile=False, public_api=False,
        replies_only=False, public_only=False, count=None, tag=None):

        self.sort = sort
        self.year = year
        self.month = month
        self.day = day
        self.offset = offset
        self.category = category
        self.tag = tag
        self.user = user
        self.userpage_type = userpage_type
        self.hot_sort_type = hot_sort_type
        self.mobile = mobile
        self.public_api = public_api
        self.replies_only = replies_only
        self.public_only = public_only
        self.count = count

        if self.sort == "best":
            self.year = 2011
            self.month = None
            self.day = None

        self.validate()

    def validate(self):
        if self.category is None and self.tag is None:
            self.category = Category.ALL

        if self.sort and self.sort not in Navigation.valid_sorts:
            raise ValueError("Sort %r is not a valid sort (%r)." % (self.sort, Navigation.valid_sorts))

        if self.userpage_type and self.userpage_type not in Navigation.valid_userpage_types:
            raise ValueError("Userpage type %r is not a valid userpage type (%r)." % (self.userpage_type, Navigation.valid_userpage_types))

        if not self.sort and not self.userpage_type:
            raise ValueError("Must specify one of either sort or userpage_type")

        if bool(self.userpage_type) != bool(self.user):
            raise ValueError("Must specify both user and userpage_type, or neither.")

        if self.hot_sort_type and not frontpage_algorithms.get(self.hot_sort_type):
            raise ValueError("hot_sort_type must be a valid frontpage algorithm name.")

        if not self.day:
            if not self.month:
                self._top_fun = 'year'
                self.month = self.day = 1
            else:
                self._top_fun = 'month'
                self.day = 1
        else:
            self._top_fun = 'day'

        if self.sort in ('top', 'best'):
            # Raises ValueError if date is invalid
            self.get_date()

    @classmethod
    def load_json(cls, data, **kwargs):
        int_or_none = lambda key: int(str(data[key]), 10) if data.get(key) else None
        str_or_none = lambda key: str(data[key]) if data.get(key) else None

        args = {
            'year': int_or_none('year'),
            'month': int_or_none('month'),
            'day': int_or_none('day'),
            'sort': str_or_none('sort'),
            'hot_sort_type': str_or_none('hot_sort_type'),
            'userpage_type': str_or_none('userpage_type'),
            'category': Category.get(data.get('category')),
            'tag': str_or_none('tag'),
            'offset': int_or_none('offset') or 0,
            'user': User.objects.get_or_none(username=data['user']) if data.get('user') else None,
            'replies_only': bool(data.get('replies_only')),
            'public_only': bool(data.get('public_only')),
            'mobile': bool(data.get('mobile')),
            'public_api': bool(data.get('public_api')),
            'count': int_or_none('count'),
        }
        args.update(kwargs)

        return cls(**args)

    @classmethod
    def load_json_or_404(cls, *args, **kwargs):
        try:
            return cls.load_json(*args, **kwargs)
        except ValueError:
            raise Http404

    def dump_json(self):
        remove_none_values = lambda d: dict((key, value) for (key,value) in d.items() if value is not None)

        return remove_none_values({
            'year': self.year,
            'month': self.month,
            'day': self.day,
            'sort': self.sort,
            'hot_sort_type': self.hot_sort_type,
            'category': self.category.name if self.category else None,
            'tag': self.tag,
            'user': self.user.username if self.user else None,
            'userpage_type': self.userpage_type,
            'pagination_size': self.pagination_size,
            'offset': self.offset,
            'mobile': self.mobile,
            'public_api': self.public_api,
            'replies_only': self.replies_only,
            'public_only': self.public_only,
            'count': self.count,
        })

    def get_date(self):
        return datetime.date(self.year, self.month, self.day)

    def get_top_data(self, group):
        try:
            return getattr(group.top, self._top_fun)(self.get_date())
        except ValueError:
            raise Http404

    @property
    def slice(self):
        return util.get_slice[self.offset:self.offset + self.pagination_size]

    @property
    def pagination_size(self):
        if self.count:
            return self.count
        elif self.mobile:
            return 7
        elif self.public_api:
            return knobs.PUBLIC_API_PAGINATION_SIZE
        else:
            return 500

    @property
    def next_offset(self):
        return self.offset + self.pagination_size


def get_user_posted(user, manager='browse_objects', anonymous=False, namefriend=True):
    manager = getattr(Comment, manager)

    if anonymous and namefriend:
        return manager.filter(author=user).order_by('-id')
    else:
        return manager.filter(author=user, anonymous=anonymous).order_by('-id')

def get_user_top_posted(user, manager, aslice, anonymous=False, namefriend=True):
    manager = getattr(Comment, manager)
    redis_top = (user.redis.top_anonymous_posts if anonymous else user.redis.top_posts)

    if anonymous and namefriend:
        keys = [user.redis.top_anonymous_posts.key, user.redis.top_posts.key]
        redis_top = list(redis.zunion(keys, withscores=True, transaction=False))
        redis_top = sorted(redis_top, key=lambda x: -x[1])
        redis_top = [int(x) for x,y in redis_top]
        return manager.in_bulk_list(redis_top[aslice])

    return manager.filter(anonymous=anonymous).in_bulk_list(redis_top[aslice])

def get_user_stickered(user):
    return Comment.objects.filter(stickers__user=user, stickers__type_id__lt=500).order_by('-stickers__timestamp')

def get_user_data(viewer, nav):
    viewer_is_staff = viewer.is_authenticated() and viewer.is_staff
    user_can_see_anonymous = (nav.user.id == viewer.id or viewer_is_staff)
    content_manager = Content.get_appropriate_manager(viewer)

    posts = []
    # Not a banned account, or you're allowed to see banned accounts.
    if nav.user.is_active or viewer_is_staff:
        if nav.userpage_type == 'top':
            if not user_can_see_anonymous:
                posts = get_user_top_posted(nav.user, content_manager, nav.slice)
            else:
                posts = get_user_top_posted(nav.user, content_manager, nav.slice, anonymous=True, namefriend=True)
        elif user_can_see_anonymous and nav.userpage_type == 'top_anonymous':
            posts = get_user_top_posted(nav.user, content_manager, nav.slice, anonymous=True, namefriend=False)
        elif nav.userpage_type == 'new':
            if user_can_see_anonymous:
                posts = get_user_posted(nav.user,
                                        manager=content_manager, anonymous=True, namefriend=True)[nav.slice]
            else:
                posts = get_user_posted(nav.user, manager=content_manager)[nav.slice]
        elif user_can_see_anonymous and nav.userpage_type == 'new_anonymous':
            posts = get_user_posted(nav.user, manager=content_manager, anonymous=True, namefriend=False)[nav.slice]
        elif nav.userpage_type == 'stickered':
            posts = get_user_stickered(nav.user)[nav.slice]
        else:
            raise Http404

        return TileDetails.from_queryset_with_viewer_stickers(viewer, posts)

    return []

def _get_hot_slice_by_threads(rlbb, nav_slice):
    ops_and_scores = rlbb.with_scores[nav_slice] if rlbb else []

    ops = [Comment(id=id) for (id, score) in ops_and_scores]

    max_from_thread = 3

    # Got the OPs, now I need to bulk fetch the top replies.
    pipeline = redis.pipeline()
    for comment in ops:
        pipeline.get(comment.redis_score.key)

    for comment in ops:
        pipeline.zrevrange(comment.popular_replies.key, 0, max_from_thread - 1, withscores=True)

    results = pipeline.execute()

    op_scores, pop_reply_lists = results[:len(ops)], results[len(ops):]

    ids = []

    if ops_and_scores:
        # Lowest score sets the threshold, but replies get a "boost" factor
        cutoff = ops_and_scores[-1][1] / Config.get('reply_boost', 1)
        for op, op_score, pop_replies in zip(ops, op_scores, pop_reply_lists):
            items = [(int(id), float(score or 0)) for (id,score) in [(op.id, op_score)] + pop_replies]
            items.sort(key=lambda (id, score): -score)
            ids += [id for (id, score) in items if score >= cutoff][:max_from_thread]

    return ids

def _get_buffer(group, nav):
    buff_lookup = {
        'active': lambda group: group.bumped_buffer,
        'hot': lambda group: group.popular,
        'top': lambda group: nav.get_top_data(group),
        'best': lambda group: nav.get_top_data(group),
    }

    return buff_lookup[nav.sort](group)

def _get_aggregate_rlbb(groups, nav):
    groups = list(groups)

    if not groups:
        return []
    else:
        rlbb = RedisLastBumpedBuffer(gen_temp_key(), size=None)
        buffers = [_get_buffer(group, nav).key for group in groups]
        redis.zunionstore(rlbb.key, buffers, aggregate='MAX')
        return rlbb

def _get_from_redis(viewer, nav):
    manager = Comment.browse_objects

    if nav.sort == 'pinned':
        if not viewer.is_authenticated():
            raise PermissionDenied()
        rlbb = viewer.redis.pinned_bump_buffer
    else:
        # The 'curated' visibility is used to curate the sections of everything.
        if nav.category == Category.ALL:
            manager = Comment.curated_browse_objects

        if nav.category == Category.MY:
            if not viewer.is_authenticated():
                raise PermissionDenied()
            following = Category.objects.filter(followers__user=viewer)
            rlbb = _get_aggregate_rlbb(following, nav)
        elif not viewer.is_authenticated() and nav.category == Category.ALL:
            # Implicitly whitelisted groups
            rlbb = _get_aggregate_rlbb(Category.objects.in_bulk_list(Category.get_whitelisted()), nav)
        else:
            rlbb = _get_buffer(nav.category, nav)

    if nav.sort != 'hot':
        ids = rlbb[nav.slice]
    elif nav.hot_sort_type:
        ids = frontpage_algorithms.get_slice(nav.hot_sort_type, nav.slice)
    else:
        ids = _get_hot_slice_by_threads(rlbb, nav.slice)

    qs = manager
    if nav.sort not in ['active']:
        qs = qs.exclude(reply_content=None)

    # Remove user-hidden comments.
    ids = remove_hidden_comment_ids(viewer, ids)

    return qs.in_bulk_list(ids)

def _get_tagged_from_redis(viewer, nav):
    comments = Comment.browse_objects

    if nav.sort == 'hot':
        ids = _get_hot_slice_by_threads(Tag(nav.tag).popular, nav.slice)
        comments = comments.exclude(reply_content__id=None)

    elif nav.sort == 'top':
        # this is so gross
        ids = nav.get_top_data(Tag(nav.tag))[nav.slice]
    else:
        ids = Tag(nav.tag).images_only[nav.slice]

    # Remove user-hidden comments.
    ids = remove_hidden_comment_ids(viewer, ids)

    return comments.in_bulk_list(ids)

def _get_from_database(viewer, nav):
    if nav.category == Category.ALL:
        # Note: Logged out users can see all posts in /new, not just whitelisted groups.
        categorized = Comment.curated_browse_objects
    elif nav.category == Category.MY:
        if not viewer.is_authenticated():
            raise PermissionDenied()
        categorized = Comment.browse_objects.filter(category__in=list(viewer.following.all().values_list('category__id', flat=True)))
    else:
        categorized = Comment.public.filter(category=nav.category)

    if nav.replies_only:
        categorized = categorized.exclude(parent_comment=None)
        # if we're only considering public replies, we should ensure the parent is public as well
        categorized = categorized.filter(parent_comment__visibility__in=[Visibility.PUBLIC])

    if nav.public_only:
        categorized = categorized.filter(visibility=Visibility.PUBLIC)

    # Remove user-hidden comments.
    if viewer.is_authenticated():
        categorized = categorized.exclude(id__in=viewer.redis.hidden_comments.smembers())

    # Prune text-only replies.
    categorized = categorized.exclude(reply_content__id=None)

    return categorized.order_by('-id')[nav.slice]

def get_archive_ops(viewer, nav):
    categorized = Comment.public.filter(category=nav.category)
    categorized = categorized.filter(parent_comment=None)
    return categorized.order_by('-id')

def get_front_comments(viewer, nav):
    if nav.tag is not None:
        return _get_tagged_from_redis(viewer, nav)
    elif nav.sort == 'new':
        return _get_from_database(viewer, nav)
    else:
        return _get_from_redis(viewer, nav)

def get_browse_tiles(viewer, nav):
    from apps.monster.models import MONSTER_GROUP, MonsterTileDetails

    #TODO an optimization - TileDetails gets the last reply itself even though get_front_comments already did.
    comments = get_front_comments(viewer, nav)

    if nav.category and nav.category.name == MONSTER_GROUP:
        materialize = lambda comments: MonsterTileDetails.from_queryset_with_viewer_stickers(viewer, comments)
    else:
        materialize = lambda comments: TileDetails.from_queryset_with_viewer_stickers(viewer, comments)

    tiles = materialize(comments)

    # Remove hidden threads.
    if viewer.is_authenticated():
        tiles = viewer.redis.hidden_threads.filter_comments(tiles, comment_key=lambda tile: tile.comment)

    return tiles


class FrontpageAlgorithm(object):
    def __init__(self, fun):
        self.fun = fun
        self.name = fun.__name__
        self.frontpage = RedisList('frontpage:%s' % self.name)


def _log_key(comment, s=1, r=1):
    details = comment.details()

    sticker_score = sum(stickers.details_for(k).value * v for k, v in details.sticker_counts.items())
    # sticker_core is roughly -5 to 100

    reply_count = details.reply_count
    # reply_count is roughly 0 to 100 (in 24 hours)

    score = sticker_score *s + reply_count * r

    """
    boost is defined as: post with score 1000 should be above a stickerless post two days later

    >>> (2 * 24 * 60 * 60) / math.log(1000, 2)
    17339.327750245317
    """

    C = 17339.327750245317 # not actually the speed of light

    if score:
        sign = score / abs(score)
        boost = sign * math.log(abs(score), 2) * C
    else:
        boost = 0

    rank = details.timestamp + boost

    return -rank

@FrontpageAlgorithm
def order_by_time_plus_log_stickers_and_replies():
    comments = list(
        Comment.public
            .filter(timestamp__gte=time.time() - 24*60*60)
            .filter(category__in=Category.get_whitelisted())
            .exclude(reply_content=None)
    )
    return sorted(comments, key=lambda comment: _log_key(comment, s=1, r=1))

@FrontpageAlgorithm
def order_by_image_replies():
    # Doing this in a weird way because I was unable to make a SQL INNER JOIN that performed decently
    ops = list(Comment.public.filter(timestamp__gte=time.time() - 24*60*60).filter(parent_comment=None))
    for op in ops:
        op.image_reply_count = op.replies.exclude(reply_content=None).count()

    return sorted(ops, key=lambda comment: -comment.image_reply_count)

class AlgorithmSet(object):
    def __init__(self, algorithms):
        self.algorithms = algorithms

    def get(self, name):
        for algo in self.algorithms:
            if algo.name == name:
                return algo

    def get_slice(self, hot_sort_type, slice):
        return [int(comment_id) for comment_id in self.get(hot_sort_type).frontpage[slice]]

    def update_scores(self):

        for algo in self.algorithms:
            ranking = algo.fun()
            temp_list = RedisList(gen_temp_key())

            if ranking:
                for comment in ranking:
                    temp_list.rpush(comment.id)

                # Atomically replace the frontpage with the new version.
                temp_list.rename(algo.frontpage.key)
            else:
                # If the ranking is empty, we just delete the frontpage key (the rename will fail)
                algo.frontpage.delete()

frontpage_algorithms = AlgorithmSet([
    order_by_time_plus_log_stickers_and_replies,
    order_by_image_replies,
])

