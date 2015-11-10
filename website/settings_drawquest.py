from settings import *

PROJECT = 'drawquest'

CANVAS_SUB_SITE = '/admin/'

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
    DOMAIN = "dq.savnac.com"
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
#    mysql -h <hostname> -u drawquest -p<press enter><paste pw from below>
# Useful commands:
#    See long-running transactions:
#        SHOW ENGINE INNODB STATUS;
if PRODUCTION:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'drawquest',
            'USER': 'drawquest',
            'PASSWORD': 'E78Sg38TNNmP',
            'HOST': 'drawquestdb.ccop1gmd625s.us-east-1.rds.amazonaws.com',
            'PORT': '3306',
        }
    }
elif TESTING_USE_MYSQL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'drawquest',
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
            'NAME': 'drawquest/db.sqlite',                      # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }

MIDDLEWARE_CLASSES = (
    'drawquest.middleware.PingMiddleware',

    'drawquest.middleware.DrawquestShimMiddleware',

    'canvas.middleware.ExceptionLogger',
    'canvas.middleware.HandleLoadBalancerHeaders',
    'canvas.middleware.DeferredWorkMiddleware',

    #TODO remove
    'drawquest.middleware.Log403',

    'django.middleware.common.CommonMiddleware',
    'canvas.middleware.UploadifyIsALittleBitchMiddleware',

    'drawquest.apps.drawquest_auth.middleware.SessionHeaderMiddleware',
    'canvas.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.canvas_auth.middleware.AnonymousUserMiddleware',

    #TODO 'canvas.middleware.RedirectToHttpsMiddleware',

    'canvas.experiments.ForceExperimentMiddleware',
    'canvas.middleware.FacebookMiddleware',
    'canvas.middleware.ImpersonateMiddleware',

    'canvas.middleware.RequestSetupMiddleware',

    'drawquest.middleware.InactiveUserMiddleware',
    'drawquest.middleware.StaffOnlyMiddleware',
    'canvas.middleware.StaffOnlyMiddleware',
    'canvas.middleware.IPHistoryMiddleware',

    'canvas.middleware.GlobalExperimentMiddleware',
    'canvas.middleware.HttpRedirectExceptionMiddleware',
    'canvas.middleware.Django403Middleware',
    'canvas.middleware.HttpExceptionMiddleware',

    'canvas.middleware.TimeDilationMiddleware',

    'apps.share_tracking.middleware.TrackShareViewsMiddleware',
    'apps.share_tracking.middleware.TrackClickthroughMiddleware',

    #'django.contrib.messages.middleware.MessageMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    'canvas.middleware.ResponseGuard',
)

AUTHENTICATION_BACKENDS = (
    'drawquest.apps.drawquest_auth.backends.DrawquestAuthBackend',
)

TEMPLATE_CONTEXT_PROCESSORS = DJANGO_DEFAULT_CONTEXT_PROCESSORS + (
    'django.core.context_processors.request',
    'canvas.context_processors.base_context',
    'apps.features.context_processors.features_context',
)

ROOT_URLCONF = 'drawquest.urls'

REDIS_HOST = Config['drawquest_redis_host']

# Avoid colliding with example.com redis DBs in testrunner and locally.
if not TESTING:
    REDIS_DB_MAIN = 10
    REDIS_DB_CACHE = 11
    SESSION_REDIS_DB = 12
else:
    REDIS_DB_MAIN = 13
    REDIS_DB_CACHE = 14
    SESSION_REDIS_DB = 15

MEMCACHE_HOSTS = Config['drawquest_memcache_hosts']

if PRODUCTION:
    CACHE_BACKEND = 'memcached://{}'.format(';'.join(Config['drawquest_memcache_hosts']))
else:
    CACHE_BACKEND = 'locmem://?max_entries=1000'

# Bump this to wipe out all caches which use cachecow.
CACHE_KEY_PREFIX = 'DQv6'

FACT_HOST = Config['drawquest_fact_host']
FACT_BUCKET = 'drawquest-facts'

IMAGE_FS = Config['drawquest_image_fs']

HTTPS_ENABLED = True
UGC_HTTPS_ENABLED = False
API_PROTOCOL = 'https' if HTTPS_ENABLED else 'http'
API_PREFIX = API_PROTOCOL + '://example.com/api/'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, 'drawquest', 'templates'),
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
    'apps.features',
    'apps.feed',
    'apps.ip_blocking',
    'apps.jinja_adapter',
    'apps.post_thread',
    'apps.share_tracking',
    'apps.signup',
    'apps.user_settings',
    'apps.threads',

    'drawquest.apps.api_console',
    'drawquest.apps.comment_freeze',
    'drawquest.apps.drawquest_auth',
    'drawquest.apps.following',
    'drawquest.apps.iap',
    'drawquest.apps.palettes',
    'drawquest.apps.playback',
    'drawquest.apps.push_notifications',
    'drawquest.apps.quest_comments',
    'drawquest.apps.quests',
    'drawquest.apps.stars',
    'drawquest.apps.submit_quest',
    'drawquest.apps.timeline',
    'drawquest.apps.tumblr',
    'drawquest.apps.whitelisting',

    'canvas',
    'drawquest',
)

if PRODUCTION:
    INSTALLED_APPS += ('sentry.client',)
else:
    INSTALLED_APPS += ('django_nose',)
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_ARGS = ['--exclude=compressor', '-d']

    INSTALLED_APPS += ('apps.sentry_debug',)
    SENTRY_CLIENT = 'sentry.client.base.DummyClient'

MINIFY_HTML = False

# We're going to stop using django-compressor if we ever launch any public-facing pages in DrawQuest.
COMPRESS_OFFLINE = False

logging.basicConfig(
    level=(logging.DEBUG if PRODUCTION else logging.DEBUG),
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join(PROJECT_PATH, "drawquest/run/gunicorn.log"),
    filemode='a',
)

DKIM_SELECTOR = "amazonses"
DKIM_DOMAIN = "example.com"
DKIM_PRIVATE_KEY_PATH = "/etc/canvas/dkim.private.key"
DKIM_PRIVATE_KEY = open(DKIM_PRIVATE_KEY_PATH).read() if os.path.exists(DKIM_PRIVATE_KEY_PATH) else None

# For now, because the password reset template in Django 1.2 is dumb and doesn't take a from_email
DEFAULT_FROM_EMAIL = "passwordreset@example.com"
UPDATES_EMAIL = "DrawQuest <updates@example.com>"

INCLUDE_ERROR_TYPE_IN_API = True

STAR_STICKER_TYPE_ID = 9001

ACTIVITY_TYPE_CLASSES = (
    'apps.activity.redis_models.FollowedByUserActivity',
    'drawquest.activities.StarredActivity',
    'drawquest.activities.PlaybackActivity',
    'drawquest.activities.FolloweePostedActivity',
    'drawquest.activities.WelcomeActivity',
)

# Behavioral options.
FEED_ENABLED = False
ALLOW_HIDING_OWN_COMMENTS = False
AUTO_MODERATE_FLAGGED_COMMENTS_THRESHOLD = 3

IAP_VERIFICATION_URL = 'https://buy.itunes.apple.com/verifyReceipt'
IAP_VERIFICATION_SANDBOX_URL = 'https://sandbox.itunes.apple.com/verifyReceipt'

TUMBLR_OAUTH_CONSUMER_KEY = "REDACTED"
TUMBLR_SECRET_KEY = "REDACTED"

API_CSRF_EXEMPT = True

EMAIL_CHANNEL_ACTIONS = {
    'recipient': ['starred'],
    'actor': [],
}

#TODO replace with something for realtime instead
HTML_APIS_ENABLED = False

QUEST_IDEAS_USERNAME = 'QuestIdeas'

