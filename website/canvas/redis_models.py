import datetime
import random
import sys
import time
import traceback
import types
import uuid

from redis import ConnectionPool, Redis
from twisted.internet.defer import inlineCallbacks

from canvas import bgwork, util, hacks
from services import Services
from django.conf import settings

def gen_temp_key():
    key = "temp:%s" % uuid.uuid1()

    def delete_temp_key():
        redis.delete(key)

    bgwork.defer(delete_temp_key)
    return key


class CanvasRedis(Redis):
    """ Convenience helpers for Redis object, and Redis logging. """
    commands = []

    def __init__(self, host, port, db, *args, **kwargs):
        Redis.__init__(self, host, port, db, *args, **kwargs)
        self._host = host
        self._port = port
        self._db = db

    def lget(self, key):
        return self.lrange(key, 0, -1)

    def zget(self, key):
        return dict((k,v) for (v,k) in self.zrange(key, 0, -1, withscores=True))

    def zrevget(self, key, **kwargs):
        return self.zrevrange(key, 0, -1, **kwargs)

    def smembers(self, key):
        return set(Redis.smembers(self, key))

    def sunion(self, keys):
        return set(Redis.sunion(self, keys))

    def zunion(self, keys, withscores=False, transaction=True, max_score=None):
        """ `max_score` is exclusive. """
        if not keys:
            return set()

        temp_key = 'temp:zunion:%s' % uuid.uuid4()
        pipe = self.pipeline(transaction=transaction)
        pipe.zunionstore(temp_key, keys)
        if max_score is None:
            pipe.zrange(temp_key, 0, -1, withscores=withscores)
        else:
            pipe.zrangebyscore(temp_key, '-inf', '(' + str(max_score), withscores=withscores, score_cast_func=str)
        pipe.delete(temp_key)
        return set(pipe.execute()[-2])

    def pipeline(self, *args, **options):
        pipeline = Redis.pipeline(self, *args, **options)

        pipeline_execute = pipeline.execute

        def execute():
            commands = pipeline.command_stack[:]
            start = time.time()

            results = pipeline_execute()

            end = time.time()
            tdelta = (end - start) * 1000
            if False: # Disabled while migrating to newer redis, should be: settings.DEBUG:
                command = "PIPELINE:\n" + "\n".join(" ".join([str(s) for s in args]) for args, kwargs in commands)
                result_size = sum(len(result) if isinstance(result, str) else 0 for result in results)
            else:
                command = result_size = None
            self.record_command(tdelta, command, result_size)

            return results

        pipeline.execute = execute

        return pipeline

    def record_command(self, tdelta, command, result_size):
        if settings.DEBUG:

            self.commands.append((self._host, self._port, self._db, tdelta, traceback.extract_stack(), command, result_size))

        request = hacks.find_request()

        if request:
            if not hasattr(request, "_redis_commands"):
                request._redis_commands = []

            request._redis_commands.append(tdelta)

    def execute_command(self, *args, **options):
        start = time.time()

        result = Redis.execute_command(self, *args, **options)

        end = time.time()
        tdelta = (end-start) * 1000
        command =  " ".join(unicode(s) for s in args)
        self.record_command(tdelta, command, int(isinstance(result, str) and len(result)))

        return result


# Note that we use two differnet Redis databases. One for canonical storage and the other
# for caching expensive db calls.
redis = CanvasRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB_MAIN)


class RedisKeyBase(object):
    def __init__(self, key):
        self.key = str(key)

    def __str__(self):
        return self.key

    all_methods = ['exists', 'delete', 'type', 'ttl', 'expire', 'expireat', 'rename', 'move']
    # Redis python is missing 'persist'


def key_call(attr):
    def caller(self, *args, **kwargs):
        return getattr(redis, attr)(self.key, *args, **kwargs)
    return caller

def redis_methods(cls):
    """
    Magic to make C{RedisKey(foo).bar(1,2)} equivalent to C{redis.bar(foo, 1,2)} for all C{bar}.
    """
    for method in cls.methods + cls.all_methods:
        setattr(cls, method, key_call(method))
    return cls


class RedisIndexableSortedSetWithScores(object):
    def __init__(self, zset):
        self.zset = zset

    def __getitem__(self, item):
        return self.zset.getslice(item, mapfn=lambda (n,s): (int(n), float(s)),withscores=True)


class RedisIndexableSortedSet(object):
    def __init__(self, getter=lambda x: x):
        self._getter = getter

    def __iter__(self):
        return iter(self[:])

    def __getitem__(self, item):
        if not isinstance(item, slice):
            raise TypeError("RedisIndexableSortedSet is not indexable without using a slice.")
        return self.getslice(item)

    @property
    def with_scores(self):
        return RedisIndexableSortedSetWithScores(self)

    def getslice(self, item, mapfn=None, **kwargs):
        """ `mapfn` defaults to whatever was passed for `getter` when this was instantiated. """
        if mapfn is None:
            mapfn = self._getter

        if isinstance(item, slice):
            assert item.step is None
            if item.stop is not None:
                start = item.start if item.start is not None else 0
                assert start >= 0 and item.stop >= 0, "Negative indexing not supported"
                return map(mapfn, redis.zrevrange(self.key, start, item.stop - 1, **kwargs))
            else:
                return map(mapfn, redis.zrevget(self.key, **kwargs))
        else:
            raise ValueError("The given item must be a slice object.")


@redis_methods
class RedisKey(RedisKeyBase):
    methods = ['set', 'get', 'getset', 'setnx', 'setex', 'incr', 'decr', 'append', 'substr']


@redis_methods
class RedisList(RedisKeyBase):
    methods = ['rpush', 'lpush', 'llen', 'lrange', 'ltrim', 'lindex', 'lset', 'lrem', 'lpop', 'rpop', 'blpop',
               'brpop', 'rpoplpush', 'sort']

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self.lrange(item.start, item.stop-1)


@redis_methods
class RedisSet(RedisKeyBase):
    methods = ['sadd', 'srem', 'spop', 'smove', 'scard', 'sismember', 'sinter', 'sinterstore', 'sunion',
               'sunionstore', 'sdiff', 'sdiffstore', 'smembers', 'srandmember', 'sort']

    def __contains__(self, item):
        """ This adds "in" operator support, so that we can do: item in set """
        return self.sismember(item)


@redis_methods
class RedisSortedSet(RedisKeyBase, RedisIndexableSortedSet):
    """ Holds ints. """
    def __init__(self, *args, **kwargs):
        self._getter = kwargs.pop('getter', int)
        super(RedisSortedSet, self).__init__(*args, **kwargs)

    methods = ['zget', 'zadd', 'zrem', 'zincrby', 'zrank', 'zrevrank', 'zrange', 'zrevrange', 'zrangebyscore',
               'zcard', 'zscore', 'zremrangebyrank', 'zremrangebyscore', 'zunionstore', 'zinterstore']
    # 'zcount' is on redis-py's trunk


@redis_methods
class RedisHash(RedisKeyBase):
    methods = ['hset', 'hsetnx', 'hget', 'hmget', 'hmset', 'hincrby', 'hexists', 'hexists', 'hlen', 'hkeys',
               'hvals', 'hgetall', 'hdel']

    def hincrby_ifsufficient(self, key, incr):
        remaining = self.hincrby(key, incr)
        success = True
        if remaining < 0:
            remaining = self.hincrby(key, -incr)
            success = False
        return {'success': success, 'remaining': remaining}

    def hset_bool(self, key, value):
        """ To read back: int(request.user.kv.get(key, 0), or use read_bool """
        return self.hset(key, int(bool(value)))

    @classmethod
    def read_bool(cls, dictionary, key):
        """ A utility to read a boolean from an hgetall dictionary, because we store bools as "0" strings. """
        return bool(int(dictionary.get(key, False)))


@redis_methods
class RedisPubSub(RedisKeyBase):
    methods = ['publish']

class RedisCircularIntBuffer(object):
    def __init__(self, key, size):
        self.key = RedisList(key)
        self.size = size

    def push(self, id):
        self.key.lpush(int(id))
        self.key.ltrim(0, self.size - 1)

    def top(self, count):
        return [int(id) for id in self.key.lrange(0, count - 1)]

    def get(self):
        return [int(id) for id in self.key.lget()]


class RedisLastBumpedBuffer(RedisIndexableSortedSet):
    """ Keep a buffer of the last C{size} push calls with unique C(id)s. Holds ints by default. """
    def __init__(self, key, size, getter=int):
        super(RedisLastBumpedBuffer, self).__init__(getter=getter)
        self.key = key
        self.size = size

    def bump(self, member, score=None, truncate=True, coerce=True):
        if score is None:
            score = time.time()
        if coerce:
            member = int(member)
        redis.zadd(self.key, member, score)
        if truncate:
            # Allows you to queue a bunch of updates and then truncate once, for perf reasons.
            self.truncate()

    def truncate(self, factor=1):
        """
        Remove up to self.size items that are ranked lower than the top self.size ranked items.
        (Should usually be 1 +/- a few race conditions)
        """
        size = self.size * factor
        redis.zremrangebyrank(self.key, -size - size, -size - 1)

    def remove(self, id, coerce=True):
        if coerce:
            id = int(id)
        redis.zrem(self.key, id)

    def delete(self):
        redis.delete(self.key)


def coerce_date(d):
    if isinstance(d, (float, int)):
        return datetime.date.fromtimestamp(d)
    else:
        return d


class DateKey(object):
    def __init__(self, keyclass, prefix, suffix = ""):
        self.keyclass = keyclass
        self.prefix = prefix
        self.suffix = suffix

    def day(self, day):
        return self.keyclass(self.prefix + 'day:' + coerce_date(day).strftime("%Y.%m.%d") + self.suffix)

    def month(self, day):
        return self.keyclass(self.prefix + 'month:' + coerce_date(day).strftime('%Y.%m') + self.suffix)

    def year(self, day):
        return self.keyclass(self.prefix + 'year:' + coerce_date(day).strftime('%Y') + self.suffix)

    @property
    def today(self):
        return self.day(datetime.date.today())

class KeyedSet(object):
    def __init__(self, prefix):
        self.prefix = prefix
        self.hash = RedisHash(prefix + "notifications")
        self.hash_id = RedisKey(prefix + 'notification_id')

    def add(self, blob):
        key = self.hash_id.incr()
        self.hash.hset(key, blob)
        return key

    def remove(self, key):
        return self.hash.hdel(key)

    def get(self):
        return dict((int(key), value) for (key, value) in self.hash.hgetall().items())

class UserNotificationQueue(object):
    def __init__(self, user_id, channel):
        self.queue = KeyedSet('user:%s:' % user_id)
        self.channel = channel

    def send(self, data):
        key = self.queue.add(util.dumps(data))
        data['nkey'] = key
        data['msg_type'] = "notification"
        self.channel.publish(data)
        return key

    def acknowledge(self, key):
        success = self.queue.remove(key)
        if success:
            self.channel.publish({'msg_type': 'notification_ack', 'nkey': key})
        return success

    def get(self):
        items = sorted(self.queue.get().items(), key=lambda (k,v): k)
        return [dict(util.loads(blob), nkey=key) for (key,blob) in items]

class IP(object):
    def __init__(self, ip):
        assert type(ip) in (int, long) # use util.ip_to_int
        self.user_history = RedisLastBumpedBuffer('ip:%s:history' % ip, 1000)

class RateLimit(object):
    def __init__(self, key, freq, timespan=60):
        self.key = key
        self.freq = freq
        self.timespan = timespan

    def allowed(self):
        key = self.key + ":" + str(int(Services.time.time()) // self.timespan)
        amount = redis.incr(key)
        # Should set expire here, but expire breaks incr on old redis versions, which we're running locally.
        return amount <= self.freq

class ThresholdMetric(object):
    divisions = 10

    def __init__(self, key, threshold=1, minutes=1):
        self.key_base = key
        self.threshold = threshold
        self.timespan = minutes * 60

    @property
    def key(self):
        return self.key_base + ":" + str(int(Services.time.time()) // (self.timespan / self.divisions))

    def increment(self):
        value = redis.incr(self.key)
        redis.expire(self.key, self.timespan * 4)
        return value

    def _timespan_keys(self, doubled=False):
        divisions = (self.divisions * 2) if doubled else self.divisions
        time_key = int((Services.time.time()) // (self.timespan / self.divisions))
        keytimes = set([time_key - x for x in range(divisions)])
        return [self.key_base + ":" + str(x) for x in keytimes]

    def amount(self, doubled=False):
        vals = redis.mget(self._timespan_keys(doubled))
        return sum([0 if x is None else int(x) for x in vals])

    def is_okay(self, doubled=False):
        if self.threshold > 0:
            return self.amount(doubled) >= self.threshold
        else:
            return self.amount(doubled) < abs(self.threshold)


class RealtimeChannel(object):
    """
    channel:id:msg_id, integer
    channel:id:msg_backlog, zset
    channel:id:pubsub, redis pubsub
    """
    def __init__(self, channel, backlog_length=None, ttl=None):
        self.channel = unicode(channel)
        self.basekey = 'channel:%s:' % channel
        self.backlog_length = backlog_length
        self.ttl = ttl

    def __hash__(self):
        return hash(self.channel)

    def __eq__(self, other):
        return hasattr(other, 'channel') and self.channel == other.channel

    def publish(self, message):
        if not self.backlog_length:
            raise Exception("Cannot publish to a RealtimeChannel without a backlog_length set.")

        id = self.msg_id.incr()
        self.msg_backlog.zadd(util.client_dumps(message), id)
        self.pubsub.publish(util.client_dumps({'id': id, 'payload': message}))
        self.msg_backlog.zremrangebyscore('-inf', id - self.backlog_length)
        if self.ttl:
            self.msg_id.expire(self.ttl)
            self.msg_backlog.expire(self.ttl)

    def get(self):
        return dict((int(id), util.loads(blob)) for (id, blob) in self.msg_backlog.zget().items())

    def sync(self):
        return {'channel': self.channel, 'last_message_id': self.msg_id.get(), 'timestamp': time.time()}

    pubsub = property(lambda self: RedisPubSub(self.basekey + 'pubsub'))
    msg_backlog = property(lambda self: RedisSortedSet(self.basekey + 'msg_backlog'))
    msg_id = property(lambda self: RedisKey(self.basekey + 'msg_id'))


class HashSlot(object):
    def __init__(self, hash, key):
        self.hash = hash
        self.key = key

    def get(self, *args, **kw):
        return self.hash.get(self.key, *args, **kw)

    def set(self, value):
        return self.hash.set(self.key, value)

    def delete(self):
        return self.hash.delete(self.key)

    def setnx(self, value):
        return self.hash.setnx(self.key, value)

    def increment(self, delta=1):
        return self.hash.increment(self.key, delta)

    def increment_ifsufficient(self, delta=1):
        return self.hash.increment_ifsufficient(self.key, delta)


# (to_str, from_str, default)
hint = lambda default=0: (lambda n: str(int(n)), int, default)
hfloat = lambda default=0: (lambda n: str(float(n)), float, default)
hstr = lambda default="": (str, str, default)
hbool = lambda default=False: (lambda n: str(int(n)), lambda n: bool(int(n)), default)

class RedisCachedHash(object):
    """
    Uses an underlying Redis Hash, but caches the value in a private member variable.

        `DEFINITION`:
            A dictionary of the keys in this hash and their serialization and default handlers (hint, hbool, etc.)
            Redefine it in your subclass.

            Example:
                DEFINITION = {"sticker_level": hint()}
    """
    DEFINITION = {}

    def __init__(self, key, definition=None):
        """
        If you pass a `definition` here, it will override the class-level DEFINITION for this instance. Otherwise
        it defaults to `self.__class__.DEFINITION`.
        """
        self.__hash = RedisHash(key)
        if definition is None:
            self.__definition = self.__class__.DEFINITION
        else:
            self.__definition = definition
        self.__values = None

    def ensure(self, nocache=False):
        if self.__values == None or nocache:
            self.update()

    def update(self):
        self.__values = self.__hash.hgetall()

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __getattr__(self, name):
        # Lazy create HashSlots
        if not name in self.__definition:
            raise AttributeError(name)
        hslot = self.__dict__[name] = HashSlot(self, name)
        return hslot

    def get(self, key, nocache=False):
        self.ensure(nocache)
        (to_str, from_str, default) = self.__definition[key]
        return from_str(self.__values.get(key, default))

    def hgetall(self):
        return self.__hash.hgetall()

    def set(self, key, value, definition=hbool()):
        """
        @param definition: A (to_str, from_str, default) tuple. See hint(), hfloat() ... etc.
        """
        self.ensure()
        try:
            (to_str, from_str, default) = self.__definition[key]
        except KeyError:
            self.__definition[key] = definition
            (to_str, from_str, default) = self.__definition[key]
        str_value = to_str(value)
        self.__hash.hset(key, str_value)
        self.__values[key] = str_value

    def delete(self, key):
        # While not strictly necessary, ensure() means we don't have to worry about __values being None and such.
        self.ensure()
        self.__hash.hdel(key)
        del self.__values[key]

    def setnx(self, key, value):
        self.ensure()
        (to_str, from_str, default) = self.__definition[key]
        str_value = to_str(value)
        changed = self.__hash.hsetnx(key, str_value)
        if changed:
            self.__values[key] = str_value
        return changed

    def increment(self, key, delta=1):
        self.ensure()
        (to_str, from_str, default) = self.__definition[key]
        result = self.__values[key] = self.__hash.hincrby(key, to_str(delta))
        return from_str(result)

    def increment_ifsufficient(self, key, delta=1):
        self.ensure()
        (to_str, from_str, default) = self.__definition[key]
        result = self.__hash.hincrby_ifsufficient(key, delta)
        self.__values[key] = result['remaining']
        result['remaining'] = from_str(result['remaining'])
        return result

