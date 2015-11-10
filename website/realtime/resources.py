from base64 import b64decode
from cgi import FieldStorage, parse_header
from hashlib import sha1
import os
import string

from twisted.internet import reactor, threads
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue, succeed, DeferredList, FirstError
from twisted.internet.protocol import Protocol
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.error import NoResource
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from twisted.web.static import File
from txaws.s3.client import S3Client
from txaws.s3.exception import S3Error

from realtime.channels import Channel
from canvas.redis_models import RealtimeChannel
from canvas import util
from configuration import Config


class ProdSwitchJS(Resource):
    def __init__(self, prod):
        Resource.__init__(self)
        self.prod = prod

    def render_GET(self, request):
        request.setHeader("content-type", "text/javascript")
        return "var PRODUCTION = " + ("true" if self.prod else "false") + ";"


class Status(Resource):
    def render_GET(self, request):
        request.setHeader("content-type", "text/html")
        return "twisted pong"


class Stats(Resource):
    def __init__(self, services):
        self.services = services

    def render_GET(self, request):
        request.setHeader("content-type", "text/plain")
        response = ""

        channels = [channel._participants for channel in self.services.channels.objects.values()]
        response +=  "Channels: %s\n" % len(channels)
        xhrs = len(reduce(lambda a,b: a.union(b), channels, set()))
        response += "XHR Listeners: %s\n" % xhrs

        return response


def return_json(request, response):
    request.setHeader('Content-type', 'application/json')
    return util.dumps(response)

def respond_json(request, response):
    request.write(return_json(request, response))
    request.finish()


class RealtimeXhrListener(object):
    def __init__(self, request):
        self.request = request
        self.channels = set()
        # ELB 503s a request after 60s
        self.call = reactor.callLater(30, self.timeout)
        self.request.notifyFinish().addBoth(self.cancelTimeout)
        self.finished = False

    def cancelTimeout(self, reason):
        self.finished = True
        if self.call.active():
            self.call.cancel()

        self.leave_channels()

    def leave_channels(self):
        for channel in list(self.channels):
            channel.leave(self)

    def timeout(self):
        # Send down an empty list of messages, so the client knows there was no error and can retry without backoff.
        self.send({})

    def send(self, messages):
        if self.finished or self.request.finished:
            return False

        messages.update({'success': True})

        request_finish_json(self.request, messages)

        self.leave_channels()

        return True

def request_jsonp(request, data):
    response = util.dumps(data)

    # Handle JSONP requests.
    callbacks = request.args.get('callback')
    if callbacks:
        callback = callbacks[0]
        # If the callback isn't alphanumeric, we could be executing arbitrary script on the client.
        if not callback.replace('_', '').isalnum():
            request.setResponseCode(500)
            response = 'JSONP callbacks must be alpha-numeric.'
        else:
            response = "%s(%s);" % (callback, response)
    return response

def request_finish_json(request, data):
    response = request_jsonp(request, data)
    request.setHeader('Content-type', 'text/javascript')
    request.write(response)
    request.finish()

def jsonp_error(request, message):
    return request_jsonp(request, {'success': False, 'reason': message})

@inlineCallbacks
def wait_all(deferreds):
    try:
        returnValue((yield DeferredList(deferreds, fireOnOneCallback=False, fireOnOneErrback=True, consumeErrors=True)))
    except FirstError, exc:
        raise exc.subFailure.value


class RealtimeResource(Resource):
    def __init__(self, services):
        self.svc = services

    def render_GET(self, request):
        channel_ids = request.args.get('c', [])
        msg_ids = request.args.get('m', [])

        if not channel_ids or not msg_ids:
            return jsonp_error(request, 'Need at least 1 channel and message id pair.')

        try:
            msg_ids = [int(m) for m in msg_ids]
        except ValueError:
            return jsonp_error(request, "Invalid message id.")

        @inlineCallbacks
        def realtime():
            try:
                channels = [self.svc.channels.get(RealtimeChannel(channel_id)) for channel_id in channel_ids]
                backlogs = yield wait_all([channel.backlog(msg_id) for channel, msg_id in zip(channels, msg_ids)])
            except Channel.DisconnectedError:
                request_finish_json(request, {'success': False, 'reason': "Disconnected from Redis"})
            else:
                backlog = {}
                for _, channel_backlog in backlogs:
                    backlog.update(channel_backlog)

                xhr = RealtimeXhrListener(request)

                if backlog:
                    xhr.send(backlog)
                else:
                    for channel in channels:
                        channel.join(xhr)

        realtime()
        return NOT_DONE_YET


class AbstractFS(object):
    def install_renderer(self, render):
        self.resource_render = render

    def resource_render(self, request, path, filedata):
        # Potentially overriden in __init__
        request.setHeader('Expires', 'Expires: Thu, 31 Dec 2020 16:00:00 GMT')
        _, ext = os.path.splitext(path)
        content_type = ({
            '.gif': 'image/gif',
            '.png': 'image/png'
        }).get(ext.lower(), 'image/jpeg')

        request.setHeader('Content-type', content_type)
        request.write(filedata)

    def operation(self):
        return self.__class__.Operation(self)

class LocalDiskFS(AbstractFS):
    def __init__(self, root, content_type=None):
        self.root = root
        self.content_type = content_type
        self.resource_render = None

    def resource(self):
        if self.resource_render:
            return self.__class__.CustomRenderResource(self, self.root)
        else:
            return File(self.root, defaultType = self.content_type if self.content_type else 'text/html')

    def read(self, path):
        return succeed(file(os.path.join(self.root, path), 'rb').read())

    class CustomRenderResource(Resource):
        def __init__(self, ldfs, root, path=""):
            Resource.__init__(self)
            self.ldfs = ldfs
            self.root = root
            self.path = path

        def getChild(self, path, request):
            return self.__class__(self.ldfs, self.root, self.path + "/" + path)

        def render(self, request):
            filedata = file(os.path.join(self.root, "." + self.path), 'rb').read()
            self.ldfs.resource_render(request, self.path, filedata)
            request.finish() # Confusing
            return NOT_DONE_YET

    class Operation(object):
        def __init__(self, fs):
            self.fs = fs

        def wait(self):
            return succeed(None)

        def save(self, filename, filedata):
            filepath = os.path.join(self.fs.root, filename)
            output = file(filepath, 'wb')
            try:
                output.write(filedata)
            finally:
                output.close()

            os.chmod(filepath, 0644) # Intentionally octal, world readable for nginx

class AmazonS3FS(AbstractFS):
    allowable_chars = string.digits + string.letters + "./"

    def __init__(self, bucket, creds=None, content_type=None):
        self.bucket = bucket
        self.client = S3Client(creds=creds)
        self.content_type = content_type

    def resource(self):
        return self.__class__.BucketResource(self, self.bucket)

    def isPathAllowed(self, path):
        return all(char in self.allowable_chars for char in path)

    def read(self, path):
        return self.client.get_object(self.bucket, path.lstrip('/'))

    class BucketResource(Resource):
        def __init__(self, s3, bucket, path=""):
            Resource.__init__(self)
            self.s3 = s3
            self.bucket = bucket
            self.path = path

        def getChild(self, path, request):
            return self.__class__(self.s3, self.bucket, self.path + "/" + path)

        def render(self, request):
            if not self.s3.isPathAllowed(self.path):
                request.setResponseCode(404)
                return "Disallowed characters in path"

            @inlineCallbacks
            def fetch_and_return():
                try:
                    filedata = yield self.s3.read(self.path)
                    self.s3.resource_render(request, self.path, filedata)
                except S3Error, s3e:
                    if s3e.get_error_code() == 'NoSuchKey':
                        request.setResponseCode(404)
                        request.write('File not found')
                    else:
                        request.setResponseCode(500)
                        request.write('S3 Error:' + s3e.get_error_code())
                except:
                    import traceback
                    traceback.print_exc()
                    request.setResponseCode(500)
                    request.write('Unknown Failure')
                finally:
                    request.finish()

            fetch_and_return()

            return NOT_DONE_YET

    class Operation(object):
        def __init__(self, s3):
            self.s3 = s3
            self.ops = []

        def wait(self):
            ops = self.ops
            self.ops = []

            return DeferredList(ops, fireOnOneCallback=False, fireOnOneErrback=True, consumeErrors=True)

        def save(self, filepath, filedata):
            if not self.s3.isPathAllowed(filepath):
                raise Exception("Disallowed characters in path")
            self.ops.append(self.s3.client.put_object(self.s3.bucket, filepath, filedata, content_type=self.s3.content_type))

class ScriptDrop(Resource):
    def __init__(self, fs):
        Resource.__init__(self)
        self.fs = fs
        self.fs.install_renderer(self.resource_render)

    def resource_render(self, request, path, filedata):
        log.msg("ScriptDrop resource_render %r" % (path,))
        request.setHeader('Expires', 'Expires: Thu, 31 Dec 2020 16:00:00 GMT')
        _, ext = os.path.splitext(path)
        request.setHeader('Content-type', 'application/javascript')
        request.write(util.dumps({'source': filedata}))

    def getChild(self, path, request):
        return self.fs.resource().getChild(path, request)

    def render_POST(self, request):
        key, pdic = parse_header(request.getHeader('content-type'))

        if not key == 'application/json':
            return return_json(request, {'success': False, 'message': 'Invalid Content-type.'})

        jsargs = util.loads(request.content.read())

        source = jsargs.get('source', "").encode('ascii')
        name = sha1(source).hexdigest()

        @inlineCallbacks
        def upload_js():
            try:
                op = self.fs.operation()
                op.save(name, source)
                yield op.wait()
                respond_json(request, {'success': True, 'name': name, 'url': Config['script_base_url'] + name})
            except Exception, e:
                log.err()
                respond_json(request, {'success': False, 'code': 'unknown', 'reason': repr(e)})

        upload_js()

        return NOT_DONE_YET
