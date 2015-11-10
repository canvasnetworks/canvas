import sys; sys.path.append('/var/canvas/common')

import logging
import os
import signal

from django.conf import settings
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.web.resource import Resource, IResource
from twisted.web.server import Site
from twisted.web.static import File
from twisted.web.util import Redirect
from twisted.application import internet, service
from twisted.python import log, logfile
from twisted.manhole.telnet import ShellFactory
from zope.interface import implements

from configuration import Config


class CanvasManholeFactory(ShellFactory):
    username = "canvas"
    password = "yumnuts"


class CanvasTCPServer(internet.TCPServer):
    sighup_death_timer = 20 * 60
    
    def __init__(self):
        port = 0 # Let the OS assign us a free port
        internet.TCPServer.__init__(self, port, get_site(production=settings.PRODUCTION))
    
    def startService(self):
        internet.TCPServer.startService(self)
        self.update_nginx()
        signal.signal(signal.SIGUSR1, lambda signum, frame: reactor.callFromThread(self.on_SIGUSR1))
        port = reactor.listenTCP(0, CanvasManholeFactory())
        file('manhole.port', 'w').write(str(port.getHost().port))
        
    def on_SIGUSR1(self):
        log.msg('SIGHUP received, stopping the reactor in %s seconds.' % self.sighup_death_timer, logLevel=logging.CRITICAL)
        reactor.callLater(self.sighup_death_timer, self.stop_reactor)
        
    def stop_reactor(self):
        log.msg("Stopping reactor after SIGHUP death timer (signal received %s seconds ago)." % self.sighup_death_timer, logLevel=logging.CRITICAL)
        reactor.stop()
        
    def update_nginx(self):
        port = self._port.getHost().port
        file('./run/twisted.port', 'w').write(str(port))


def CanvasApp(nginx=False):
    application = service.Application("Canvas")

    web_server = CanvasTCPServer()
    web_server.setServiceParent(application)
    
    
    log_file = logfile.LogFile(
        name="twistd.log", 
        directory="/var/canvas/website/run",
        maxRotatedFiles=100,
    )
    
    application.setComponent(log.ILogObserver, log.FileLogObserver(log_file).emit)

    return application


def setup_django_env():
    """ I must be called before any Django code is imported. """
    import sys, os
    for path in ['../', '../website']:
        if path not in sys.path:
            sys.path.append(path)

@inlineCallbacks
def construct(root, services):
    print "LOADING: Connecting to external services."
    yield services.connect()

def monkey_patch_twisted_because_it_suuuuuuuuuuuuuucks():
    old_render_GET = File.render_GET
    
    def render_GET(self, request):
        result = old_render_GET(self, request)
        if result == '' and self.type:
            request.setHeader('content-type', self.type)
        return result
        
    File.render_GET = render_GET
    
def get_s3_fs(bucket=Config['image_bucket'], **kwargs):
    from realtime.resources import AmazonS3FS
    from txaws.credentials import AWSCredentials
    # Handle unicode credential values as txAWS cannot.
    creds = dict([(k,v.encode('ascii')) for k,v in Config['aws'].items()])
    return AmazonS3FS(bucket, AWSCredentials(**creds), **kwargs)
    
def get_local_fs():
    from realtime.resources import LocalDiskFS
    return LocalDiskFS('./ugc', content_type='application/javascript')
    
def get_fs(production):
    return get_s3_fs() if production else get_local_fs()
    
def get_script_fs(production):
    from realtime.resources import LocalDiskFS
    return get_s3_fs(Config['script_bucket'], content_type='application/javascript') if production else LocalDiskFS('./ugc/local_script_drop', content_type='application/javascript') # Always use s3 even not in prod; relies on s3 serving up files


class QuietSite(Site):
    def log(self, request):
        pass


def get_site(production):
    setup_django_env()
    
    monkey_patch_twisted_because_it_suuuuuuuuuuuuuucks()
    
    from realtime.resources import RealtimeResource, ScriptDrop, Status, Stats
    from realtime.channels import Services
    
    services = Services()
    root = Resource()
    reactor.callLater(0, construct, root, services)
    
    root.putChild('script_drop', ScriptDrop(get_script_fs(production)))
    root.putChild('rt', RealtimeResource(services))
    root.putChild('rt_stats', Stats(services))
    root.putChild('twisted_ping', Status())

    return QuietSite(root)

