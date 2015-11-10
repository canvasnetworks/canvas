class CommunicationsChannel(object):
    """
    A communications channel is a concrete way of notifying people of things that happened to them or their
    Comment(s) on Canvas.
    """
    # A list of the actions that this channel can handle.
    # This depends on whether a user is an actor or a recipient.
    # You should override this for your specific channel.
    actor_actions = []
    recipient_actions = []
    
    @classmethod
    def all_handled_actions(cls):
        """ Returns a list of actions that this specific channel knows how to handle. """
        all_actions = cls.recipient_actions[:]
        all_actions.extend(cls.actor_actions[:])
        return all_actions
        
    @classmethod
    def enabled_for_actor_action(cls, action, actor, *args, **kwargs):
        """
        Can this channel handle this notification type for an actor?

        Honors unsubscribe rules for a given user.
        """
        return action in cls.actor_actions and actor.kv.subscriptions.can_receive(action, cls)

    @classmethod
    def enabled_for_recipient_action(cls, action, recipient, *args, **kwargs):
        """
        Can this channel handle this notification type for a recipient?

        Honors unsubscribe rules for a given user.
        """
        return action in cls.recipient_actions and recipient.kv.subscriptions.can_receive(action, cls)

    def deliver(self, notification_entry):
        pass

