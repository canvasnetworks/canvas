#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Description:

History:
   * 2010-05-16T15:54:22+0400 Initial commit. Version 0.1 released.
"""

__author__ = 'Nikolay Panov (author@niksite.ru)'
__license__ = 'BSD'
__version__ = 0.1
__updated__ = '2010-05-16 15:55:34 nik'

try:
    import cPickle as pickle
except ImportError:
    import pickle

import urlparse
import redis
import zlib
from django.core.cache.backends.base import BaseCache
from django.utils.encoding import smart_unicode, smart_str


class CacheClass(BaseCache):

    def __init__(self, server, params):
        "Connect to Redis, and set up cache backend."
        BaseCache.__init__(self, params)
        self._cache = redis.Redis(server.split(':')[0], db=int(params.get('db', 1)))
        self._headers = {'zlib': '!zlib!',
                         'pickle': '!pickle!'}

    def _prepare_key(self, raw_key):
        "``smart_str``-encode the key."
        return smart_str(raw_key)

    def _check_header(self, header, value):
        """Check whether this value has this header"""
        header_marker = self._headers.get(header)
        if header_marker and \
               isinstance(value, str) and \
               value[:len(header_marker)] == header_marker:
            value = value[len(header_marker):]
            if header == 'zlib':
                value = zlib.decompress(value)
            if header == 'pickle':
                value = pickle.loads(value)
        return value

    def _pack_value(self, value):
        """Pack value, use pickle and/or zlib if necessary"""
        if isinstance(value, str):
            pass
        elif isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, int) or isinstance(value, float):
            value = str(value)
        else:
            value = self._headers['pickle'] + pickle.dumps(value)
        # zlib.compress if value is long enough
        if len(value) > 1000:
            value = self._headers['zlib'] + zlib.compress(value)
        return value

    def _unpack_value(self, value):
        """unpack value, use pickle and/or zlib if necessary"""
        value = self._check_header('zlib', value)
        value = self._check_header('pickle', value)
        if isinstance(value, basestring):
            return smart_unicode(value)
        else:
            return value

    def add(self, key, value, timeout=0):
        """Add a value to the cache, failing if the key already exists.
        Returns ``True`` if the object was added, ``False`` if not.
        """
        if self._cache.exists(key):
            return False
        return self.set(key, value, timeout)

    def set(self, key, value, timeout=None):
        "Persist a value to the cache, and set an optional expiration time."

        key = self._prepare_key(key)

        # store the key/value pair
        result = self._cache.set(key, self._pack_value(value))

        # set content expiration, if necessary
        if timeout != -1:
            self._cache.expire(key, timeout or self.default_timeout)

        return result

    def get(self, key, default=None):
        """Retrieve a value from the cache.
        Returns unpicked value if key is found, ``None`` if not.
        """
        key = self._prepare_key(key)

        # get the value from the cache
        value = self._cache.get(key)

        if value is None:
            return default
        else:
            return self._unpack_value(value)

    def delete(self, key):
        "Remove a key from the cache."
        key = self._prepare_key(key)
        self._cache.delete(key)

    def flush(self, all_dbs=False):
        self._cache.flush(all_dbs)

    def close(self, **kwargs):
        "Disconnect from the cache."
        pass

# Emacs:
# Local variables:
# time-stamp-pattern: "100/^__updated__ = '%%'$"
# End:
