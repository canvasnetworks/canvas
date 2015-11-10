from django.db.models import *
from django.db import IntegrityError

from canvas import json, bgwork
from canvas.models import BaseCanvasModel
from canvas.notifications.actions import Actions
from canvas.util import UnixTimestampField, Now
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.quest_comments.models import QuestComment


class Playback(BaseCanvasModel):
    comment = ForeignKey(QuestComment, related_name='playbacks', null=False)
    viewer = ForeignKey(User, null=False)
    timestamp = UnixTimestampField(default=0)

    class Meta(object):
        unique_together = ('comment', 'viewer',)

    @classmethod
    def append(cls, **kwargs):
        """ Ignores dupes. """
        if not 'timestamp' in kwargs:
            kwargs['timestamp'] = Now()

        instance = cls(**kwargs)

        try:
            instance.save()
        except IntegrityError:
            return

        instance.comment.details.force()

        @bgwork.defer
        def playback_action():
            Actions.playback(instance.viewer, instance.comment)

    def to_client(self):
        return {
            'timestamp': self.timestamp,
            'viewer': self.viewer,
        }


class PlaybackData(BaseCanvasModel):
    comment = OneToOneField(QuestComment, related_name='playback_data', null=False, unique=True)
    blob = TextField()

    @classmethod
    def create_with_json(cls, comment, json_data):
        return cls.objects.create(comment=comment, blob=json.dumps(json_data))

    @property
    def json_data(self):
        return json.loads(self.blob)

    @json_data.setter
    def set_json_data(self, data):
        self.blob = json.dumps(data)

