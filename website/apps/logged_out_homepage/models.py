from django.db.models import ForeignKey, IntegerField
from django.shortcuts import get_object_or_404, Http404

from apps.canvas_auth.models import User, AnonymousUser
from canvas import browse
from canvas.cache_patterns import CachedCall
from canvas.models import BaseCanvasModel, Comment, Content, get_mapping_id_from_short_id
from canvas.util import UnixTimestampField, Now
from canvas.view_helpers import CommentViewData
from canvas.templatetags.jinja_tags import render_jinja_to_string
from django.conf import settings


class ThreadPreview(object):
    def __init__(self, op, main_post, *more_posts):
        self.op = op
        self.main_post = main_post
        self.more_posts = more_posts
        self.curator = ""
        self.timestamp = None
        self.sort = None

    @classmethod
    def get_by_short_id(cls, short_id):
        try:
            mapping_id = get_mapping_id_from_short_id(short_id)
        except ValueError:
            raise Http404
        comment = get_object_or_404(Comment.published, id=mapping_id)
        return cls.get_from_comment(comment)

    @classmethod
    def get_from_comment(cls, comment):
        candidates = Comment.public.in_bulk_list([comment.id] + comment.top_replies[:10])
        candidates = [post for post in candidates if post.reply_content]
        candidates = sorted(candidates, key=lambda comment: -comment.get_score()[0])
        thread = [comment] + candidates[:5]

        (posts,) = CachedCall.many_multicall([post.details for post in thread])

        return cls(*posts)

    @classmethod
    def get_from_spotlighted_thread(cls, spotlighted):
        preview = cls.get_from_comment(spotlighted.comment)
        preview.curator = spotlighted.curator.username
        preview.timestamp = spotlighted.timestamp
        preview.sort = spotlighted.sort
        return preview


class SpotlightedThread(BaseCanvasModel):
    comment = ForeignKey(Comment, null=False, related_name='spotlighted_threads')
    curator = ForeignKey(User, blank=True, null=True, default=None, related_name='spotlighted_threads')
    timestamp = UnixTimestampField(default=0)
    sort = IntegerField()

    class Meta:
        ordering = ['sort']

    @classmethod
    def get_or_create(cls, comment):
        if comment.parent_comment_id:
            comment = comment.parent_comment
        try:
            spotlighted = cls.objects.get(comment=comment.id)
        except cls.DoesNotExist:
            cmt = Comment.objects.get(pk=comment.id)
            spotlighted = cls(comment=cmt)
            spotlighted.sort = 1
            spotlighted.save()
        return spotlighted


def spotlighted_threads():
    return [ThreadPreview.get_from_spotlighted_thread(st) for st in SpotlightedThread.objects.all()]

def suggested_threads():
    spotlighted_ids = SpotlightedThread.objects.all().values_list('comment_id', flat=True)

    nav = browse.Navigation(sort='hot', hot_sort_type='order_by_image_replies')
    ops = list(browse.get_front_comments(AnonymousUser(), nav))
    ops = [op for op in ops if op.id not in spotlighted_ids]
    ops = ops[:300]
    return [ThreadPreview.get_from_comment(op) for op in ops]

def generate_homepage():
    threads = spotlighted_threads()
    ctx = {
        'threads': threads,
        'DOMAIN': settings.DOMAIN,
    }
    return render_jinja_to_string('logged_out_homepage/homepage.html', ctx)

cached_homepage = CachedCall('cached_homepage', generate_homepage, 15 * 60)

