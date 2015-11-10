from django.conf.urls.defaults import *

from canvas.url_util import re_slug

urlpatterns = patterns('apps.share_tracking.views',
    url(re_slug('share_id') + '/?$', 'shared_url'),
)

