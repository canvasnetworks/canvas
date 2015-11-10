#from django.core.management.base import BaseCommand

#from canvas.details_models import ContentDetails
#from apps.canvas_auth.models import User
#from canvas.redis_models import redis
#from django.conf import settings
#from canvas import util

#class Command(BaseCommand):
#    args = ''
#    help = """Schedules sending email newsletters to all users."""
#    def handle(self, id_start=0, id_end=1000000000000, *args, **options):
#        id_start, id_end = int(id_start), int(id_end)
#        from_fs = SimpleStorageServiceFS('canvas_public_ugc')
#        to_fs = SimpleStorageServiceFS('canvas-export')
#        for user in User.objects.filter(id__gte=id_start).exclude(id__gt=id_end).exclude(email='').order_by('id'):





from configuration import aws
from django.core.management.base import BaseCommand
from canvas.details_models import ContentDetails
from apps.canvas_auth.models import User
from canvas.redis_models import redis
import tarfile
from django.conf import settings
import os
from canvas.upload import SimpleStorageServiceFS
from canvas import util
import tempfile
import zipfile
import time
import StringIO
from boto.s3.connection import S3Connection
from boto.s3.key import Key

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
    def save(self, filename, filedata):
        _, ext = os.path.splitext(filename)
        content_type = 'application/zip'
        key = Key(self.bucket)
        key.key = self.prefix + filename
        key.set_contents_from_string(filedata, headers={'Content-Type': content_type})

from_fs = S3('canvas_public_ugc')
to_fs = S3('canvas-export')
user = User.objects.get(username='ae')
print "id: %s username: %r email: %r" % (user.id, user.username, user.email)

ids = Comment.all_objects.filter(author=user).exclude(reply_content__isnull=True).values_list('reply_content_id', flat=True)
num_ids = len(ids)
last = time.time()
n = 0
total = 0

#with tempfile.SpooledTemporaryFile() as tmp:
#with tempfile.NamedTemporaryFile(delete=True) as tmp:
with open('./foo.tar', 'w') as tmp:
    #with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
    with tarfile.open(fileobj=tmp, mode="w") as tar:
        for id_ in ids:#[2:3]:
            details_id = ('content:' + id_ + ':details').encode('ascii')
            raw = redis.get(details_id)
            details = util.loads(raw)
            filename = details['original']['name']
            fp = StringIO.StringIO()
            #dtmp = tempfile.NamedTemporaryFile(delete=)
            from_fs.read_to_fp(filename, fp)
            #fp.write('testing')
            fp.seek(0)
            if not len(fp.buf):
                print 'ZERO LENGTH FILE!!!!!!! {}'.format(details['original']['name'])
            info = tarfile.TarInfo(name=('canvas_images/' + filename.lstrip('original/')))
            info.size = len(fp.buf)
            tar.addfile(tarinfo=info, fileobj=fp)
            #dtmp.close()
            #archive.write(dtmp.name, 'canvas_images/' + filename.lstrip('original/'))
            #archive.write('./test.jpg', 'canvas_images/' + filename.lstrip('original/'))
            #file_data = from_fs.read_to_fp(filename, fp)
            #file_data = from_fs.read(filename)
            #print file_data[:50]
            #file_data = 'i see'
            #file_data = file_data[:50]
            #archive.writestr(filename.lstrip('original/'), file_data)
            #archive.writestr('canvas_images/' + filename.lstrip('original/'), fp.getvalue())
            #archive.writestr('canvas_images/' + filename.lstrip('original/'), file_data)
            total += time.time() - last
            n += 1.
            ##print total / n
            print (num_ids - n),
            last = time.time()
        ## Reset file pointer
        tmp.seek(0)

with open('./foo.tar', 'r') as tmp:
    to_fs.save('{}-{}.tar'.format(user.id, user.username), tmp.read())
    #print tmp.name
    #with zipfile.ZipFile('./foo.zip', 'r', zipfile.ZIP_DEFLATED) as archive:
    #with zipfile.ZipFile(tmp.name, 'r', zipfile.ZIP_DEFLATED) as archive:
    #    archive.printdir()
    #   ##print tmp

