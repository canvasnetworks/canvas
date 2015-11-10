from canvas.redis_models import redis
from drawquest import knobs

def filter_frozen_comments(comments):
    #TODO pipelining.
    ts = redis.get('dq:comment_freeze_ts')
    id_ = redis.get('dq:comment_freeze_id')

    if ts is None and id_ is None:
        return comments

    if ts is not None:
        ts = float(ts)
        filtered = [comment for comment in comments if float(comment.timestamp) <= ts]

    if id_ is not None:
        id_ = long(id_)
        filtered = [comment for comment in comments if long(comment.id) <= id_]

    return filtered

