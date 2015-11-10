import apps.feed.realtime

def realtime_feed_context(request):
    if not request.user.is_authenticated():
        return {}

    followees = request.user.redis.following.smembers()
    feed_following_channels = [apps.feed.realtime.updates_channel(followee_id).sync()
                               for followee_id in followees]

    return {
        'feed_following_channels': feed_following_channels,
        'feed_unseen': int(request.user.kv.feed_unseen.get() or 0),
    }

