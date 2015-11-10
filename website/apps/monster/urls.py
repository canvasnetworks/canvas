from django.conf.urls.defaults import *

from canvas.url_util import re_slug, maybe

urlpatterns = patterns('apps.monster.views',
    url('^/$', 'landing'),
    url('^/create$', 'create'),
    url('^/random$', 'random'),
    url('^/api/browse$', 'api_browse_monsters'),
    url('^/api/details/' + re_slug('short_id') + '$', 'api_monster_details'),
    url('^/' + re_slug('short_id') + maybe('/' + re_slug('option')) + '$', 'view'),
)

