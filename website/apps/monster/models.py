from random import choice

from django.db.models import ForeignKey, CharField

from apps.canvas_auth.models import User, AnonymousUser
from canvas.browse import TileDetails
from canvas.cache_patterns import CachedCall
from canvas.models import BaseCanvasModel, Comment, Content
from canvas.redis_models import RedisSet
from canvas.util import UnixTimestampField, Now, base36encode, Services


MONSTER_GROUP = 'monstermash'
MONSTER_MOBILE_GROUP = 'monstermashmobile'


class CompletedMonsterSet(RedisSet):
    def __init__(self, user):
        key = 'monstermash:{0}:completed'.format(user.username)
        super(CompletedMonsterSet, self).__init__(key)

    def __iter__(self):
        return iter(self.smembers())


class MonsterPart(BaseCanvasModel):
    comment = ForeignKey(Comment, null=False, related_name='monster_parts')
    hint_slice = ForeignKey(Content, null=True, blank=True)

    @classmethod
    def get_by_comment(cls, comment):
        try:
            monster_part = cls.objects.get(comment=comment.id)
        except cls.DoesNotExist:
            cmt = Comment.objects.get(pk=comment.id)
            monster_part = cls(comment=cmt)
            monster_part.save()
        return monster_part

    @classmethod
    def get_random_new_monster(cls, user):
        try:
            # monstermash ops
            query = Comment.objects.filter(category__name=MONSTER_GROUP,parent_comment=None)
            if not isinstance(user, AnonymousUser):
                # not completed by current user
                completed = CompletedMonsterSet(user).smembers()
                if len(completed) > 0:
                    query = query.exclude(id__in=completed)
            return choice(query[:30])
        except IndexError:
            return None


class MonsterInvite(BaseCanvasModel):
    monster_part = ForeignKey(MonsterPart, null=False, related_name='invites')
    timestamp = UnixTimestampField(null=False)
    used_by = ForeignKey(User, null=True)

    @classmethod
    def get_by_monsterpart(cls, monster_part):
        try:
            invite = cls.objects.get(monster_part=monster_part)
        except cls.DoesNotExist:
            invite = cls(monster_part=monster_part, timestamp=Services.time.time())
            invite.save()
        return invite

    @property
    def code(self):
        str_code = "{0}{1}".format(self.pk, int(self.timestamp))
        return base36encode(int(str_code))

    @property
    def is_used(self):
        return not self.used_by is None

    def claim(self, user):
        self.timestamp = Services.time.time()
        self.used_by = user
        self.save()


class MobileUser(BaseCanvasModel):
    device_token = CharField(max_length=128, unique=True, blank=False)
    user = ForeignKey(User, related_name="device_tokens", blank=False, null=False, default=None)

    def __init__(self, user, device_token):
        super(MobileUser, self).__init__()
        self.user = user
        self.device_token = device_token

    @classmethod
    def register(cls, user, device_token):
        # clear out other references to the token
        cls.objects.filter(device_token=device_token).delete()
        mobile_user = cls(user, device_token)
        mobile_user.save()

    @classmethod
    def get_tokens(cls, user):
        return cls.objects.filter(user=user).values_list('device_token', flat=True)


def mobile_details_from_queryset(comments):
    bottoms, tops = CachedCall.many_multicall([cmt.details           for cmt in comments],
                                              [cmt.thread.op.details for cmt in comments])
    tiles = []
    for bottom, top in zip(bottoms, tops):
        tile = {
            'top': top,
            'bottom': bottom,
        }
        tiles.append(tile)
    return tiles


class MonsterTileDetails(TileDetails):
    def __init__(self, bottom_comment_details, top_comment_details):
        super(MonsterTileDetails, self).__init__(bottom_comment_details)
        self._top = top_comment_details

    @classmethod
    def from_queryset(cls, comments):
        bottoms, tops = CachedCall.many_multicall([cmt.details           for cmt in comments],
                                                  [cmt.thread.op.details for cmt in comments])
        tiles = []
        for bottom, top in zip(bottoms, tops):
            tile = cls(bottom, top)
            tiles.append(tile)
        return tiles

    @classmethod
    def from_queryset_with_viewer_stickers(cls, viewer, comments):
        bottoms, tops = CachedCall.many_multicall([cmt.details           for cmt in comments],
                                                  [cmt.thread.op.details for cmt in comments])
        tiles = []
        for bottom, top in zip(bottoms, tops):
            tile = cls(bottom, top)
            tile.viewer_sticker = Comment.get_sticker_from_user_for_comment_id(bottom.id, viewer)
            tiles.append(tile)
        return tiles

    @classmethod
    def from_shared_op_details_with_viewer_stickers(cls, viewer, top_details, reply_details):
        """
        `top_details` is a single CommentDetails instance of the monster top.
        `reply_details` is a list of CommentDetails instances, of the monster replies/bottoms.
        """
        tiles = []
        for bottom in reply_details:
            tile = cls(bottom, top_details)
            tile.viewer_sticker = Comment.get_sticker_from_user_for_comment_id(bottom.id, viewer)
            tiles.append(tile)
        return tiles

    @property
    def top(self):
        return self._top

    @property
    def bottom(self):
        return self._comment_details

