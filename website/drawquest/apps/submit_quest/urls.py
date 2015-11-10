from django.conf.urls.defaults import *

urlpatterns = patterns('drawquest.apps.submit_quest.views',
    url(r'^$', 'submit_quest_wrapper'),
    url(r'^/iframe', 'submit_quest'),
    url(r'^/success', 'success'),
)

