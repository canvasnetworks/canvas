from django.conf.urls.defaults import *
from django.contrib import admin
from django.views.generic.simple import redirect_to
from django.views.decorators.cache import cache_page

from django.conf import settings

import apps.ip_blocking.admin
from apps.share_tracking import views
from canvas import api, sitemaps
from canvas.shortcuts import direct_to_template
from canvas.views import archive_links
from canvas.url_util import re_slug, re_int, re_group_slug, re_year, re_month, re_day, maybe

def cached(view):
    return cache_page(60*60*24*365*5, key_prefix='archive_cache')(view)

code_urls = [url(r'^%s$' % code, 'apps.signup.views.signup', kwargs={'skip_invite_code': code}) for code in settings.SHORT_CODES]
code_urls += [url(r'^%s$' % code, 'apps.signup.views.signup') for code in settings.CLOSED_SHORT_CODES]

static_urls = patterns('canvas.views',
    url(r'^archive_links$', cached(archive_links)),
    url(r'^archive_cats$', 'archive_cats'),
    url(r'^about$', 'about', name="about"),
    url(r'^code_of_conduct$', 'code_of_conduct'),
    url(r'^content_policy$', redirect_to, {'url': 'code_of_conduct'}),
    url(r'^dmca$', 'dmca'),
    url(r'^empty$', direct_to_template, kwargs={'template': 'empty.html'}),
    url(r'^privacy$', 'privacy'),
    url(r'^terms$', 'terms_of_service'),
    url(r'^jobs$', 'direct_to_template', kwargs={'template': 'jobs/jobs_ios_engineers.html'}),
    url(r'^jobs/designer$', 'direct_to_template', kwargs={'template': 'jobs/jobs_designer.html'}),
    url(r'^jobs/software_engineer$', 'direct_to_template', kwargs={'template': 'jobs/jobs_engineers.html'}),
    url(r'^jobs/ios_engineer$', 'direct_to_template', kwargs={'template': 'jobs/jobs_ios_engineers.html'}),
    url(r'^facebook_welcome_page$', 'facebook_welcome_page'),
)

root_urls = patterns('canvas.views',
    url(r'^$', 'frontpage', kwargs={'sort': 'hot', 'homepage': True}),
    url(r'^best$', 'frontpage', kwargs={'sort': 'best'}),
    url(r'^csrf_token', 'csrf_token'),
    (r'^feed', include('apps.feed.urls')),
    url(r'^invite$', 'invite'),
    url(r'^join$', 'join'),
    url(r'^login$', 'canvas_login'),
    url(r'^login_exit_iframe$', 'direct_to_django_template', kwargs={'template': 'exit_iframe.django.html', "breakout_url": "/login"}),
    url(r'^logout$', 'logout'),
    url(r'^all_stamps$', 'all_stamps'),
    (r'^monster', include('apps.monster.urls')),
    url(r'^new$', 'frontpage', kwargs={'sort':'new'}),
    # Note that ping is handled by special middleware.
    url(r'^onboarding', include('apps.onboarding.urls')),
    (r'^post_thread', include('apps.post_thread.urls')),
    url(r'^script/' + re_slug('short_id') + '$', 'script_view'),
    url(r'^signup_exit_iframe$', 'signup_exit_iframe'),
    url(r'^signup_help_exit_iframe$', 'direct_to_django_template', kwargs={'template': 'exit_iframe.django.html', "breakout_url": "/welcome?next=signup"}),
    url(r'^signup_link_exit_iframe$', 'direct_to_django_template', kwargs={'template': 'exit_iframe.django.html', "breakout_url": "/signup"}),
    url(r'^share_prompt$', 'signup_share_prompt'),
    url(r'^stamps_used/(?P<content>[a-z0-9]+)$', 'stamps_used'),
    url(r'^top$', 'frontpage', kwargs={'sort': 'top'}),
    url(r'^top/' + re_day + '$', 'frontpage', kwargs={'sort': 'top'}),
    url(r'^top/' + re_month + '$', 'frontpage', kwargs={'sort': 'top'}),
    url(r'^top/' + re_year + '$', 'frontpage', kwargs={'sort': 'top'}),
    url(r'^unsubscribe$', 'unsubscribe'),
    url(r'^user/' + re_slug('username') + '/?$', 'user_view', kwargs={'userpage_type':'top'}, name="user_link"),
    url(r'^user/' + re_slug('username') + '/edit/?$', 'user_edit'),
    url(r'^user/' + re_slug('username') + '/new/?$', 'user_view', kwargs={'userpage_type':'new'}),
    url(r'^user/' + re_slug('username') + '/anonymous/?$', 'user_view', kwargs={'userpage_type':'top_anonymous'}),
    url(r'^user/' + re_slug('username') + '/anonymous/new/?$', 'user_view', kwargs={'userpage_type':'new_anonymous'}),
    url(r'^user/' + re_slug('username') + '/stickered/?$', 'user_view', kwargs={'userpage_type':'stickered'}),
    url(r'^warning$', 'warning'),
    url(r'^warning/code_of_conduct$', 'blocking_coc'),
    url(r'^js_testing$', 'direct_to_django_template', kwargs={'template': 'js_testing.django.html'}),
    url(r'^landing/wall1$', 'remix_share_page'),
    url(r'^debug_fact_stream$', 'debug_fact_stream'),
    url(r'^public_api/', include('apps.public_api.urls')),
)

group_browse_urls = patterns('canvas.views',
    url(r'^' + re_group_slug('name') + '/?$', 'category', kwargs={'sort': 'hot'}),
    url(r'^' + re_group_slug('name') + '/about$', 'group_about'),
    url(r'^' + re_group_slug('name') + '/active$', 'category', kwargs={'sort': 'active'}),
    url(r'^' + re_group_slug('name') + '/best$', 'category', kwargs={'sort': 'best'}),
    url(r'^' + re_group_slug('name') + '/new$', 'category', kwargs={'sort': 'new'}),
    url(r'^' + re_group_slug('name') + '/top$', 'category', kwargs={'sort': 'top'}),
    url(r'^' + re_group_slug('name') + '/top/' + re_day + '$', 'category', kwargs={'sort': 'top'}),
    url(r'^' + re_group_slug('name') + '/top/' + re_month + '$', 'category', kwargs={'sort': 'top'}),
    url(r'^' + re_group_slug('name') + '/top/' + re_year + '$', 'category', kwargs={'sort': 'top'}),
)

tag_browse_urls = patterns('canvas.views',
    url(r'^' + re_group_slug('tag') + '/?$', 'tag', kwargs={'sort': 'hot'}),
    url(r'^' + re_group_slug('tag') + '/best$', 'tag', kwargs={'sort': 'top'}),
    url(r'^' + re_group_slug('tag') + '/new$', 'tag', kwargs={'sort': 'new'}),
)

group_urls = patterns('canvas.views',
    url(r'^new$', 'group_new'),
)

# All of these will be preceeded by the staff/ prefix.
staff_urls = patterns('canvas.views',
    url(r'^vanity_metrics$', 'staff_vanity_metrics'),
    url(r'^pulse$', 'staff_pulse'),
    url(r'^action$', 'staff_action'),
    url(r'^vintage$', 'staff_vintage'),
    url(r'^processlist$', 'processlist'),
    url(r'^flagged$', 'flagged'),
    url(r'^epic_sticker_messages$', 'epic_sticker_messages'),
    url(r'^numbers$', 'numbers'),
    url(r'^user$', 'staff_user_browse'),
    url(r'^user/' + re_slug('username') + '$', 'staff_user_view'),
    url(r'^moderator/' + re_slug('username') + '$', 'staff_user_view', kwargs={'key': 'moderator'}),
    url(r'^user/' + re_slug('username') + '/warn$', 'staff_user_warn'),
    url(r'^user/' + re_slug('username') + '/ban$', 'staff_user_ban'),
    url(r'^user/' + re_slug('username') + '/unban$', 'staff_user_unban'),
    url(r'^user/' + re_slug('username') + '/dilate$', 'staff_user_dilate'),
    url(r'^user/' + re_slug('username') + '/ip_history$', 'staff_user_ip_history'),
    url(r'^ip/' + re_slug('ip') + '/user_history$', 'staff_ip_user_history'),
    url(r'^exception$', 'staff_exception'),
    url(r'^noop$', 'staff_noop'),
    url(r'^sticker_values$', 'sticker_values'),
)

staff_urls += patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^logged_out_homepage$', 'apps.logged_out_homepage.views.homepage_admin'),
    url(r'^sticky_threads$', 'apps.sticky_threads.views.sticky_admin'),
    url(r'^image_types/p/' + re_slug('short_id')
                           + maybe('/'+re_int('page'))
                           + maybe('/reply/'+re_int('gotoreply'))
                           + '$',
        'apps.threads.views.thread', kwargs={'template_name': 'staff/image_types.django.html'}),
)

sitemaps = dict(categories=sitemaps.Categories, static_pages=sitemaps.StaticSitemap(static_urls))


password_reset_urls = patterns('',
    url(r'^password_reset$', 'django.contrib.auth.views.password_reset', kwargs={'template_name': 'password_reset_form.django.html', 'email_template_name': 'password_reset_email.django.html'}), # use 'from_email': 'passwordreset@example.com' when it lands in stable.
    url(r'^password_reset/done$', 'django.contrib.auth.views.password_reset_done', kwargs={'template_name': 'password_reset_done.django.html'}),
    url(r'^reset(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm', kwargs={'template_name': 'password_reset_confirm.django.html'}),
    url(r'^reset/done$', 'django.contrib.auth.views.password_reset_complete', kwargs={'template_name': 'password_reset_complete.django.html'}),
)

urlpatterns = patterns('',
    url('^staff$', 'canvas.views.staff_api_console'),
    (r'^staff/', include(staff_urls)),
    (r'^x/', include(tag_browse_urls)),
    (r'^t/', include(tag_browse_urls)),
    (r'^group/', include(group_urls)),

    url(r'^p/' + re_slug('short_id') + '/current/?$', 'apps.threads.views.thread', kwargs={'page': 'current'}),
    url(r'^p/' + re_slug('short_id')
               + maybe('/'+re_int('page'))
               + maybe('/reply/'+re_int('gotoreply'))
               + maybe('/(?P<sort_by_top>top)')
               + '/?$', 'apps.threads.views.thread'),

    url(r'^d/' + re_slug('short_id') + maybe('/'+re_int('page')) + maybe('/reply/'+re_int('gotoreply')), 'apps.share_page.views.share_detail'),

    (r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),

    (r'^settings', include('apps.user_settings.urls')),
    (r'^s/', include('apps.share_tracking.urls')),
    (r'^invite/', include('apps.invite_remixer.urls')),

    url(r'^home$', 'apps.logged_out_homepage.views.homepage'),

    url(r'^facebook_iframe/$', 'apps.facebook_app.views.facebook_iframe'),

    (r'^api/', include(api.urls)),
    (r'^', include(password_reset_urls)),
    (r'^', include(static_urls)),
    (r'^', include(root_urls)),

    # signup
    url(r'^signup$', 'apps.signup.views.signup'),
    url(r'^signup_prompt$', 'apps.signup.views.signup', kwargs={'template': 'signup_prompt.django.html', "success_redirect": "/signup_exit_iframe"}),
    url(r'^signup_share_prompt$', 'apps.signup.views.signup', kwargs={'template': 'signup_prompt.django.html', "success_redirect": "/share_prompt"}),
    *code_urls
)

from apps.sentry_debug import urls as sentry_debug_urls
urlpatterns += patterns('',
    url(r'sentry_debug/', include(sentry_debug_urls)),
)

