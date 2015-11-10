import datetime
from collections import defaultdict

from canvas.redis_models import redis, RedisSet, RedisSortedSet, RedisKey, RedisLastBumpedBuffer, DateKey, RealtimeChannel
from canvas import knobs
from services import Services

all_tags = RedisSet("tags:all")

class Tag(object):
    top = property(lambda self: DateKey(lambda key: RedisLastBumpedBuffer(key, 30*30), self.base_key, ':top'))

    updates_channel = property(lambda self: RealtimeChannel('tu:%s' %  self.name, 5, ttl=24*60*60))

    def __repr__(self):
        return self.name

    def __init__(self, name):
        self.name = name.lower().strip().replace('#', '')
        self.base_key = 'tag:{}:posts'.format(self.name)
        self.new = RedisSortedSet(self.base_key)
        self.images_only = RedisLastBumpedBuffer(self.base_key + ':images', 1000)
        self.popular = RedisLastBumpedBuffer(self.base_key + ':popular', 1000)
        self.post_count = RedisKey(self.base_key + ':count')

    def to_client(self):
        return self.name

    def tag_comment(self, comment, timestamp=None):
        if timestamp is None:
            timestamp = Services.time.time()

        self.new.zadd(int(comment.id), timestamp)
        all_tags.sadd(self.name)

        if comment.reply_content is not None:
            self.images_only.bump(int(comment.id), score=timestamp)
            count = self.post_count.incr()
            self.updates_channel.publish({'post': comment.id, 'tag': self.name, 'count': count})

    def untag_comment(self, comment):
        self.new.zrem(comment.id)
        self.images_only.remove(comment.id)
        self.popular.remove(comment.id)

    def get_absolute_url(self):
        return '/x/' + self.name.replace('#','')

    def user_is_following(self, user):
        if not user.is_authenticated():
            return False

        return self.name in user.redis.followed_tags

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


def tag_dict(name, tracked, current, unseen):
    return {
        'name': name,
        'tracked': tracked,
        'current': current,
        'unseen': unseen,
    }

def get_tracked_tags(user, followed_tags, nav_tag):
    is_current = lambda x: nav_tag is not None and x == nav_tag

    if not user.is_authenticated():
        tags = [tag_dict(tag, False, is_current(tag), False)
                    for tag in knobs.OFFLINE_SUGGESTED_TOPICS]

        if nav_tag is not None and nav_tag not in knobs.OFFLINE_SUGGESTED_TOPICS:
            return [tag_dict(nav_tag, False, is_current(nav_tag), False)] + tags
        else:
            return tags

    else:

        followed_tags_info = user.redis.followed_tags_info.hgetall()
        followed = []

        for tag in followed_tags:
            current = int(Tag(tag).post_count.get() or 0)
            seen = int(followed_tags_info.get(tag, 0))
            unseen = (current - seen) if (seen > 0) else False
            if unseen and unseen >= knobs.FOLLOWED_TAGS_REALTIME_THRESHOLD:
                unseen = "10+"
            if tag == nav_tag:
                unseen = False
                user.redis.followed_tags_info.hset(tag, current)
            followed.append(tag_dict(tag, True, is_current(tag), unseen))

        if nav_tag is not None and nav_tag not in followed_tags:
            return [tag_dict(nav_tag, False, is_current(nav_tag), False)] + followed
        else:
            return followed

