from django.shortcuts import get_object_or_404

from drawquest.api_decorators import api_decorator
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user

urlpatterns = []
api = api_decorator(urlpatterns)

#@api('')
#@require_user
#def (request):

