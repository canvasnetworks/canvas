from apps.invite_remixer.urls import absolute_invite_url
from apps.tags.models import Tag
from canvas import stickers as canvas_stickers, experiments, knobs, last_sticker
from django.conf import settings

def followed_tags_context(request):
    following = []

    if request.user.is_authenticated():
        following = request.user.redis.followed_tags.zrevrange(0, knobs.FOLLOWED_TAGS_SHOWN)

    tag_channels = []
    for tag in following:
        tag_channels.append(Tag(tag).updates_channel.sync())

    return {
        'followed_tags': following,
        'tag_channels': tag_channels,
    }

