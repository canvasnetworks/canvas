from django.core.management.base import BaseCommand, CommandError
from canvas.thumbnailer import update_all_content
from canvas.models import Content
from realtime.server import get_local_fs, get_s3_fs

class Command(BaseCommand):
    args = ''
    help = 'Moves all images to from the local filesystem to s3'

    def handle(self, *args, **options):
        update_all_content(get_local_fs(), get_s3_fs())
