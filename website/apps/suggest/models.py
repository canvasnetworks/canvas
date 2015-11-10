from random import sample

from django.db.models import Count

from canvas import knobs
from canvas.cache_patterns import memoize, CachedCall
import canvas.models

@memoize(key=lambda user: 'user:{}:most_stickered_unfollowed_users_v2'.format(user.id), time=7*24*60*60)
def get_most_stickered_unfollowed_users(user):
    """ Returns a CachedCall instance. """
    number_to_suggest = knobs.SUGGESTED_USERS_TO_FOLLOW_COUNT
    following = user.redis.following.smembers() | user.redis.muted_suggested_users.smembers()
    stickered = (canvas.models.User.objects.filter(comments__stickers__user=user, comments__stickers__type_id__lt=500)
                    .filter(is_active=True)
                    .exclude(id__in=following)
                    .annotate(num_stickers=Count('comments__author'))
                    .order_by('-num_stickers')
                    .values_list('username', 'id', 'num_stickers'))

    stickered = [stickered_user for stickered_user in stickered if stickered_user[0] != user.username]

    if len(stickered) >= number_to_suggest:
        return [{'username': x[0], 'id': x[1]} for x in stickered[0:number_to_suggest]]

    start = [{'username': x[0], 'id': x[1]} for x in stickered]
    whitelisted = get_whitelisted_user_ids()()
    ids = set([x['id'] for x in whitelisted])
    whitelisted_ids = ids - following
    whitelisted = [x for x in whitelisted if x['id'] in whitelisted_ids and x['id'] != user.id]

    wanted = number_to_suggest - len(start)
    if len(whitelisted) >= wanted:
        return start + [x for x in sample(whitelisted, (number_to_suggest - len(start)))]
    elif len(whitelisted) > 0:
        return start + [x for x in sample(whitelisted, len(whitelisted))]
    else:
        return start


@memoize(key=lambda user: 'user:{}:suggested_tags_v1'.format(user.id), time=7*24*60*60)
def get_suggested_tags(user):
    number_to_suggest = 3
    suggested = set(knobs.SUGGESTED_TOPICS)
    followed = set(user.redis.followed_tags[:]) | user.redis.muted_suggested_tags.smembers()
    unfollowed = suggested - followed

    # Add preview to tag
    unfollowed = [{'name': topic} for topic in unfollowed]
    topic_previews = canvas.models.Content.all_objects.filter(id__in=knobs.SUGGESTED_TOPIC_PREVIEWS.values())
    topic_previews = CachedCall.multicall([preview.details for preview in topic_previews])
    preview_mapping = dict([(content['id'], content) for content in topic_previews])
    for topic in unfollowed:
        topic['preview'] = preview_mapping.get(knobs.SUGGESTED_TOPIC_PREVIEWS[topic['name']])

    size = len(unfollowed)
    if size >= number_to_suggest:
        return sample(unfollowed, number_to_suggest)
    elif size > 0:
        return list(unfollowed)
    else:
        return []

@memoize(key='users:whitelisted_ids', time=7*24*60*60)
def get_whitelisted_user_ids():
    return [{'username':x[0], 'id':x[1]} for x in
            (canvas.models.User.objects.filter(username__in=knobs.SUGGESTED_USERS).values_list('username', 'id'))]

