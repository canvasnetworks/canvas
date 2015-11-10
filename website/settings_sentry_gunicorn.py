# http://gunicorn.org/configure.html
import os
import random

cpu_count = lambda: os.sysconf('SC_NPROCESSORS_ONLN')

logfile = "run/sentry.gunicorn.log"
loglevel = "debug"

bind = '0.0.0.0:9005'

timeout = 90

PRODUCTION = bool(os.path.exists('/etc/canvas'))
PRODUCTION_DEBUG = bool(os.path.exists('/etc/canvas/debug'))

debug = not PRODUCTION or PRODUCTION_DEBUG

daemon = not debug

workers = cpu_count() * 4 + 1 if PRODUCTION else 3


