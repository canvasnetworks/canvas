# http://gunicorn.org/configure.html

import sys

sys.path.append('/var/canvas/website')

from settings_gunicorn import *

pidfile = 'drawquest/run/gunicorn.pid'
logfile = 'drawquest/run/gunicorn.log'

port = 8001
bind = '127.0.0.1:{}'.format(port)

