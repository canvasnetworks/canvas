from canvas import economy, last_sticker
from canvas.notifications.base_channel import CommunicationsChannel


class OnScreenChannel(CommunicationsChannel):
    recipient_actions = [
        'stickered', 
        'epic_stickered',
        'invite_remixer',
        'invite_monster_remixer',
    ]
    
    def deliver(self, notification):
        if notification.action == 'invite_remixer':
            self.deliver_invite_remixer_message(notification)
        elif notification.action == 'invite_monster_remixer':
            self.deliver_invite_monster_remixer_message(notification)
        else:
            # Do the following for all types of stickering.
            last_sticker.set_sticker(notification.recipient, notification.comment_sticker)
            last_sticker.realtime_update_sticker_receipt(notification.recipient)

            # call appropriate function
            if notification.action == 'epic_stickered':
                self.deliver_epic_stickered_message(notification)

    def deliver_epic_stickered_message(self, notification):
        recipient = notification.recipient
        queue = recipient.redis.notifications
        info = {
            'type': 'big_stick', 
            'sticker': last_sticker.get_info(recipient),
        }

        message = notification.comment_sticker.epic_message
        if message and message.strip():
            info['message'] = message
            info['message_author'] = notification.comment_sticker.user.username
            info['thumbnail_url'] = notification.comment_sticker.comment.details().get_thumbnail_absolute_url(),

        queue.send(info)

    def deliver_invite_remixer_message(self, notification):
        recipient = notification.recipient
        queue = recipient.redis.notifications
        actor = "Someone" if notification.comment.anonymous else notification.actor.username
        queue.send({
            'type': 'invite_remixer', 
            'actor': actor,
            'comment_url': notification.comment.get_absolute_url(),
            'thumbnail_url': notification.comment.details().get_thumbnail_absolute_url(),
            'invitee': notification.invitee.username,
        })

    def deliver_invite_monster_remixer_message(self, notification):
        recipient = notification.recipient
        queue = recipient.redis.notifications
        actor = "Someone" if notification.comment.anonymous else notification.actor.username
        queue.send({
            'type': 'invite_monster_remixer', 
            'actor': actor,
            'comment_url': notification.comment.get_absolute_url(),
            'thumbnail_url': notification.comment.details().get_thumbnail_absolute_url(),
            'invitee': notification.invitee.username,
        })

