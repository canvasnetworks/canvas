from django.conf.urls.defaults import *
from canvas.shortcuts import direct_to_template
from canvas.view_guards import require_staff

urlpatterns = patterns('drawquest.apps.whitelisting.views',
    url(r'^$', 'whitelisting'),
    url(r'^/paginated/(?P<after_id>\d+)$', 'whitelisting_paginated'),

    url(r'^/flagged$', 'flag_queue'),
    url(r'^/flagged/paginated/(?P<after_id>\d+)$', 'flag_queue_paginated'),

    url(r'^/new$', 'new'),
    url(r'^/new/paginated/(?P<after_id>\d+)$', 'new_paginated'),

    url(r'^/all$', 'all'),
    url(r'^/all/paginated/(?P<after_id>\d+)$', 'all_paginated'),
)

