import sys

if sys.platform == 'linux2':
    from twisted.internet import epollreactor
    epollreactor.install()

from twisted.internet.protocol import Factory
from realtime.server import CanvasApp

Factory.noisy = False # Fuck off
application = CanvasApp(nginx=True)
