from django.db import IntegrityError
from django.db.models import *
from django.conf import settings

from canvas.exceptions import ServiceError
from canvas.models import BaseCanvasModel, CommentSticker, Comment
from drawquest import economy
from drawquest.apps.drawquest_auth.models import User


class Unstar(BaseCanvasModel):
    """
    Records the first un-star for a comment by a user, which we check for when re-starring to avoid sending
    duplicate notifications.
    """
    comment = OneToOneField(Comment, db_index=True)
    user = ForeignKey(User, db_index=True)

    class Meta(object):
        unique_together = ('comment', 'user')

def has_starred(user, comment):
    try:
        Unstar.objects.get(comment=comment, user=user)
        return True
    except Unstar.DoesNotExist:
        return False

def get_star_sticker():
    from canvas import stickers

    return stickers.get(settings.STAR_STICKER_TYPE_ID)

def star(user, comment, ip='0.0.0.0'):
    if not comment.parent_comment_id:
        raise ServiceError("Can't star a quest.")

    comment.sticker(user, settings.STAR_STICKER_TYPE_ID, skip_self_check=True, ip=ip)

    if not has_starred(comment, user) and user.id != comment.author_id:
        economy.credit_star(comment.author)

def unstar(user, comment):
    try:
        sticker = CommentSticker.objects.get(type_id=settings.STAR_STICKER_TYPE_ID, comment=comment, user=user)
    except CommentSticker.DoesNotExist:
        raise ServiceError("Can't remove a star from something you didn't star in the first place.")

    try:
        Unstar.objects.create(comment=sticker.comment, user=user)
    except IntegrityError:
        pass

    sticker.delete()

    comment.details.force()
    comment.update_score()

