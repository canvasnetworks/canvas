from django.conf.urls.defaults import url, patterns
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from canvas.api_decorators import json_response
from canvas.exceptions import ServiceError
from canvas.view_guards import require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.playback.models import Playback, PlaybackData
from drawquest.apps.quest_comments.models import QuestComment

urlpatterns = []
api = api_decorator(urlpatterns)

@api('playback')
def playback_drawing(request, comment_id):
    comment = get_object_or_404(QuestComment, id=comment_id)

    if request.user.is_authenticated():
        Playback.append(comment=comment, viewer=request.user)

    return {'comment': comment.details()}

@api('playback_data')
def playback_data(request, comment_id):
    comment = get_object_or_404(QuestComment, id=comment_id)

    try:
        data = comment.playback_data.json_data
    except (PlaybackData.DoesNotExist, AttributeError,):
        data = None

    return {'playback_data': data}

@csrf_exempt
@json_response
@require_user
def set_playback_data(request):
    try:
        comment_id = request.POST['comment_id']
    except KeyError:
        raise ServiceError("Missing comment ID.")

    comment = get_object_or_404(QuestComment, id=comment_id)

    playback_data = request.POST['playback_data']

    PlaybackData.create_with_json(comment, playback_data)


urlpatterns += patterns ('',
    url(r'^set_playback_data$', set_playback_data),
)

