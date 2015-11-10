from apps.client_details.models import ClientDetailsBase
from canvas.details_models import CommentDetailsStickersMixin, CommentDetailsRealtimeMixin
from drawquest.details_models import ContentDetails
from drawquest.apps.drawquest_auth.details_models import UserDetails
from canvas import util


class QuestCommentDetails(ClientDetailsBase, CommentDetailsStickersMixin, CommentDetailsRealtimeMixin):
    TO_CLIENT_WHITELIST = [
        'id',
        'user',
        'timestamp',
        'content',
        'quest_id',
        'quest_title',
        'reactions',
        'posted_on_quest_of_the_day',
    ]

    @classmethod
    def from_id(cls, comment_id):
        from drawquest.apps.quest_comments.models import QuestComment
        return QuestComment.details_by_id(comment_id)()

    def to_dict(self):
        return self._d

    @property
    def content(self):
        return ContentDetails(self._d['content'])

    @property
    def reply_content(self):
        """ Shim for canvas internals. """
        return self.content

    @property
    def share_page_url(self):
        return '/p/' + util.base36encode(self.id)

    @property
    def user(self):
        return UserDetails.from_id(self.author_id)

