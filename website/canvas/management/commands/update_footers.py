import math

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from canvas.models import Comment
from realtime.server import get_fs
from realtime.footer import Footer
from django.conf import settings

from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import *


class Command(BaseCommand):
    args = ''
    help = 'Recreates all the thumbnails.'

    def handle(self, *args, **options):
        update_all_footers(get_fs(settings.PRODUCTION), get_fs(settings.PRODUCTION), *args)


def update_all_footers(from_fs, to_fs, resume_percent=0.0, stop_percent=1.0, skip_preexisting=False):
    resume_percent, stop_percent = float(resume_percent), float(stop_percent)

    comments = Comment.objects.all().exclude(Q(reply_content__isnull=True) | Q(reply_content__animated=True)).select_related()

    total = comments.count()
    start_slice = math.floor(resume_percent * total)
    stop_slice = math.ceil(stop_percent * total)

    print "Updating footers %s-%s of %s" % (start_slice, stop_slice, total)

    for i, cmt in enumerate(comments[start_slice:stop_slice]):
        print "%05.2f%% complete. Updating: %s" % ((i + start_slice) * 100.0 / total, cmt.id)

        content = cmt.reply_content.details()

        # Check if it already exists.
        if skip_preexisting and 'footer' in content:
            continue

        if content.get('original'):
            Footer.get_app()
            meta = cmt.footer.update(web=QWebPage())

    print 'All done.'

