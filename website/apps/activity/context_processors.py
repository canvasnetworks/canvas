def realtime_activity_stream_context(request):
    if not request.user.is_authenticated():
        return {}

    stream = request.user.redis.activity_stream_channel.sync()

    return {
        'activity_stream_channel': stream,
        'activity_stream_unseen': int(request.user.kv.activity_stream_unseen.get() or 0),
    }

