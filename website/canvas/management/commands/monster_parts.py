
from datetime import datetime
import os

from django.core.files.temp import gettempdir
from django.core.management.base import BaseCommand, CommandError

from canvas.models import Comment
from apps.monster.models import MONSTER_GROUP
from django.conf import settings


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        print ""
        for cmt in Comment.objects.filter(category__name=MONSTER_GROUP):
            top = cmt.id
            bottom = None
            if cmt.parent_comment is not None:
                top = cmt.parent_comment.id
                bottom = cmt.id
            print "{0},{1},{2},{3},{4}".format(top, bottom, cmt.author.username, cmt.get_absolute_url(), datetime.fromtimestamp(cmt.timestamp))
