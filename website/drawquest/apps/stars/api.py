from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from canvas.models import Metrics
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.stars import models
from drawquest.apps.stars.rate_limiting import check_star_rate_limit

urlpatterns = []
api = api_decorator(urlpatterns)

@api('star')
@require_user
def star_comment(request, comment_id):
    comment = get_object_or_404(QuestComment, id=comment_id)

    check_star_rate_limit(request, comment)

    models.star(request.user, comment, ip=request.META['REMOTE_ADDR'])
    Metrics.star.record(request, comment=comment.id)

    comment_details = comment.details()

    return {'comment': comment.details()}

@api('unstar')
@require_user
def unstar_comment(request, comment_id):
    comment = get_object_or_404(QuestComment, id=comment_id)

    models.unstar(request.user, comment)
    Metrics.unstar.record(request, comment=comment.id)

    comment_details = comment.details()

    return {'comment': comment.details()}

