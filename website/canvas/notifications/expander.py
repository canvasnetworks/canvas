"""
The expander encapsulates the business logic of multiplexing notifications to specific channels and specific
recipients given a PendingNotification.

Note that a PendingNotification just tells us that someone "did" something, such as replied or remixed. It has no
channel information. The expander decides who should be notified (ie, actor or recipient(s)) and on which channels.
"""
from canvas.notifications.activity_stream_channel import ActivityStreamChannel
from canvas.notifications.email_channel import EmailChannel
from canvas.notifications.on_screen_channel import OnScreenChannel
from drawquest.apps.push_notifications.push_notification_channel import PushNotificationChannel

# Maps channel name to class. Notifications store the channel name. This allows us to grab the channel class.
channel_map = {
    'EmailChannel': EmailChannel,
    'OnScreenChannel': OnScreenChannel,
    'ActivityStreamChannel': ActivityStreamChannel,
    'PushNotificationChannel': PushNotificationChannel,
}


class BaseExpander:
    def expand(self, pending_notification):
        """
        Expands a pending notification. Only override this if you want to produce Notifications that do not all have
        the same action.

        pending_notification:
            An instance of PendingNotification

        Returns a list of Notification(s).
        """
        recipients = self.decide_recipients(pending_notification)
        # Remove dupes from recipients.
        recipients = list(set(recipients))
        return self.expand_entries_for_channels(pending_notification, recipients)

    def decide_recipients(self, pending_notification):
        """
        Returns a list of User who should be notified about this action.

        Override this in specific expanders to specify recipients.
        """
        return []

    def expand_entries_for_channels(self, pending_notification, recipients=[]):
        """
        Expands a PendingNotification to a list of Notification(s) given some recipients. For each recipient, it
        honors their unsubscription wishes/settings and the channel's own definitions of which actions it can handle.

        pending_notification:
            An instance of PendingNotification.
        recipients:
            A list of User(s).
        """
        from canvas.notifications.notification_models import Notification

        actor = pending_notification.actor
        action = pending_notification.action

        notifications = []
        # Get all the possible channels
        channels = channel_map.values()
        for channel_class in channels:
            # Does this channel know how to handle this type of notification when the user is an actor?
            if channel_class.enabled_for_actor_action(action, actor, pending_notification):
                # Note that the "recipient" here is the actor!
                entry = Notification.from_pending_notification(pending_notification,
                                                               actor,
                                                               channel_name=channel_class.__name__)
                notifications.append(entry)

            for recipient in recipients:
                if channel_class.enabled_for_recipient_action(action, recipient, pending_notification):
                    entry = Notification.from_pending_notification(pending_notification,
                                                                   recipient,
                                                                   channel_name=channel_class.__name__)
                    notifications.append(entry)
        return notifications


class RepliedExpander(BaseExpander):
    def expand(self, pending_notification):
        """
        We override expand, because we want to issue Notification(s) with actions that are more specific than
        'replied', like 'remixed' and 'thread_replied'.
        """
        comment = pending_notification.comment
        op_author = comment.thread.op.author

        action_tuples, recipients = [], []

        def add_action(recipient, action):
            """ Doesn't add duplicate recipients. So call this in order of priority. """
            if recipient not in recipients:
                recipients.append(recipient)
                action_tuples.append((recipient, action,))

        is_remix = bool(comment.reply_content and comment.reply_content.is_remix())
        is_at_reply = bool(comment.replied_comment)

        if is_at_reply:
            recipient = comment.replied_comment.author
            add_action(recipient, 'replied')

        if is_remix and not comment.external_content.exists():
            try:
                # Note that we cannot get the specific Comment that the user has remixed.
                # The recipient here will be the first OC author of the content.
                recipient = comment.reply_content.remix_of.first_caption.author
                add_action(recipient, 'remixed')
            except AttributeError, e:
                # Then there was no first_caption. This is probably a draw from scratch.
                pass

        add_action(op_author, 'thread_replied')

        notifications = []
        for recipient, action in action_tuples:
            pending_notification.action = action
            notifications.extend(self.expand_entries_for_channels(pending_notification, [recipient]))

        # For all replies, make sure that we do not email the actor (the person who replied or remixed). Else, you'd
        # be getting emails for remixing your own work!
        return filter(lambda notification: notification.recipient != notification.actor, notifications)


def get_expander(pending_notification):
    """ Returns the appropriate expander given a pending_notification (based on its action). """
    return _expander_map.get(pending_notification.action, BaseExpander)

def expand(pending_notification):
    """
    The entry into this module.

    Expands a PendingNotification into zero or more Notification.
    """
    return get_expander(pending_notification)().expand(pending_notification)

def expand_and_deliver(pending_notification):
    """
    Expands this PendingNotification into multiple channel-specific notifications and then delivers them.

    Note that we do not maintain any delivery state here since we currently only handle instant notifications. This,
    however, becomes necessary once we add time delays to notifications.
    """
    notifications = expand(pending_notification)
    for notification in notifications:
        #TODO: Should we add these to the bg_work queue separately?
        deliver_notification(notification)
    return notifications

def deliver_notification(notification):
    channel_map[notification.channel]().deliver(notification)

class StickeredExpander(BaseExpander):
    def decide_recipients(self, pending_notification):
        """ We notify the author of the post when someone stickers her post. """
        comment_sticker = pending_notification.comment_sticker
        return [comment_sticker.comment.author]

class ActorOnlyExpander(BaseExpander):
    def decide_recipients(self, pending_notification):
        return [pending_notification.actor]

class InviteRemixerExpander(BaseExpander):
    def decide_recipients(self, pending_notification):
        return [pending_notification.invitee]

class InviteMonsterRemixerExpander(BaseExpander):
    def decide_recipients(self, pending_notification):
        return [pending_notification.invitee]

class FollowedByUserExpander(BaseExpander):
    def decide_recipients(self, pending_notification):
        return [pending_notification.followee]

class PostPromotedExpander(BaseExpander):
    def decide_recipients(self, pending_notification):
        return [pending_notification.comment.author]

class FacebookFriendJoinedExpander(BaseExpander):
    def decide_recipients(self, pending_notification):
        return [fb_friend.user for fb_friend in pending_notification.facebook_friends if fb_friend.user]

class StarredExpander(BaseExpander):
    def decide_recipients(self, pending_notification):
        from drawquest.apps.stars.models import has_starred

        if (pending_notification.actor.id != pending_notification.comment_sticker.comment.author.id
            and not has_starred(pending_notification.comment_sticker.comment, pending_notification.actor)):
            return [pending_notification.comment_sticker.comment.author]
        return []

class PlaybackExpander(BaseExpander):
    def decide_recipients(self, pending_notification):
        if pending_notification.actor.id != pending_notification.comment.author.id:
            return [pending_notification.comment.author]
        return []

class FolloweePostedExpander(BaseExpander):
    def decide_recipients(self, pending_notification):
        author = pending_notification.comment.author
        return author.followers()


# Maps an action to an expander.
_expander_map = {
    'replied': RepliedExpander,
    'stickered': StickeredExpander,
    'epic_stickered': StickeredExpander,
    'leveled_up': ActorOnlyExpander,
    'daily_free_stickers': ActorOnlyExpander,
    'invite_remixer': InviteRemixerExpander,
    'invite_monster_remixer': InviteMonsterRemixerExpander,
    'followed_by_user': FollowedByUserExpander,
    'post_promoted': PostPromotedExpander,
    'thread_promoted': PostPromotedExpander,
    'facebook_friend_joined': FacebookFriendJoinedExpander,
    'starred': StarredExpander,
    'followee_posted': FolloweePostedExpander,
    'playback': PlaybackExpander,
}

