from datetime import date

from django.conf import settings

from apps.canvas_auth.models import User
from drawquest.apps.drawquest_auth.details_models import UserDetails
from services import Services


class BaseActivity(object):
    """ Define `TYPE` in subclasses to correspond with the 'type' item in activity data. """
    @property
    def TYPE(self):
        raise NotImplementedError

    FORCE_ANONYMOUS = None

    def __init__(self, data={}, actor=None, key=None):
        """ Automatically records a timestamp as well. """
        if data.get('type', self.TYPE) != self.TYPE:
            raise TypeError("Incompatible activity type.")

        self._data = {
            'ts': Services.time.time(),
            'type': self.TYPE,
        }

        if actor:
            #TODO have a UserDetails for example.com too to get rid of this branch.
            if settings.PROJECT == 'canvas':
                self._data['actor'] = {'username': actor.username, 'id': actor.id}
            elif settings.PROJECT == 'drawquest':
                self._data['actor'] = UserDetails.from_id(actor.id).to_client()

        self._data.update(data)

        if 'id' not in self._data:
            from apps.activity.models import Activity
            db_activity = Activity.from_redis_activity(self, key=key)
            self._data['id'] = db_activity.id

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError

    def to_dict(self):
        return self._data

    def to_client(self):
        ret = self._data.copy()

        def remove_key(key):
            if key in ret:
                del ret[key]

        if self.is_actor_anonymous:
            remove_key('actor')

        remove_key('activity_type')

        return ret

    @property
    def timestamp(self):
        return self._data.get('ts')

    @property
    def actor(self):
        return self._data.get('actor')

    @property
    def actor_user(self):
        """ Returns the actual `User` instance for the actor. """
        if self.actor:
            return User.objects.get(id=self.actor['id'])

    @property
    def is_actor_anonymous(self):
        if self.FORCE_ANONYMOUS is not None:
            return self.FORCE_ANONYMOUS
        return bool(self._data.get('is_actor_anonymous'))

    @property
    def date(self):
        return date.fromtimestamp(self.ts)

    @property
    def thumbnail_url(self):
        return self._data.get('thumbnail_url')

    @property
    def details_url(self):
        """ The primary link URL for this activity item. """
        if self._data.get('details_url'):
            path = self._data.get('details_url')
            try:
                path, hash_ = path.split('#')
                hash_ = '#' + hash_
            except ValueError:
                hash_ = ''
            return '{}?from_activity={}{}'.format(path, self._data.get('id'), hash_)

    def has_read(self, viewer):
        return viewer.redis.activity_stream.has_read(self._data['id'])

