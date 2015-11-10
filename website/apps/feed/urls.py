from django.conf.urls.defaults import *

urlpatterns = patterns('apps.feed.views',
    url(r'^$', 'feed', name='feed'),
)

