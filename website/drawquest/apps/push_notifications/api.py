from django.shortcuts import get_object_or_404

from canvas.exceptions import ServiceError
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.push_notifications import models

urlpatterns = []
api = api_decorator(urlpatterns)

@api('unsubscribe')
@require_user
def push_notifications_unsubscribe(request, notification_type):
    try:
        models.unsubscribe(request.user, notification_type)
    except ValueError as e:
        raise ServiceError(e.message)

@api('resubscribe')
@require_user
def push_notifications_resubscribe(request, notification_type):
    try:
        models.resubscribe(request.user, notification_type)
    except ValueError as e:
        raise ServiceError(e.message)

