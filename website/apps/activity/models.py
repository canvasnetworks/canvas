from datetime import date
import itertools

from django.db.models import *
from django.conf import settings

from apps.canvas_auth.models import User
from canvas import util, knobs
from canvas.cache_patterns import CachedCall
from canvas.models import BaseCanvasModel, Category
from canvas.util import UnixTimestampField, Now
from drawquest.apps.drawquest_auth.details_models import UserDetails


class Activity(BaseCanvasModel):
    actor = ForeignKey(User, null=True)
    timestamp = UnixTimestampField()
    activity_type = CharField(max_length=255, blank=False)
    data = TextField()
    key = PositiveIntegerField(blank=True, null=True)

    class Meta(object):
        unique_together = ('activity_type', 'key')

    @classmethod
    def from_redis_activity(cls, activity, key=None):
        act = cls()

        if activity.actor:
            act.actor = User.objects.get(pk=activity.actor['id'])

        act.timestamp = activity.timestamp
        act.activity_type = activity.TYPE
        act.key = key
        discard_keys = ['actor', 'ts', 'type']
        base = activity.to_dict()
        act._data = {k: base[k] for k in base.keys() if k not in discard_keys}
        act.data = util.dumps(act._data)
        act.save()
        return act

    def _details(self):
        base = util.loads(self.data)
        base.update({
            'id': self.id,
            'ts': self.timestamp,
            'activity_type': self.activity_type,
        })

        #TODO have a UserDetails for example.com too to get rid of this branch.
        if self.actor:
            if settings.PROJECT == 'canvas':
                base['actor'] = {
                    'id': self.actor.id,
                    'username': self.actor.username,
                }
            elif settings.PROJECT == 'drawquest':
                base['actor'] = UserDetails.from_id(self.actor.id).to_client()

        return base

    @classmethod
    def details_by_id(cls, id):
        return CachedCall(
            "activity:%s:details_v2" % id,
            lambda: cls.objects.get(id=id)._details(),
            30*24*60*60,
        )

    @property
    def details(self):
        return Activity.details_by_id(self.id)


def get_activity_stream_items(user, earliest_timestamp_cutoff=None):
    stream = user.redis.activity_stream

    if earliest_timestamp_cutoff:
        stream = stream.iter_until(earliest_timestamp_cutoff)

    return list(itertools.islice(stream, 0, knobs.ACTIVITY_STREAM_PER_PAGE))

