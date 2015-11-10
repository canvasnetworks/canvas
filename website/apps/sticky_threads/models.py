from django.db.models import ForeignKey, IntegerField, TextField
from django.shortcuts import get_object_or_404, Http404

from apps.canvas_auth.models import User, AnonymousUser
from canvas import util
from canvas.cache_patterns import CachedCall
from canvas.models import BaseCanvasModel, Comment, Content, get_mapping_id_from_short_id
from canvas.redis_models import RedisList
from canvas.templatetags.jinja_tags import render_jinja_to_string
from canvas.util import UnixTimestampField, Now
from canvas.view_helpers import CommentViewData
from django.conf import settings


class ThreadPreview(object):
    def __init__(self, main_post):
        self.main_post = main_post
        self.curator = ""
        self.timestamp = None
        self.sort = None
        self.text = ""

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
        (post,) = CachedCall.multicall([comment.details])
        return cls(comment.details().to_client())

    @classmethod
    def get_from_sticky_thread(cls, sticky):
        preview = cls.get_from_comment(sticky.comment)
        preview.curator = sticky.curator.username if sticky.curator is not None else ''
        preview.timestamp = sticky.timestamp
        preview.sort = sticky.sort
        preview.text = sticky.text
        return preview


STICKY_THREAD_CACHE_KEY = 'homepage:sticky_threads'

def update_sticky_thread_cache():
    threads = RedisList(STICKY_THREAD_CACHE_KEY)
    threads.delete()
    for x in [util.dumps((x.comment.id, x.text)) for x in StickyThread.objects.all()]:
        threads.rpush(x)

def get_sticky_threads_from_cache():
    """ Returns a list of comment ID / sticky text pairs. """
    threads = RedisList(STICKY_THREAD_CACHE_KEY)
    return [tuple(util.loads(thread)) for thread in threads.lrange(0, -1)]


class StickyThread(BaseCanvasModel):
    comment = ForeignKey(Comment, null=False, related_name='sticky_threads')
    curator = ForeignKey(User, blank=True, null=True, default=None, related_name='sticky_threads')
    text = TextField()
    timestamp = UnixTimestampField(default=0)
    sort = IntegerField()

    class Meta:
        ordering = ['sort']

    @classmethod
    def get_or_create(cls, comment):
        try:
            sticky = cls.objects.get(comment=comment.id)
        except cls.DoesNotExist:
            cmt = Comment.objects.get(pk=comment.id)
            sticky = cls(comment=cmt)
            try:
                sticky.sort = 1 + max(cls.objects.values_list('sort', flat=True))
            except ValueError:
                sticky.sort = 1
            sticky.save()
        return sticky


def sticky_threads():
    return [ThreadPreview.get_from_sticky_thread(st) for st in StickyThread.objects.all()]

