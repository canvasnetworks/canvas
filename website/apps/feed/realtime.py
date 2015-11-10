from apps.feed.redis_models import visible_in_feed, users_promoted_comment_at
from canvas import knobs
from canvas.redis_models import RealtimeChannel

def updates_channel(followed_user):
    if hasattr(followed_user, 'id'):
        followed_user = followed_user.id
    return RealtimeChannel('fu:{}'.format(followed_user), 20)

def publish_new_comment(new_comment):
    from canvas.models import UserRedis

    if not visible_in_feed({'comment': new_comment.details(), 'type': 'post'}):
        return

    author = new_comment.author

    # Bump unseen counts.
    for user_id in author.redis.followers.smembers():
        user_redis = UserRedis(user_id)
        user_redis.user_kv.hincrby('feed_unseen', 1)

    updates_channel(author).publish({'comment': new_comment.id, 'type': 'post'})

def publish_promoted_comment(comment_sticker, promoter):
    if comment_sticker.cost < knobs.FEED_PROMOTION_STICKER_COST_THRESHOLD:
        return

    from canvas.models import UserRedis

    comment = comment_sticker.comment

    if not visible_in_feed({'comment': comment.details(), 'type': 'promotion'}):
        return

    # Bump unseen counts for users who wouldn't already have this in their feed.
    for user_id in promoter.redis.followers.smembers():
        user_redis = UserRedis(user_id)

        following_ids = user_redis.following.smembers()

        if str(comment.author_id) in following_ids or str(comment.author_id) == str(user_id):
            # User already follows this author, or this author is the user himself.
            continue

        first_ts = users_promoted_comment_at(following_ids, comment)

        try:
            if float(first_ts) <= float(user_redis.user_kv.hget('feed_last_viewed')):
                # User viewed the feed after this was promoted.
                continue
        except TypeError:
            continue

        user_redis.user_kv.hincrby('feed_unseen', 1)

    updates_channel(promoter).publish({'comment': comment.id, 'type': 'promotion'})

