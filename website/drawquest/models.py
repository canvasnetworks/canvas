from datetime import timedelta as td

from cachecow.decorators import cached_function
from django.db.models.signals import post_save
from django.shortcuts import get_object_or_404, Http404

from canvas.models import UserInfo
from canvas.redis_models import RealtimeChannel
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.following import models as following_models
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.models import Quest
from website.apps.canvas_auth.models import User as CanvasUser


@cached_function(timeout=td(days=7), key=[
    'user_profile',
    lambda username: username,
])
def user_profile(username):
    user = get_object_or_404(User.objects.select_related('userinfo', 'userinfo__avatar'), username=username)

    if not user.is_active:
        raise Http404("Deactivated user.")

    follow_counts = following_models.counts(user)

    return {
        'user': user.details(),
        'bio': user.userinfo.bio_text,
        'quest_completion_count': Quest.completed_by_user_count(user),
        'follower_count': follow_counts['followers'],
        'following_count': follow_counts['following'],
    }

# Cache invalidation for user_profile.
post_save.connect(
    lambda sender, instance, **kwargs: user_profile.delete_cache(instance.username),
    sender=CanvasUser, dispatch_uid='post_save_for_user_profile_canvas_user', weak=False
)
post_save.connect(
    lambda sender, instance, **kwargs: user_profile.delete_cache(instance.username),
    sender=User, dispatch_uid='post_save_for_user_profile_user', weak=False
)
post_save.connect(
    lambda sender, instance, **kwargs: user_profile.delete_cache(instance.user.username),
    sender=UserInfo, dispatch_uid='post_save_for_user_profile_userinfo', weak=False
)
post_save.connect(
    lambda sender, instance, **kwargs: user_profile.delete_cache(instance.author.username),
    sender=QuestComment, dispatch_uid='post_save_for_completed_quest_ids_user_profile', weak=False
)

def user_profile_for_viewer(username, viewer=None):
    ret = user_profile(username)

    if viewer and viewer.is_authenticated() and viewer.username != username:
        user = get_object_or_404(User.objects.select_related('userinfo', 'userinfo__avatar'), username=username)

        ret['viewer_is_following'] = viewer.is_following(user)

    return ret

def realtime_sync(user):
    channel_ids = ['qotd']

    if user.is_authenticated():
        channel_ids.append(user.redis.activity_stream_channel.channel)
        channel_ids.append(user.redis.coin_channel.channel)

    channels = {}
    for channel_id in channel_ids:
        channel = RealtimeChannel(channel_id)
        channels[channel_id] = channel.sync()

    return channels

