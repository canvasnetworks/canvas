from urbanairship import Airship
from django.conf import settings

from canvas import util
from canvas.metrics import Metrics
from canvas.redis_models import RedisSet

GLOBAL_PUSH_NOTIFICATION_TYPES = {
    'quest_of_the_day':         0,
    'new_palettes':             1,
}

PERSONAL_PUSH_NOTIFICATION_TYPES = {
    'starred':                  2,
    'facebook_friend_joined':   3,
}

def push_notification(notification_type, alert, extra_metadata={}, recipient=None, badge=None, request=None):
    """
    `recipient` is a User instance.
    """
    ua = Airship(settings.URBANAIRSHIP_APP_KEY, settings.URBANAIRSHIP_APP_MASTER_SECRET)
    type_ = notification_type

    payload = {'aps': {'alert': alert}, 'push_notification_type': notification_type}
    payload.update(extra_metadata)

    if badge is not None:
        payload['aps']['badge'] = badge

    if type_ in GLOBAL_PUSH_NOTIFICATION_TYPES:
        if settings.PRODUCTION:
            #TODO, only send to this tag with .push: tags=[notification_type])
            ua.broadcast(payload)
            util.logger.info("Sent global push notification with alert: {}".format(alert))
    elif type_ in PERSONAL_PUSH_NOTIFICATION_TYPES:
        if settings.PRODUCTION and not is_unsubscribed(recipient, type_):
            ua.push(payload, aliases=[recipient.username])
    else:
        raise ValueError("Invalid push notification type '{}'.".format(notification_type))


# Subscriptions only matter for personal notifications. Global notification subscriptions are handled on the device.

unsubscriptions = dict((name, RedisSet('push_notification:{0}:unsubscriptions'.format(id_)),)
                       for name, id_ in PERSONAL_PUSH_NOTIFICATION_TYPES.items())

def _check_personal_type(push_notification_type):
    if push_notification_type not in PERSONAL_PUSH_NOTIFICATION_TYPES:
        raise ValueError("Invalid personal push notification type '{}'".format(push_notification_type))

def unsubscribe(user, push_notification_type):
    _check_personal_type(push_notification_type)
    unsubscriptions[push_notification_type].sadd(user.id)

def resubscribe(user, push_notification_type):
    _check_personal_type(push_notification_type)
    unsubscriptions[push_notification_type].srem(user.id)

def unsubscribers(push_notification_type):
    _check_personal_type(push_notification_type)
    return unsubscriptions[push_notification_type].smembers()

def is_unsubscribed(user, push_notification_type):
    _check_personal_type(push_notification_type)
    return str(user.id) in unsubscriptions[push_notification_type]

def is_subscribed(user, push_notification_type):
    return not is_unsubscribed(user, push_notification_type)

