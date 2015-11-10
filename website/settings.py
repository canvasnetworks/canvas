# -*- coding: utf-8 -*-
# Django settings for Canvas.

import copy
import logging
import platform

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS

from settings_common import *
from settings_sentry_common import *

PROJECT = 'canvas'

CANVAS_SUB_SITE = '/'

if PRODUCTION:
    DOMAIN = "example.com"
    SELF_PORT = 9000
    SELF = 'localhost:9000'
    UGC_HOST = 'i.canvasugc.com'
    FACEBOOK_APP_ACCESS_TOKEN = "REDACTED"
    FACEBOOK_APP_ID = "REDACTED"
    FACEBOOK_APP_SECRET = "REDACTED"
    FACEBOOK_NAMESPACE = "REDACTED"
    URBANAIRSHIP_APP_KEY = "REDACTED"
    URBANAIRSHIP_APP_SECRET = "REDACTED"
    URBANAIRSHIP_APP_MASTER_SECRET = "REDACTED"
else:
    DOMAIN = "savnac.com"
    # We're port forwarding 80 -> 9000
    SELF_PORT = 80
    SELF = 'localhost'
    UGC_HOST = 'ugc.savnac.com'
    FACEBOOK_APP_ACCESS_TOKEN = "REDACTED"
    FACEBOOK_APP_ID = "REDACTED"
    FACEBOOK_APP_SECRET = "REDACTED"
    FACEBOOK_NAMESPACE = "REDACTED"
    URBANAIRSHIP_APP_KEY = "REDACTED"
    URBANAIRSHIP_APP_SECRET = "REDACTED"
    URBANAIRSHIP_APP_MASTER_SECRET = "REDACTED"

# To get to the mysql shell:
#    mysql -h <hostname> -u canvas -p<press enter><paste pw from below>
if PRODUCTION:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'canvas',
            'USER': 'canvas',
            'PASSWORD': "REDACTED",
            'HOST': '',
            'PORT': '',
        }
    }
elif TESTING_USE_MYSQL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'canvas',
            'USER': 'root',
            'PASSWORD': '',
            'HOST': 'localhost',
            'PORT': '',
            'OPTIONS': {
                # http://stackoverflow.com/questions/11853141/foo-objects-getid-none-returns-foo-instance-sometimes
                'init_command': 'SET SQL_AUTO_IS_NULL=0;',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': 'db.sqlite',                      # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }

# Before we go multi-web-frontend this should probably get moved into memcache or redis
CACHE_BACKEND = 'locmem://?max_entries=1000'  # Seriously? Gross. Django 1.3 turns this into a proper dictionary.

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_PATH, 'static/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = "REDACTED"

# List of callables that know how to import templates from various sources.
if DEBUG:
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )
else:
    TEMPLATE_LOADERS = (
        ('django.template.loaders.cached.Loader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ),),
    )

MIDDLEWARE_CLASSES = (
    'canvas.middleware.PingMiddleware',
    'canvas.middleware.ExceptionLogger',
    'canvas.middleware.HandleLoadBalancerHeaders',
    'canvas.middleware.DeferredWorkMiddleware',

    'django.middleware.common.CommonMiddleware',
    'canvas.middleware.UploadifyIsALittleBitchMiddleware',
    'canvas.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    'apps.canvas_auth.middleware.SessionMigrationMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.canvas_auth.middleware.AnonymousUserMiddleware',

    'canvas.middleware.RedirectToHttpsMiddleware',

    'canvas.experiments.ForceExperimentMiddleware',
    'canvas.middleware.FacebookMiddleware',
    'canvas.middleware.ImpersonateMiddleware',
    'apps.mobile.middleware.MobileDetectionMiddleware',

    'canvas.middleware.RequestSetupMiddleware',

    'canvas.middleware.SandboxMiddleware',
    'canvas.middleware.StaffOnlyMiddleware',
    'canvas.middleware.IPHistoryMiddleware',

    'canvas.middleware.GlobalExperimentMiddleware',
    'canvas.middleware.SeasonalStickerMiddleware',
    'canvas.middleware.HttpRedirectExceptionMiddleware',
    'canvas.middleware.Django403Middleware',
    'canvas.middleware.HttpExceptionMiddleware',

    'canvas.middleware.MinifyHTMLMiddleware',

    'apps.canvas_auth.middleware.HttpBasicAuthMiddleware',

    'canvas.middleware.TimeDilationMiddleware',

    'apps.activity.middleware.ActivityReadMiddleware',

    'apps.share_tracking.middleware.TrackShareViewsMiddleware',
    'apps.share_tracking.middleware.TrackClickthroughMiddleware',
    'apps.invite_remixer.middleware.TrackInviteMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'canvas.middleware.ResponseGuard',
)

AUTHENTICATION_BACKENDS = (
    'apps.canvas_auth.backends.CanvasAuthBackend',
)

HTTP_AUTH_REALM = 'canvas'

DJANGO_DEFAULT_CONTEXT_PROCESSORS = copy.copy(TEMPLATE_CONTEXT_PROCESSORS)

TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.request',
    'canvas.context_processors.base_context',
    'apps.invite_remixer.context_processors.invite_remixer_context',
    'apps.onboarding.context_processors.onboarding_context',
    'apps.activity.context_processors.realtime_activity_stream_context',
    'apps.features.context_processors.features_context',
    'apps.feed.context_processors.realtime_feed_context',
    'apps.tags.context_processors.followed_tags_context',
)

LOGIN_URL = '/login'

ROOT_URLCONF = 'urls'

REDIS_HOST = Config['redis_host']
REDIS_PORT = 6379

if not TESTING:
    REDIS_DB_MAIN = 0
    REDIS_DB_CACHE = 1
    SESSION_REDIS_DB = 2
else:
    REDIS_DB_MAIN = 4
    REDIS_DB_CACHE = 5
    SESSION_REDIS_DB = 6

SESSION_ENGINE = 'redis_sessions.session'

SESSION_REDIS_HOST = REDIS_HOST
SESSION_REDIS_PORT = REDIS_PORT
SESSION_REDIS_PREFIX = None

MEMCACHE_HOSTS = Config['memcache_hosts']

FACT_HOST = Config['fact_host']
FACT_BUCKET = 'canvas-facts'

IMAGE_FS = Config['image_fs']

HTTPS_ENABLED = True
UGC_HTTPS_ENABLED = HTTPS_ENABLED

TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, 'templates'),
)

INSTALLED_APPS = (
    'apps.monkey_patch_django',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django.contrib.humanize',
    'django.contrib.messages',

    'south',
    'compressor',
    'debug_toolbar',
    'django_bcrypt',

    'apps.activity',
    'apps.analytics',
    'apps.canvas_auth',
    'apps.comments',
    'apps.facebook_app',
    'apps.features',
    'apps.feed',
    'apps.following',
    'apps.comment_hiding',
    'apps.invite_remixer',
    'apps.ip_blocking',
    'apps.jinja_adapter',
    'apps.logged_out_homepage',
    'apps.mobile',
    'apps.monster',
    'apps.onboarding',
    'apps.post_thread',
    'apps.share_tracking',
    'apps.signup',
    'apps.sticky_threads',
    'apps.suggest',
    'apps.tags',
    'apps.user_settings',
    'apps.threads',

    'canvas',
)

if PRODUCTION:
    pass #INSTALLED_APPS += ('sentry.client',)
else:
    INSTALLED_APPS += ('django_nose',)
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_ARGS = ['--exclude=compressor', '--exclude=drawquest', '-d']

    INSTALLED_APPS += ('apps.sentry_debug',)
    SENTRY_CLIENT = 'sentry.client.base.DummyClient'

#TODO this is unused, at least in Django 1.2?
STATIC_PATH = os.path.join(PROJECT_PATH, "static")

MINIFY_HTML = not TESTING and not LOCAL_SANDBOX

# django-compressor settings
COMPRESS = COMPRESS_ENABLED = True

# Just concatenate Javascript
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter'] if not DEBUG else []
COMPRESS_MTIME_DELAY = 0

# Just concatenate CSS
COMPRESS_CSS_FILTERS = []
COMPRESS_CACHE_BACKEND = 'redis_cache.cache://%s:%s/?timeout=1500&db=%s' % (REDIS_HOST, REDIS_PORT, REDIS_DB_CACHE)
COMPRESS_OFFLINE = not TESTING and not LOCAL_SANDBOX

if COMPRESS_OFFLINE:
    COMPRESS_STORAGE = 'canvas.storage.CanvasFileStorage'

class CompressFakeRequest(object):
    def __init__(self):
        self.PRODUCTION = PRODUCTION
        self.GET = {}

COMPRESS_OFFLINE_CONTEXT = {
    'request': CompressFakeRequest(),
    'DEBUG': DEBUG,
    'GET': {},
}

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG and (request.path.startswith('/__debug__/') or request.GET.get('debug_toolbar', False))
}

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'canvas.debug.RedisPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
)


if PRODUCTION:
    EMAIL_BACKEND = 'django_ses.SESBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = os.path.join(PROJECT_PATH, 'run/sent_mail.log')

# Used for the django_ses e-mail backend
AWS_ACCESS_KEY_ID = Config['aws']['access_key']
AWS_SECRET_ACCESS_KEY = Config['aws']['secret_key']

# For now, because the password reset template in Django 1.2 is dumb and doesn't take a from_email
DEFAULT_FROM_EMAIL = "passwordreset@example.com"
UPDATES_EMAIL = "Canvas <updates@example.com>"

EMAIL_CONFIRMATION_DAYS = 14

SHORT_CODES = ['party', 'galileu', 'exame', 'epoca', 'elpais', 'ontd', 'andrewwk', 'buzzfeed', 'nico', 'usertest', 'youpix']
SHORT_CODE_AUTOFOLLOW = {'andrewwk': 'partyhard', 'buzzfeed': 'buzzfeed'}
SHORT_CODE_COPY = {
    'nico': """ニコ生から来た皆様へ<br/><br/>Example.comへようこそ！<br/>今回のニコニコ生放送をご覧頂き、ありがとうございました。<br/> もしご興味があれば、登録してExample.comを自由に使ってください！""",
    'andrewwk': """<h1>Andrew W.K. on Canvas</h1><hr><p>Once you sign up, you'll be following Andrew W.K's #partyhard group on Canvas.</p><p>The King of Partying himself will be joining us LIVE on August 10th at 4PM EST to remix images and collaborate with users in #partyhard, so mark your calendars!</p>""",
}
CLOSED_SHORT_CODES = ['redditors_only']

HIDDEN_GROUPS = ['profiles', 'monstermash', 'monstermashmobile']

# List of short ids for Comment(s) that show the Canvas Team.
if PRODUCTION:
    ABOUT_PAGE_COMMENTS = ['rqz', 'j7yo', 'j6b0', 'cea7p', 'k096h']
else:
    ABOUT_PAGE_COMMENTS = ['vu7', 'wn1', 's9j']

# Migrates existing users over from sha1 to bcrypt.
BCRYPT_MIGRATE = True
BCRYPT_ENABLED_UNDER_TEST = False
BCRYPT_ROUNDS = 11 # Means 2^N rounds, takes roughly .2s when N=11

logging.basicConfig(
    level=(logging.DEBUG if PRODUCTION else logging.DEBUG),
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join(PROJECT_PATH, "run/gunicorn.log"),
    filemode='a',
)

DKIM_SELECTOR = "amazonses"
DKIM_DOMAIN = "example.com"
DKIM_PRIVATE_KEY_PATH = "/etc/canvas/dkim.private.key"
DKIM_PRIVATE_KEY = open(DKIM_PRIVATE_KEY_PATH).read() if os.path.exists(DKIM_PRIVATE_KEY_PATH) else None

MEMOIZE_RAW_HTML = not DEBUG

import logging
logging.getLogger('boto').setLevel(logging.CRITICAL)

CANVAS_ACCOUNT_USERNAME = 'Canvas'

INCLUDE_ERROR_TYPE_IN_API = False

ACTIVITY_TYPE_CLASSES = (
    'apps.activity.redis_models.StickerActivity',
    'apps.activity.redis_models.LevelUpActivity',
    'apps.activity.redis_models.EpicStickerActivity',
    'apps.activity.redis_models.DailyFreeStickersActivity',
    'apps.activity.redis_models.RemixActivity',
    'apps.activity.redis_models.ThreadReplyActivity',
    'apps.activity.redis_models.ReplyActivity',
    'apps.activity.redis_models.RemixInviteActivity',
    'apps.activity.redis_models.MonsterRemixInviteActivity',
    'apps.activity.redis_models.FollowedByUserActivity',
    'apps.activity.redis_models.PostPromotedActivity',
    'apps.activity.redis_models.ThreadPromotedActivity',
)

EMAIL_CHANNEL_ACTIONS = {
    'recipient': ['remixed', 'replied', 'thread_replied'],
    'actor': ['newsletter', 'digest'],
}

# Behavioral options.
FEED_ENABLED = True
ALLOW_HIDING_OWN_COMMENTS = False
AUTO_MODERATE_FLAGGED_COMMENTS_THRESHOLD = None

API_CSRF_EXEMPT = False

#TODO replace with something for realtime instead
HTML_APIS_ENABLED = True

