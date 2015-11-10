from canvas.redis_models import redis
from canvas.shortcuts import r2r_jinja
from drawquest.apps.comment_freeze import signals

def comment_freeze(request):
    ctx = {}

    if request.method == 'POST':
        ts = request.POST['comment_freeze_ts']

        if ts:
            redis.set('dq:comment_freeze_ts', ts)
        else:
            redis.delete('dq:comment_freeze_ts')

        signals.comment_freeze_ts_changed.send(None)

    ctx['comment_freeze_ts'] = redis.get('dq:comment_freeze_ts') or ''

    return r2r_jinja('comment_freeze/comment_freeze.html', ctx, request)

