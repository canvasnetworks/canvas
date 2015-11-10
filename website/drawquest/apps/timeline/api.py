from django.shortcuts import get_object_or_404

from drawquest.api_decorators import api_decorator
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.timeline.models import complete_quest
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user

urlpatterns = []
api = api_decorator(urlpatterns)

@api('share_completed_quest_to_timeline')
@require_user
def share_completed_quest_to_timeline(request, comment_id, facebook_access_token):
    comment = get_object_or_404(QuestComment, id=comment_id)
    complete_quest(request.user, comment, facebook_access_token, request=request)

