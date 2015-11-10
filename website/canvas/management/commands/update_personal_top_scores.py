from time import time
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from canvas.models import Comment, CommentSticker, Visibility
from canvas import stickers

class Command(BaseCommand):
    args = ''
    help = 'Update comment scores for the front pages.'

    def handle(self, start, *args, **options):
        start = int(start)
        comments = Comment.objects.filter(id__gte=start).exclude(author=None)
        print "Remaining", len(comments)
        for comment in comments:
            if comment.id % 100 == 0:
                print "Updating", comment.id
                
            details = comment.details()

            sticker_scores = [stickers.details_for(k).value * v for k, v in details['sticker_counts'].items()]
            top_score = sum(sticker_scores)

            visibility = details.get('visibility')
            if visibility in Visibility.invisible_choices:
                top_score = -1

            # Some old comments have no author
            personal_top = (comment.author.redis.top_anonymous_posts if comment.anonymous else comment.author.redis.top_posts)
            personal_top.bump(comment.id, top_score)
