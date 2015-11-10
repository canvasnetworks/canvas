from base64 import b64decode
import httplib
import os
import urllib2
import uuid

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from django.conf.urls.defaults import url, patterns
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from canvas import util
from canvas.redis_models import redis
from canvas.api_decorators import json_response, api_decorator
from canvas.exceptions import ServiceError
from canvas.thumbnailer import create_content
from configuration import aws, Config


class LocalDiskFS(object):
    def __init__(self, root):
        self.root = root

    def save(self, filename, filedata):
        filepath = os.path.join(self.root, filename)
        output = file(filepath, 'wb')
        try:
            output.write(filedata)
        finally:
            output.close()

        os.chmod(filepath, 0644) # Intentionally octal, world readable for nginx

    def read(self, filename):
        filepath = os.path.join(self.root, filename)
        return file(filepath, 'rb').read()


class SimpleStorageServiceFS(object):
    def __init__(self, bucket, prefix=""):
        conn = S3Connection(*aws)
        self.bucket = conn.get_bucket(bucket)
        self.prefix = prefix

    def read(self, filename):
        key = Key(self.bucket)
        key.key = self.prefix + filename
        return key.get_contents_as_string()

    def save(self, filename, filedata):
        _, ext = os.path.splitext(filename)
        content_type = ({
            '.gif': 'image/gif',
            '.png': 'image/png',
        }).get(ext.lower(), 'image/jpeg')

        key = Key(self.bucket)
        key.key = self.prefix + filename
        key.set_contents_from_string(filedata, headers={'Content-Type': content_type})


def get_fs(fs_type, *args):
    fs_lookup = {
        'local': LocalDiskFS,
        's3': SimpleStorageServiceFS,
    }
    return fs_lookup[fs_type](*args)

def _got_imagedata(filedata, request, url=''):
    remix_of = request.GET.get('remix_of')
    stamps_used = request.GET.getlist('used_stamps')
    text_used = request.GET.get('used_text', '')
    is_quest = str(request.GET.get('is_quest', 0)) == '1'

    fs = get_fs(*settings.IMAGE_FS)

    try:
        return create_content(request.META['REMOTE_ADDR'], fs, filedata, remix_of, stamps_used, text_used, url, is_quest=is_quest)
    except IOError, e:
        raise ServiceError("Unable to read image.")

def upload_from_url(request, url):
    return _got_imagedata(_fetch_url(url), request, url=url)

def _fetch_url(url):
    if not url.startswith('http://') and not url.startswith('https://'):
        if '://' not in url:
            url = 'http://' + url
        else:
            # Must at least prevent file://, better to whitelist than blacklist
            raise ServiceError("Only http/https links allowed")

    try:
        url_request = urllib2.Request(url)
        url_response = urllib2.urlopen(url_request)
    except (IOError, httplib.HTTPException, UnicodeEncodeError):
        raise ServiceError("Unable to download image.")

    if url_response.getcode() != 200:
        raise ServiceError("The requested image could not be downloaded. Please try a different image.")
    else:
        return url_response.read()

# Not a regular @api because it takes file uploads, but it does return a JSONResponse
@csrf_exempt
@json_response
def api_upload(request):
    content_type = request.META['CONTENT_TYPE']

    url = ''
    filedata = None

    if 'file' in request.FILES:
        filedata = "".join(request.FILES['file'].chunks())

    elif content_type.startswith('application/json'):
        json = util.loads(request.raw_post_data)
        url = json.get('url', '').strip()
        filedata = _fetch_url(url)

    elif content_type.startswith('application/base64-png'):
        token = 'data:image/png;base64,'
        header, data = request.raw_post_data.split(',', 2)
        if not header.startswith('data:') or not 'image/png' in header or not 'base64' in header:
            return {'success': False, 'code': 'unknown', 'reason': 'Missing data url header.'}
        else:
            filedata = b64decode(data)

    if filedata:
        return _got_imagedata(filedata, request, url=url)
    else:
        raise ServiceError("No file or url.")

chunk_uploads = patterns('canvas.upload')

api = api_decorator(chunk_uploads)

@api('upload')
def upload_chunk(request, data):
    chunk_name = str(uuid.uuid4())

    redis.setex("chunk:{0}".format(chunk_name), data, 60 * 60)

    return {
        'chunk_name': chunk_name,
    }

@api('combine')
def combine_upload_chunks(request, chunks, metadata, is_quest=False):
    keys = ['chunk:{0}'.format(chunk) for chunk in chunks]

    raw_values = redis.mget(keys)

    if not all(raw_values):
        raise ServiceError("Missing uploaded chunk, please retry.")

    values = [b64decode(val) for val in raw_values]
    filedata = "".join(values)

    fs = get_fs(*settings.IMAGE_FS)
    remix_of = metadata.get('remix_of')
    stamps_used = metadata.get('used_stamps', []) or []
    text_used = metadata.get('used_text', '') or ''

    redis.delete(*keys)

    try:
        return create_content(request.META['REMOTE_ADDR'], fs, filedata, remix_of, stamps_used, text_used, '',
                              is_quest=is_quest)
    except IOError, e:
        raise ServiceError("Unable to read image.")

