# http://gunicorn.org/configure.html
import os
import random
import sys

import gunicorn

sys.path.append('/var/canvas/website')

PRODUCTION = bool(os.path.exists('/etc/canvas'))
PRODUCTION_DEBUG = bool(os.path.exists('/etc/canvas/debug'))

debug = not PRODUCTION or PRODUCTION_DEBUG


# Gunicorn must be HARD restarted to get these changes. SIGHUP will not see them.
# Do NOT import non-system modules here, or they will be imported pre-fork and won't reload on restarts of servers

cpu_count = lambda: os.sysconf('SC_NPROCESSORS_ONLN')

pidfile = 'run/gunicorn.pid'
logfile = 'run/gunicorn.log'
loglevel = 'info'
daemon = True

if PRODUCTION:
    timeout = 9000
else:
    timeout = 600

workers = cpu_count() * 2 + 1 if PRODUCTION else 3

# Gunicorn will break if you try to change worker_class then SIGHUPing. You'll need to hard restart.
worker_class = 'gunicorn_worker.SyncWorker'

STOCHASTIC = False

if gunicorn.version_info[1] > 12:
    def post_request(worker, request, environ):
        _post_request(worker, request, environ)
else:
    def post_request(worker, request):
        _post_request(worker, request)

def _post_request(worker, request, environ={}):
    from canvas import bgwork, util
    from sentry.client.models import client

    try:
        bgwork.perform()
    except Exception, e:
        util.logger.exception('post_request error in bgwork.perform:' + e.message)
        client.create_from_exception()

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)" % worker.pid)
    if STOCHASTIC:    
        from canvas.debug import StackMonitor
        StackMonitor.ensure()

#def when_ready(server):
    
