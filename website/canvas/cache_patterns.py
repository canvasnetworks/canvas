from functools import wraps

import memcache
import simplejson

from canvas import util
from configuration import Config
from django.conf import settings

cache = memcache.Client(settings.MEMCACHE_HOSTS)


class DoesNotExist(object): pass

class InProcessCache(object):
    def __init__(self):
        self.flush()

    def flush(self):
        self.cache = {}

    def get(self, key):
        return self.cache.get(key, DoesNotExist)

    def set(self, key, value):
        self.cache[key] = value

    def delete(self, key):
        try:
            del self.cache[key]
        except KeyError:
            pass

    def __contains__(self, key):
        return key in self.cache

def _call_if_not_instance_of(key, cls, *args, **kwargs):
    """ If key is not an instance of cls, call it with *args and **kwargs, otherwise just return it. """
    return key(*args, **kwargs) if not isinstance(key, cls) else key
    
def memoize(key, time=24*60*60):
    """ A cache decorator that returns a CachedCall. Takes a key or a function that returns a key. """
    def decorator(fxn):
        def wrapper(*args, **kwargs):
            cache_key = _call_if_not_instance_of(key, str, *args, **kwargs)
            return CachedCall(cache_key, lambda: fxn(*args, **kwargs), time)
        return wrapper
    return decorator

def invalidates_cache(cc):
    """
    Invalidates the cache after the function executes. Takes a CachedCall or a function that returns a CachedCall.
    """
    def decorator(fxn):
        def wrapper(*args, **kwargs):
            # Invalidate the cache, given a CachedCall
            cache_call = _call_if_not_instance_of(cc, CachedCall, *args, **kwargs)
            # Execute and return the wrapped function
            try:
                return fxn(*args, **kwargs)
            finally:
                cache_call.invalidate()
        return wrapper
    return decorator

class CachedCall(object):
    # Note that inprocess_cache is a CLASS variable. It is instantiated the first time 
    # this class is parsed. It is then shared by all instances of CachedCall.
    inprocess_cache = InProcessCache()
    default_timeout = 24 * 60 * 60

    def __init__(self, key, function, timeout=default_timeout, decorator=lambda x: x, promoter=lambda x: x):
        #TODO `promoter` is a temporary hack until we can instantiate Details objs based on the cached data.
        self.key = key.encode('ascii')
        self.timeout = timeout
        self.function = function
        self.cache_decorator = decorator
        self.promoter = promoter

    def __eq__(self, other):
        return hasattr(other, 'key') and other.key == self.key

    def __hash__(self):
        return hash(self.key)

    def __call__(self, *args, **kwargs):
        return self._get(*args, **kwargs)

    def _get(self, force=False, skip_decorator=False):
        raw_value = self._fetch(force)
        value = self.promoter(raw_value)
        if not skip_decorator:
            return self.cache_decorator(value)
        else:
            return value

    def get_local_only(self):
        return self.inprocess_cache.get(self.key)

    def value_from_cache_data(self, cache_data):
        try:
            value = util.loads(cache_data)
        except:
            return DoesNotExist
        return value

    def invalidate(self):
        """ Just unsets the cache without re-caching. """
        # Remove from remote
        cache.delete(self.key)
        # Remove from class_variable/local cache.
        CachedCall.inprocess_cache.delete(self.key)

    def generate_cache_data(self):
        """ Sets the cache. """
        value = self.function()
        cache_data = self.remote_set(value)
        self.local_set(value)
        return cache_data

    def remote_set(self, value):
        """ Sets the remote cache. """
        cache_data = util.dumps(value)
        cache.set(self.key, cache_data, self.timeout)
        return cache_data

    def local_set(self, value):
        """ Sets the local cache. """
        self.inprocess_cache.set(self.key, value)

    def _fetch(self, force):
        if not force:
            # Can we find it in the local cache?
            value = self.get_local_only()
            if not value == DoesNotExist:
                return value

            # Is it in the remote cache?
            value = self.value_from_cache_data(cache.get(self.key))
            if not value == DoesNotExist:
                return value

        cache_data = self.generate_cache_data()
        return self.value_from_cache_data(cache_data)

    def force(self, *args, **kwargs):
        return self._get(force=True, *args, **kwargs)

    @classmethod
    def multicall(cls, calls, skip_decorator=False):
        if not calls:
            return []

        results = {}

        fetch_calls = []
        for call in set(calls):
            value = call.get_local_only()
            if value == DoesNotExist:
                fetch_calls.append(call)
            else:
                results[call] = value
                results[call] = call.promoter(results[call])

        todo = []
        multicall_results = cache.get_multi([call.key for call in fetch_calls])
        for call in fetch_calls:
            cache_data = multicall_results.get(call.key, DoesNotExist)
            value = call.value_from_cache_data(cache_data) if cache_data != DoesNotExist else DoesNotExist
            if value == DoesNotExist:
                todo.append(call)
            else:
                results[call] = value
                results[call] = call.promoter(results[call])

        for call in todo:
            results[call] = call.value_from_cache_data(call.generate_cache_data())
            if results[call]:
                results[call] = call.promoter(results[call])

        if not skip_decorator:
            for call, value in results.items():
                results[call] = call.cache_decorator(value)

        return [results[call] for call in calls]

    @classmethod
    def many_multicall(cls, *call_lists, **kwargs):
        concat = sum(call_lists, [])
        concat_results = cls.multicall(concat, **kwargs)
        start = 0
        results = []
        for call_list in call_lists:
            length = len(call_list)
            results.append(concat_results[start:start + length])
            start += length
        return results

    @classmethod
    def queryset_details(cls, queryset, **kwargs):
        return cls.multicall([obj.details for obj in queryset], **kwargs)


def cacheable(key):
    def decorator(func):
        #TODO Category.get_top = CachedCall('category:top_v2', Category._get_top)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return CachedCall(key, lambda: func(*args, **kwargs))()
        return wrapper
    return decorator

