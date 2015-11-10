from canvas import util
from canvas.metrics import Metrics
from canvas.notifications.email_channel import EmailChannel
from canvas.shortcuts import r2r_jinja
from canvas.models import unsubscribe_newsletter
from canvas.subscriptions import get_unsubscriptions, handle_unsubscribe_post
from drawquest.apps.drawquest_auth.models import User


def unsubscribe(request):
    token = request.REQUEST.get('token', '')
    email = request.REQUEST.get('email')

    ctx = {
        'token': token,
        'email': email,
        'unsubscribed': False,
        'unsubscribed_on_get': False,
        'unsubscribed_settings': None,
        'user': None,
        'error': False,
    }

    template_name = 'unsubscribe.html'

    if email and util.token(email) == token:
        # No user_id associated with the sent email, unsubscribe this email address from all email
        find_user = User.objects.filter(email=email)
        # If there is one and only one user with that email address, then pick them, otherwise we'll fall back to just an email address
        user = ctx['user'] = find_user[0] if find_user.count() == 1 else None
    else:
        ctx['error'] = True
        return r2r_jinja(template_name, ctx, request)

    all_actions = EmailChannel.all_handled_actions()

    if user:
        # Support for unsubscribe headers.
        # We support passing in 'actions'
        action = request.REQUEST.get('action')
        if action and (action in EmailChannel.all_handled_actions() or action.upper() == 'ALL'):
            ctx['unsubscribed_on_get'] = ctx['unsubscribed'] = True
            user.kv.subscriptions.unsubscribe(action)
            Metrics.unsubscribe_action.record(request, action=action, method=request.method)

        if request.method == 'POST':
            # Handle the 'ALL' case separately because the semantics for it are inverted.
            # ie, if ALL is checked, it means to DISABLE. While if REMIXED is checked, it means ENABLE.
            handle_unsubscribe_post(user, request.REQUEST, request)

        # We use this dictionary to render the checkboxes in the html.
        ctx['unsubscribed'] = ctx['unsubscribed'] or get_unsubscriptions(user, all_actions)

        ctx['unsubscribed_settings'] = get_unsubscriptions(user)
        template_name = 'unsubscribe_for_user.html'
    else:
        unsubscribe_newsletter(email)
        ctx['unsubscribed'] = True
        Metrics.unsubscribe_email_address.record(request)

    return r2r_jinja(template_name, ctx, request)

def test_realtime(request):
    from canvas.redis_models import RealtimeChannel
    from django.http import HttpResponse
    RealtimeChannel('qotd', 1).publish({'quest_id':1006})
    return HttpResponse('ok')

