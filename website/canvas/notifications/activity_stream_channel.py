from django.conf import settings

from apps.activity import jinja_tags
from apps.activity.redis_models import (StickerActivity, EpicStickerActivity,
                                        LevelUpActivity, RemixActivity, DailyFreeStickersActivity,
                                        ThreadReplyActivity, ReplyActivity,
                                        RemixInviteActivity, MonsterRemixInviteActivity,
                                        FollowedByUserActivity, PostPromotedActivity, ThreadPromotedActivity)
from canvas import economy, util
from canvas.notifications.base_channel import CommunicationsChannel


class ActivityStreamChannel(CommunicationsChannel):
    """ Viewable at /activity """
    # This channel knows how to handle ...
    recipient_actions = [
        'daily_free_stickers',
        'epic_stickered',
        'followed_by_user',
        'invite_monster_remixer',
        'invite_remixer',
        'leveled_up',
        'remixed',
        'replied',
        'stickered',
        'thread_replied',
        'post_promoted',
        'thread_promoted',
        'starred',
        'playback',
        'followee_posted',
    ]

    def _action_leveled_up(self, notification):
        return LevelUpActivity({
            'reward_stickers':  notification.reward_stickers,
        }, actor=notification.actor)

    def _action_daily_free_stickers(self, notification):
        return DailyFreeStickersActivity({
            'reward_stickers': notification.reward_stickers,
        }, actor=notification.actor)

    def _action_stickered(self, notification):
        return StickerActivity.from_sticker(notification.actor, notification.comment_sticker)

    def _action_epic_stickered(self, notification):
        return EpicStickerActivity.from_sticker(notification.actor, notification.comment_sticker)

    def _action_remixed(self, notification):
        return RemixActivity.from_comment(notification.actor, notification.comment)

    def _action_thread_replied(self, notification):
        return ThreadReplyActivity.from_comment(notification.actor, notification.comment)

    def _action_replied(self, notification):
        return ReplyActivity.from_comment(notification.actor, notification.comment)

    def _action_invite_remixer(self, notification):
        return RemixInviteActivity.from_comment(notification.actor, notification.comment)

    def _action_invite_monster_remixer(self, notification):
        return MonsterRemixInviteActivity.from_comment(notification.actor, notification.comment)

    def _action_followed_by_user(self, notification):
        return FollowedByUserActivity.from_user(notification.actor, notification.followee)

    def _action_post_promoted(self, notification):
        return PostPromotedActivity.from_comment(notification.actor, notification.comment)

    def _action_thread_promoted(self, notification):
        return ThreadPromotedActivity.from_comment(notification.actor, notification.comment)

    def _action_starred(self, notification):
        from drawquest.activities import StarredActivity
        return StarredActivity.from_sticker(notification.actor, notification.comment_sticker)

    def _action_playback(self, notification):
        from drawquest.activities import PlaybackActivity
        return PlaybackActivity.from_comment(notification.actor, notification.comment)

    def _action_followee_posted(self, notification):
        from drawquest.activities import FolloweePostedActivity
        return FolloweePostedActivity.from_comment(notification.actor, notification.comment)

    def deliver(self, notification):
        activity = getattr(self, '_action_' + notification.action)(notification)

        recipient = notification.recipient

        if not recipient.redis.activity_stream.valid_activity_type(activity.TYPE):
            return

        recipient.redis.activity_stream.push(activity)

        payload = {'type': activity.TYPE, 'id': activity.id}

        if settings.HTML_APIS_ENABLED:
            payload['html'] = jinja_tags.activity_stream_item(activity, recipient)

        recipient.redis.activity_stream_channel.publish(payload)

        recipient.kv.activity_stream_unseen.increment()

