import os
import urlparse

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.exception import BotoServerError
from compressor.signals import post_compress
from django.dispatch import Signal
from django.conf import settings

from canvas.redis_models import RedisHash
from canvas.util import flatten, gzip_string
from configuration import aws, Config

visibility_changed = Signal(providing_args=['instance'])

def upload_compressed_files_to_s3(sender, type, mode, context, **kwargs):
    if mode != "file":
        return

    if not settings.COMPRESS_OFFLINE:
        return

    url = context['url']

    path = urlparse.urlparse(url).path

    source_name = "/var/canvas/website/" + path
    destination_name = path

    with file(source_name, 'rb') as handle:
        raw_filedata = handle.read()

    filedata = gzip_string(raw_filedata)

    content_types = {
        'css': 'text/css',
        'js': 'text/javascript',
    }

    content_type = content_types[type]

    headers = {
        "Cache-Control": "max-age=315360000, public",
        "Expires": "Thu, 31 Dec 2037 23:55:55 GMT",
        "Content-Encoding": "gzip",
        'Content-Type': content_type,
    }

    conn = S3Connection(*aws)
    bucket = conn.get_bucket(Config['compress_bucket'])

    key = Key(bucket)
    key.key = destination_name
    try:
        if key.exists():
            print "Skipping", destination_name, " already exists."
        else:
            print "Uploading %s (%s kb)" % (destination_name, len(filedata) // 1024)
            key.set_contents_from_string(filedata, headers=headers)
    except BotoServerError, bse:
        print bse

post_compress.connect(upload_compressed_files_to_s3)

