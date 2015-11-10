from canvas.metrics import Metrics
from canvas.notifications.email_channel import EmailChannel


def get_unsubscriptions(user, action_list=EmailChannel.all_handled_actions()):
    d = {}
    for action in action_list:
        if not user.kv.subscriptions.can_receive(action):
            d[action] = True
        else:
            d[action] = False

    d['ALL'] = not user.kv.subscriptions.can_receive('ALL')
    return d

def handle_unsubscribe_post(user, actions_dict, request):
    subscriptions = user.kv.subscriptions
    all_actions = EmailChannel.all_handled_actions()

    unsubscribe_from_all = actions_dict.get('ALL', False)
    if unsubscribe_from_all:
        subscriptions.unsubscribe_from_all()
        Metrics.unsubscribe_all.record(request)
        return
    elif not subscriptions.can_receive('ALL'):
        # Remove the blanket ban, and honor individual preferences.
        subscriptions.subscribe('ALL')
        return

    # Handle the rest of the actions.
    for action in all_actions:
        if bool(actions_dict.get(action, False)):
            subscriptions.subscribe(action)
        else:
            # It was unchecked. So unsubscribe.
            subscriptions.unsubscribe(action)
            Metrics.unsubscribe_action.record(request, action=action, method=request.method)

