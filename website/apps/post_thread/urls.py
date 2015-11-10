from django.conf.urls.defaults import *

urlpatterns = patterns('apps.post_thread.views',
    url('^$', 'post_thread', name='post_thread'),
    url('^/popup$', 'popup_post_thread'),
    url('^/popup/posted$', 'popup_thread_posted'),
)

