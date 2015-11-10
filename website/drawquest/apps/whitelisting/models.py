from django.db import models

from cachecow.cache import invalidate_namespace

from canvas.models import CommentModerationLog, Visibility
from canvas.redis_models import redis
from drawquest.apps.quest_comments.models import QuestComment


def allow(moderator, comment):
    return moderate(moderator, comment, Visibility.PUBLIC)

def deny(moderator, comment):
    return moderate(moderator, comment, Visibility.DISABLED)

def enable(from_id=None):
    if from_id is None:
        from_id = get_latest_before_unjudged_id()

        if from_id is None:
            from_id = 0

    redis.set('dq:comment_freeze_id', from_id)
    invalidate_namespace('comments')

def disable():
    redis.delete('dq:comment_freeze_id')
    invalidate_namespace('comments')

def get_latest_before_unjudged_id():
    id_ = redis.get('dq:comment_freeze_id')

    if id_ is None:
        id_ = 0

    id_ = long(id_)

    earliest_unjudged = QuestComment.all_objects.filter(
        id__gt=id_,
        judged=False,
    ).order_by('id')

    if earliest_unjudged.exists():
        #print 'id',earliest_unjudged[0].id
        earliest_unjudged_id = earliest_unjudged[0].id

        latest_before_unjudged = QuestComment.all_objects.filter(
            #timestamp__lt=earliest_unjudged_ts,
            id__lt=earliest_unjudged_id,
        ).order_by('-id')

        if not latest_before_unjudged.exists():
            return

        new_id = latest_before_unjudged[0].id
    else:
        latest = QuestComment.all_objects.all().order_by('-id')
        
        if not latest.exists():
            return

        latest = latest[0]
        new_id = latest.id
    return new_id

def update_freeze():
    id_ = redis.get('dq:comment_freeze_id')
    if id_ is None:
        return

    new_id = get_latest_before_unjudged_id()

    redis.set('dq:comment_freeze_id', new_id)
    return new_id

def moderate(moderator, comment, visibility):
    comment.visibility = visibility
    comment.judged = True
    comment.save()

    CommentModerationLog.append(
        user=comment.author,
        comment=comment,
        moderator=moderator,
        visibility=visibility,
    )

    comment.visibility_changed()

    update_freeze()

