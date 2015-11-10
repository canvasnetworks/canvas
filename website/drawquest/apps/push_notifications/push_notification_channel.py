from apps.activity import jinja_tags
from canvas.notifications.base_channel import CommunicationsChannel
from drawquest.apps.push_notifications import models


class PushNotificationChannel(CommunicationsChannel):
    recipient_actions = [
        'quest_of_the_day',
        'new_palettes',
        'facebook_friend_joined',
        'starred',
    ]

    @classmethod
    def enabled_for_recipient_action(cls, action, recipient, pending_notification=None, *args, **kwargs):
        flag = super(PushNotificationChannel, cls).enabled_for_recipient_action(
            action, recipient, pending_notification=pending_notification, *args, **kwargs)

        try:
            return flag and not models.is_unsubscribed(recipient, action)
        except ValueError:
            return flag

    def _push(self, notification, alert, extra_metadata={}, badge=None):
        recipient = notification.recipient
        models.push_notification(notification.action, alert,
                                 recipient=recipient, extra_metadata=extra_metadata, badge=badge)

    def _action_facebook_friend_joined(self, notification):
        self._push(notification, "{} {} has joined DrawQuest!".format(notification.actor.facebookuser.first_name,
                                                                      notification.actor.facebookuser.last_name),
                   extra_metadata={'username': notification.actor.username})

    def _action_starred(self, notification):
        self._push(notification, "{} has starred your drawing!".format(notification.actor.username),
                   extra_metadata={
                       'comment_id': notification.comment_sticker.comment.id,
                       'quest_id': notification.comment_sticker.comment.parent_comment_id,
                   })

    def deliver(self, notification):
        getattr(self, '_action_' + notification.action)(notification)

