from django.conf.urls.defaults import *

from canvas.url_util import re_slug, re_int, re_group_slug, re_year, re_month, re_day, maybe

urlpatterns = patterns('apps.public_api.views',
    url('^$', 'root'),
    url('^posts/' + maybe(re_slug('short_id')) + '$', 'posts'),
    url('^users/' + maybe(re_slug('username')) + '$', 'users'),
    url('^groups/' + maybe(re_group_slug('group_name')) + '$', 'groups'),
)

