from django.conf.urls.defaults import *

from canvas.view_guards import require_staff
from canvas.views import direct_to_django_template

urlpatterns = patterns('',
    (r'^js_error$', require_staff(direct_to_django_template), {'template': 'sentry_debug/js_error.django.html'}),
)

