from django.shortcuts import get_object_or_404

from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.models import UserModerationLog
from canvas.view_guards import require_staff, require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.whitelisting import models

urlpatterns = []
api = api_decorator(urlpatterns)

@api('allow')
@require_staff
def whitelisting_allow(request, comment_id):
    comment = get_object_or_404(QuestComment.all_objects, id=comment_id)
    models.allow(request.user, comment)

@api('deny')
@require_staff
def whitelisting_deny(request, comment_id, disable_author=False):
    comment = get_object_or_404(QuestComment.all_objects, id=comment_id)
    models.deny(request.user, comment)

    if disable_author:
        author = comment.author
        author.is_active = False
        author.save()
        author.userinfo.details.force()

        UserModerationLog.append(
            user=author,
            moderator=request.user,
            action=UserModerationLog.Actions.warn,
        )

@api('enable')
@require_staff
def whitelisting_enable(request, from_id=None):
    models.enable(from_id=from_id)

@api('disable')
@require_staff
def whitelisting_disable(request):
    models.disable()

