import logging

from canvas.notifications.email_channel import EmailChannel
from canvas.notifications import expander
from canvas.redis_models import hbool

class UserNotificationsSubscription(object):
    """
    Stores notification unsubscriptions for users for a specific channel.

    For example, allows users to opt of of remix notifications for the EmailChannel but not for a (hypothetical 
    sms channel).
        
    By default, users are signed up for all email notifications. 

    This stores the actions that they SPECIFICALLY unsubscribed from, represented by a False in the underlying hash. 
    """
    @classmethod
    def DEFINITION(cls):
        """
        This is a static definition of all the default values of flags.

        This is used to construct the UserKV.
        """
        DEFINITION = {}
        channels = expander.channel_map.values()
        for channel in channels:
            DEFINITION[cls.make_channel_action_key(channel, "ALL")] = hbool(True)
            for action in channel.all_handled_actions():
                DEFINITION[cls.make_channel_action_key(channel, action)] = hbool(True)
        return DEFINITION

    def __init__(self, hash):
        self.hash = hash

    def unsubscribe(self, action, channel=EmailChannel):
        """ Unscubscribe from a specific notification on a specific channel. """
        self.hash.set(self.make_channel_action_key(channel, action), False)

    def subscribe(self, action, channel=EmailChannel):
        try:
            self.hash.delete(self.make_channel_action_key(channel, action))
        except KeyError:
            pass

    def unsubscribe_from_all(self, channel=EmailChannel):
        """ Never receive notifications on this channel. Use this to silence all emails. """
        # We store a special value for a blanket unsubscription.
        self.unsubscribe("ALL", channel)
        for action in channel.all_handled_actions():
            self.subscribe(action, channel)

    def can_receive(self, action, channel=EmailChannel):
        """ Returns False if the user is unsubscribed for this action on the given channel. True otherwise. """
        # Has the user unsubscribed from ALL?
        subscribed_to_all = self.hash.get(self.make_channel_action_key(channel, "ALL"), nocache=True)
        if not subscribed_to_all:
            return False
        if action.lower() == 'newsletter':
            return True
        return self.hash.get(self.make_channel_action_key(channel, action))

    # An alias for can_receive
    is_subscribed = can_receive

    @classmethod
    def make_channel_action_key(cls, channel, action):
        """ Builds the hash key for unsubscription. eg EmailChannel:remixed. """
        channel_name = channel.__name__.split(".").pop()
        return "%s:%s:unsubscribe" % (channel_name, action)


class PendingNotification(object):
    #TODO Need to figure out how to store this in Redis. For now, we do all the processing and expansion 
    # asynchronously in bgwork. So no need to store for now.
    def __init__(self, actor, action, **data):
        """
        `actor`:
            a User
        `action`:
            See canvas.notifications.actions.
        `data`:
            A dict mapping action arg names to their values (see Actions). The contents of this becomes
            the read-only attributes of this object.
        """
        self.actor = actor
        self.action = action
        self.data = data

    def __getattr__(self, name):
        return self.data.get(name)
        
    def to_client(self):
        def to_client(val):
            if hasattr(val, 'to_client'):
                return val.to_client()
            return val

        # First, fetch the data from the 
        return dict(actor=self.actor,
                    action=self.action,
                    data=dict(zip(self.data.keys(), [to_client(d) for d in self.data.values()])))

    def __repr__(self):
        d = self.to_client()
        del d['data']
        return unicode(d)


class Notification(PendingNotification):
    """
    A channel-specific notification.

    This is the data structure that gets handed over to the template that creates the message.
    """
    channel = None
    recipient = None

    def __init__(self, recipient, *args, **kwargs):
        self.recipient = recipient
        super(Notification, self).__init__(*args, **kwargs)

    @classmethod
    def from_pending_notification(cls, pn, recipient, channel_name):
        entity = cls(recipient=recipient, actor=pn.actor, action=pn.action, **pn.data)
        entity.channel = channel_name
        return entity

    def to_client(self):
        d = PendingNotification.to_client(self)
        d.update(recipient=self.recipient.to_client())
        return d

