from django.core.exceptions import PermissionDenied
from django.db import models

from canvas.details_models import CommentDetails
from canvas.exceptions import ServiceError
from canvas.redis_models import RedisSet
from canvas.notifications.actions import Actions
from canvas.url_util import verify_first_party_url


class RemixInviteArchive(RedisSet):
    def __init__(self, user):
        super(RemixInviteArchive, self).__init__('user:{}:invited_remixes'.format(user.id))
        self.user = user

    def add_invite(self, comment):
        self.sadd(comment.id)

    def invites(self):
        return CommentDetails.from_ids(self.smembers())
    
    def mobile_monster_invites(self):
        return [comment for comment in self.invites() if comment.is_monster_top(mobile=True)]


class RemixInvites(RedisSet):
    actions = {
        'invite': Actions.invite_remixer,
        'monster': Actions.invite_monster_remixer,
    }

    def __init__(self, comment):
        super(RemixInvites, self).__init__('comment:{}:invited_remixers'.format(comment.id))
        self.comment = comment

    def invite(self, inviter, invitee, type='invite'):
        if invitee.id in self:
            raise ServiceError("User has already been invited.")
        if invitee.id == inviter.id:
            raise ServiceError("You can't invite yourself to remix! You're already here!")
        if self.comment.author == invitee:
            raise ServiceError("That user is already in this thread.")
        self.actions[type](inviter, self.comment, invitee)
        self.sadd(invitee.id)

        invitee.remix_invites.add_invite(self.comment)

