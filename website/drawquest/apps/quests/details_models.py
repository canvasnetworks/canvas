from apps.client_details.models import ClientDetailsBase
from drawquest.details_models import ContentDetails


class QuestDetails(ClientDetailsBase):
    TO_CLIENT_WHITELIST = [
        'id',
        'content',
        'timestamp',
        'title',
        'comments_url',
        'author_count',
        'drawing_count',
    ]

    @classmethod
    def from_id(cls, quest_id):
        from drawquest.apps.quests.models import Quest
        return Quest.details_by_id(quest_id)()

    def to_dict(self):
        return self._d

    @property
    def content(self):
        return ContentDetails(self._d['content'])

    @property
    def reply_content(self):
        """ Shim for canvas internals. """
        return self.content

