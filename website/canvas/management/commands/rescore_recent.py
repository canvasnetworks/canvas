from time import time
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from canvas.models import Content, Comment, Category

class Command(BaseCommand):
    args = ''
    help = 'Update comment scores for the front pages.'

    def handle(self, *args, **options):
        start = time()


        comments = list(Comment.all_objects.filter(timestamp__gte=start - 24 * 60 * 60))
        
        print "Rescoring", len(comments), "comments"
        
        for comment in comments:
            comment.update_score()
            for child_comment in Comment.all_objects.in_bulk_list(comment.popular_replies[0:3]):
                child_comment.update_score()
        
        print "Scores updated. Total elapsed time: %0.2fs" % (time() - start)
