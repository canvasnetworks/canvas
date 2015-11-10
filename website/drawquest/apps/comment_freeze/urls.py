from django.conf.urls.defaults import *

urlpatterns = patterns('drawquest.apps.comment_freeze.views',
    url(r'^$', 'comment_freeze'),
)

