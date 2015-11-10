from django.core.management.base import BaseCommand

from apps.canvas_auth.models import User
from apps.feed.redis_models import visible_in_feed
from canvas.details_models import CommentDetails


class CleanFeeds(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        for user in User.objects.all():
            post_ids = user.redis.feed_source[:]
            for post_id in post_ids:
                comment_details = CommentDetails.from_id(post_id)
                if not visible_in_feed({'comment': comment_details, 'type': 'post'}):
                    user.redis.feed_source.remove(post_id)

