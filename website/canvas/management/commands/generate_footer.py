import datetime
import os
from tempfile import TemporaryFile
import webbrowser

from django.core.files.temp import gettempdir
from django.core.management.base import BaseCommand, CommandError

from canvas.models import Comment
from django.conf import settings


class Command(BaseCommand):
    args = 'filename'
    help = ''

    def handle(self, *args, **options):
        comment_id = args[0]
        cmt = Comment.objects.get(id=comment_id)
        cmt.footer.update()
        print 'http://' + settings.DOMAIN + cmt.footer.get_absolute_url()

