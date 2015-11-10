from configuration import aws
from django.core.management.base import BaseCommand
from canvas.shortcuts import r2r_jinja
from canvas.details_models import ContentDetails
from apps.canvas_auth.models import User
from canvas.redis_models import redis
import tarfile
from django.conf import settings
import os
from canvas.upload import SimpleStorageServiceFS
from canvas import util
import tempfile
from boto.exception import S3ResponseError
import zipfile
import time
import StringIO
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from apps.canvas_auth.models import User

class S3(object):
    def __init__(self, bucket, prefix=""):
        conn = S3Connection(*aws)
        self.bucket = conn.get_bucket(bucket)
        self.prefix = prefix
    def read(self, filename):
        key = Key(self.bucket)
        key.key = self.prefix + filename
        return key.get_contents_as_string()
    def read_to_fp(self, filename, fp):
        key = Key(self.bucket)
        key.key = self.prefix + filename
        return key.get_contents_to_file(fp)
    def copy_to_other_s3(self, filename, other_s3, to_filename):
        key = Key(self.bucket)
        key.key = self.prefix + filename
        key.copy(other_s3.bucket, to_filename)
    def save(self, filename, filedata, content_type='application/zip'):
        _, ext = os.path.splitext(filename)
        key = Key(self.bucket)
        key.key = self.prefix + filename
        key.set_contents_from_string(filedata, headers={'Content-Type': content_type})

from_fs = S3('canvas_public_ugc')
to_fs = S3('canvas-export')


#id_start = 15262
#id_end = 45000
id_start = 35218#85000
id_end = 45000
#for user2 in User.objects.filter(id__gte=id_start).exclude(id__gt=id_end).order_by('id').iterator():
for user2 in User.objects.filter(id__in=list(Comment.objects.order_by('-id').values_list('author_id', flat=True).distinct()[:50])).iterator():
    #user = User.objects.get(username='photocopier')
    print "id: %s username: %r email: %r" % (user2.id, user2.username, user2.email)
    ids = Comment.all_objects.filter(author=user2).exclude(reply_content__isnull=True).values_list('reply_content_id', flat=True)
    num_ids = len(ids)
    last = time.time()
    n = 0
    total = 0
    image_urls = []
    all_last = time.time()
    to_dir = '{}-{}/'.format(user2.id, user2.username)
    for id_ in ids:#[2:3]:
        details_id = ('content:' + id_ + ':details').encode('ascii')
        raw = redis.get(details_id)
        if not raw:
            continue
        details = util.loads(raw)
        try:
            filename = details['original']['name']
        except KeyError:
            print "KeyError: ",
            print details
            continue
        to_filename = to_dir + filename.lstrip('original/')
        try:
            from_fs.copy_to_other_s3(filename, to_fs, to_filename)
        except S3ResponseError:
            continue
        image_urls.append('http://canvas-export.s3-website-us-east-1.amazonaws.com/' + to_filename)
        total += time.time() - last
        n += 1.
        ##print total / n
        #print (num_ids - n),
        last = time.time()
    index_html = r2r_jinja('exporter_index.html', {'user': user2, 'image_urls': image_urls})
    index_html = index_html.content
    to_fs.save(to_dir + 'index.html', index_html, content_type='text/html')
    print "finished {} images for user {} in {}s".format(num_ids, user2.username, time.time() - all_last)

