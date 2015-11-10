# -*- coding: utf-8 -*-
# Common Django settings for Canvas.

import os, sys

def add_to_python_path(path):
    if path not in sys.path:
        sys.path.append(path)

add_to_python_path('/var/canvas/common')
from configuration import Config, TESTING, PRODUCTION, LOCAL_SANDBOX, TESTING_BOX

PROJECT_PATH = os.path.abspath(os.path.split(__file__)[0])
TESTING_USE_MYSQL = TESTING_BOX # When devs are on MySQL we can remove this and just use TESTING.
DEBUG = (not PRODUCTION) or bool(os.path.exists('/etc/canvas/debug'))
TEMPLATE_DEBUG = DEBUG
PROFILE = DEBUG
# Don't run through all migrations for testing, simply syncdb.
SOUTH_TESTS_MIGRATE = False


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

