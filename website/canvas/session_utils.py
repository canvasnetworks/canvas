"""
This module provides convenience methods for interacting with Django sessions.
"""
from datetime import timedelta, datetime
import time

__timestamped_key = lambda key: "%s_timestamp" % key

def store_ephemeral(request, key, value):
    """ Stores a creation-time timestamp for a session value.
    """
    # Current time
    timestamp = time.time()
    # We store the timestamp here. 
    timestamped_key = __timestamped_key(key)
    
    request.session[key] = value
    request.session[timestamped_key] = timestamp
    return value

def get_ephemeral(request, key, ttl=timedelta(days=1), default=None):
    """ Gets a value from the session based on a time-to-live.
    """
    # Was this value timestamped?
    timestamped_key = __timestamped_key(key)
    stored_timestamp = request.session.get(timestamped_key, None)
    if not stored_timestamp:
        # This was never an ephemeral value. Return it.
        return request.session.get(key, default)

    creation_time = datetime.fromtimestamp(stored_timestamp)
    
    if (datetime.now() - creation_time) > ttl:
        # Then the value is stale.
        # Delete it
        del request.session[key]
        del request.session[timestamped_key]
        return default
    
    return request.session.get(key)
