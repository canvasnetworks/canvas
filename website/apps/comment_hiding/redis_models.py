from django.core.exceptions import PermissionDenied
from django.conf import settings

from apps.canvas_auth.models import User
from canvas.redis_models import redis, RedisSet


class HiddenComments(RedisSet):
    def __init__(self, user_id):
        self.user_id = user_id
        super(HiddenComments, self).__init__('user:{}:hidden_comments'.format(user_id))

    def hide_comment(self, comment):
        """ `comment` can be a Comment instance, CommentDetails instance, or comment ID. """
        user = User.objects.get(id=self.user_id)

        if not is_dismissable(comment, user):
            raise PermissionDenied("User cannot dismiss this comment.")

        try:
            self.sadd(comment.id)
        except AttributeError:
            self.sadd(comment)


class HiddenThreads(RedisSet):
    def __init__(self, user_id):
        self.user_id = user_id
        super(HiddenThreads, self).__init__('user:{}:hidden_threads'.format(user_id))

    def hide_thread(self, comment):
        """ `comment` can be a Comment or CommentDetails. """
        user = User.objects.get(id=self.user_id)
        if not is_dismissable(comment, user):
            raise PermissionDenied("User cannot dismiss this thread.")

        self.sadd(comment.thread_op_comment_id)

    def filter_comments(self, comments, comment_key=lambda comment: comment):
        hidden_threads = self.smembers()
        return [comment for comment in comments
                if str(comment_key(comment).thread_op_comment_id) not in hidden_threads]


def remove_hidden_comment_ids(user, comment_ids):
    if not user.is_authenticated():
        return comment_ids

    to_filter = set(int(id_) for id_ in user.redis.hidden_comments.smembers())
    include = lambda x: not x in to_filter
    return filter(include, comment_ids)

def is_dismissable(comment_details, viewer):
    if not viewer.is_authenticated():
        return False

    if viewer.is_staff:
        return True

    if hasattr(comment_details, 'details'):
        comment_details = comment_details.details()

    if settings.ALLOW_HIDING_OWN_COMMENTS:
        return True

    return (comment_details.author_name.lower() != 'canvas'
            and comment_details.author_id != viewer.id)

