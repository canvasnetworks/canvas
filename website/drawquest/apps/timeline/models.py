from django.db import models
from django.conf import settings
from facebook import GraphAPIError, GraphAPI
from sentry.client.models import client

from canvas import bgwork
from canvas.exceptions import ServiceError
from canvas.metrics import Metrics
from canvas.models import FacebookUser
from drawquest import economy

def complete_quest(user, quest_comment, access_token, request=None):
    if user.id != quest_comment.author_id:
        raise ServiceError("You can't share to your timeline a drawing you didn't create.")

    try:
        user.facebookuser
    except FacebookUser.DoesNotExist:
        raise ServiceError("Can't share to your timeline if you haven't added your Facebook account yet.")

    # Although we've renamed it to "draw", Facebook still internally refers to it as "complete".
    action = 'complete'

    quest_url = quest_comment.get_share_page_url_with_tracking(user, 'facebook', absolute=True)

    @bgwork.defer
    def rewards():
        economy.credit_personal_share(user)

    send_action = '{}:{}'.format(settings.FACEBOOK_NAMESPACE, action)

    @bgwork.defer
    def do_graph_action():
        try:
            graph = GraphAPI(access_token)
            graph.put_object('me', send_action, quest=quest_url)
            if request:
                Metrics.share_to_timeline.record(request, quest=quest_url)
        except GraphAPIError as e:
            if request:
                Metrics.share_to_timeline_error.record(request, quest=quest_url)
            client.create_from_exception()

