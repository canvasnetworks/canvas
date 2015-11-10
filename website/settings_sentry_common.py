import os, sys

from settings_common import *

if PRODUCTION:
    SENTRY_WEB_HOST = 'ip-10-112-58-112.ec2.internal'
else:
    SENTRY_WEB_HOST = 'localhost'

SENTRY_WEB_PORT = 9005

SENTRY_REMOTE_URL = 'http://{0}:{1}/store/'.format(SENTRY_WEB_HOST, SENTRY_WEB_PORT)

SENTRY_KEY = "REDACTED"

SENTRY_MAX_LENGTH_STRING = 4000

