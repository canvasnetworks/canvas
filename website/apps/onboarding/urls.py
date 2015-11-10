from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to

from apps.onboarding.flow import ONBOARDING_START


urlpatterns = patterns('',
    (r'^/start$', 'apps.onboarding.views.start'),
    (r'^/welcome$', 'apps.onboarding.views.welcome_tutorial'),
    (r'^/finish$', 'apps.onboarding.views.finish'),
    (r'^/follow$', 'apps.onboarding.views.suggested_users'),
)

