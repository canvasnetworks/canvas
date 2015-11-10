from django.conf.urls.defaults import *
from django.views.decorators.cache import cache_page
from django.views.generic.simple import redirect_to

from canvas.shortcuts import direct_to_template
from canvas.url_util import re_slug, re_int, re_group_slug, re_year, re_month, re_day, maybe
from canvas.view_guards import require_staff, require_user
from drawquest import api
from website import urls as canvas_urls
from drawquest.apps.quests.urls import top_comments_urls


def cached(view):
    return cache_page(60*20, key_prefix='website_v2')(view)


admin_urls = patterns('',
    (r'^$', redirect_to, {'url': '/admin/x/everything'}),
    (r'^', include(canvas_urls.root_urls)),
    (r'^staff/comment_freeze$', include('drawquest.apps.comment_freeze.urls')),
    (r'^staff/whitelisting', include('drawquest.apps.whitelisting.urls')),
    url(r'^staff$', direct_to_template, kwargs={'template': 'staff/staff.html'}),
    (r'^staff/', include(canvas_urls.staff_urls)),
    (r'^api_console$', 'drawquest.apps.api_console.views.staff_api_console'),

    (r'^quests/', include('drawquest.apps.quests.urls')),

    (r'^x/', include(canvas_urls.tag_browse_urls)),
    (r'^t/', include(canvas_urls.tag_browse_urls)),

    url(r'^p/' + re_slug('short_id')
               + maybe('/'+re_int('page'))
               + maybe('/reply/'+re_int('gotoreply'))
               + maybe('/(?P<sort_by_top>top)')
               + '/?$', 'apps.threads.views.thread'),
)

urlpatterns = patterns('canvas.views',
    url(r'^js_testing$', 'direct_to_django_template', kwargs={'template': 'drawquest_js_testing.django.html'}),

    url(r'^login$', 'drawquest_login', kwargs={'default_next': '/', 'staff_protocol': 'http'}),
    url(r'^logout$', 'logout'),
)

urlpatterns += patterns('',
    (r'^download$', redirect_to, {'url': 'https://itunes.apple.com/us/app/drawquest-free-daily-drawing/id576917425?ls=1&mt=8'}),

    (r'^test_realtime$', 'drawquest.views.test_realtime'),

    (r'^admin/', include(admin_urls)),
    (r'^quests/', include(top_comments_urls)),
    (r'^api/', include(api.urls)),
    url(r'deauthorize_facebook_user', 'drawquest.apps.drawquest_auth.views.deauthorize_facebook_user'),
    url(r'^p/' + re_slug('short_id'), 'drawquest.apps.quest_comments.views.share_page'),
    (r'^password_reset/', include('drawquest.apps.drawquest_auth.urls')),
    (r'^quests/submit_quest', include('drawquest.apps.submit_quest.urls')),
    url(r'^unsubscribe$', 'drawquest.views.unsubscribe'),
    (r'^s/', include('apps.share_tracking.urls')),

    (r'^whitelisting', include('drawquest.apps.whitelisting.urls')),

    url(r'^$', require_user(cached(direct_to_template)), kwargs={'template': 'drawquest/index.html'}, name='drawquest_landing_page'),
    url(r'^about$', require_user(cached(direct_to_template)), kwargs={'template': 'drawquest/team.html'}, name='drawquest_team_page'),
    url(r'^privacy$', cached(direct_to_template), kwargs={'template': 'drawquest/privacy.html'}, name='drawquest_privacy_page'),
    url(r'^terms$', cached(direct_to_template), kwargs={'template': 'drawquest/terms.html'}, name='drawquest_terms_page'),
    url(r'^jobs$', require_user(cached(direct_to_template)), kwargs={'template': 'drawquest/jobs.html'}, name='drawquest_jobs_page'),

    url(r'^palettes$', require_staff(direct_to_template), kwargs={'template': 'drawquest/palettes.html'}, name='drawquest_palettes_page'),

    url(r'^app/about$', cached(direct_to_template), kwargs={'template': 'drawquest/app/about.html'}, name='drawquest_app_about_page'),
    url(r'^app/privacy$', cached(direct_to_template), kwargs={'template': 'drawquest/app/privacy.html'}, name='drawquest_app_privacy_page'),
    url(r'^app/terms$', cached(direct_to_template), kwargs={'template': 'drawquest/app/terms.html'}, name='drawquest_app_terms_page'),
)

