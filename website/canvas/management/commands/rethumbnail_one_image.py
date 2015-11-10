from django.core.management.base import BaseCommand, CommandError
from canvas.thumbnailer import update
from canvas.models import Content
from canvas.upload import get_fs
from configuration import Config
from django.conf import settings

class Command(BaseCommand):
    args = ''
    help = 'Recreates all the thumbnails.'

    def handle(self, cid, *args, **options):
        update(get_fs(*settings.IMAGE_FS), Content.all_objects.get(id=cid), None)

