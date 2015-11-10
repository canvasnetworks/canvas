from datetime import timedelta as td

from cachecow.decorators import cached_function
from django.conf import settings
from django.db.models import *
from django.db.models.signals import post_save
from django.shortcuts import get_object_or_404, Http404

from canvas.cache_patterns import CachedCall
from canvas.models import BaseCanvasModel, Comment, Content, get_mapping_id_from_short_id
from canvas.redis_models import RealtimeChannel
from canvas.redis_models import redis
from canvas.util import UnixTimestampField
from drawquest import knobs
from drawquest.apps.drawquest_auth.models import User, AnonymousUser
from drawquest.apps.push_notifications.models import push_notification
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests import signals
from services import Services


class QuestPreview(object):
    def __init__(self, quest):
        self.quest = quest
        self.curator = ""
        self.timestamp = None
        self.sort = None
        self.scheduled_quest_id = None

    @classmethod
    def get_by_short_id(cls, short_id):
        try:
            mapping_id = get_mapping_id_from_short_id(short_id)
        except ValueError:
            raise Http404
        quest = get_object_or_404(Quest.published, id=mapping_id)
        return cls.get_from_quest(quest)

    @classmethod
    def get_from_quest(cls, quest):
        return cls(quest.thread.op.details())

    @classmethod
    def get_from_scheduled_quest(cls, scheduled_quest):
        preview = cls.get_from_quest(scheduled_quest.quest)
        preview.curator = getattr(scheduled_quest.curator, 'username', '')
        preview.timestamp = scheduled_quest.timestamp
        preview.sort = scheduled_quest.sort
        preview.scheduled_quest_id = scheduled_quest.id
        return preview


class ScheduledQuest(BaseCanvasModel):
    quest = ForeignKey('Quest', null=False)
    curator = ForeignKey(User, blank=True, null=True, default=None, related_name='scheduled_quests')
    timestamp = UnixTimestampField(default=0)
    appeared_on = UnixTimestampField(null=True, db_index=True)
    sort = IntegerField()

    class Meta:
        ordering = ['-appeared_on']

    @classmethod
    def get_or_create(cls, quest):
        if quest.parent_comment_id:
            quest = quest.parent_comment

        try:
            return cls.objects.get(quest=quest.id)
        except cls.DoesNotExist:
            return cls.objects.create(quest=Quest.objects.get(pk=quest.id), sort=1)

    @classmethod
    def archived(cls, select_quests=False):
        qs = cls.objects
        if select_quests:
            qs = qs.select_related('quest')

        current_quest_id = redis.get('dq:current_scheduled_quest')
        if current_quest_id:
            qs = qs.exclude(id=current_quest_id)

        return qs.exclude(appeared_on__isnull=True).order_by('-appeared_on')

    @classmethod
    def unarchived(cls):
        return cls.objects.filter(appeared_on__isnull=True).order_by('sort')

    def _publish_quest_of_the_day(self):
        signals.current_quest_changed.send(ScheduledQuest, instance=self)

        RealtimeChannel('qotd', 1).publish({'quest_id': self.quest_id})

        push_notification('quest_of_the_day',
                          "Today's Quest: {}".format(self.quest.title),
                          extra_metadata={'quest_id': self.quest.id},
                          badge=1)

    def set_as_current_quest(self):
        redis.set('dq:current_scheduled_quest', self.id)
        self.appeared_on = Services.time.time()
        self.save()

        self.quest.details.force()

        self._publish_quest_of_the_day()

    @classmethod
    def rollover_next_quest(cls):
        """
        Sets the next scheduled quest as the currently active one / quest of the day.
        """
        cls.unarchived().order_by('sort')[0].set_as_current_quest()

    @classmethod
    def current_scheduled_quest(cls):
        """ The `ScheduledQuest` instance representing the current quest of the day. """
        scheduled_quest_id = redis.get('dq:current_scheduled_quest')
        if scheduled_quest_id:
            return cls.objects.get(id=scheduled_quest_id)


class Quest(Comment):
    class Meta:
        proxy = True

    @property
    def comments_url(self):
        return settings.API_PREFIX + 'quests/comments'

    @property
    def comments(self):
        return self.replies

    @classmethod
    def completed_by_user_count(self, user):
        """ The number of quests a user has completed. """
        return QuestComment.by_author(user).values('parent_comment_id').distinct().count()

    def author_count(self):
        return self.replies.values_list('author_id', flat=True).distinct().count()

    def drawing_count(self):
        return self.replies.exclude(reply_content__isnull=True).count()

    def comments_details(self):
        cmts = QuestComment.objects.filter(parent_comment=self).order_by('-id')
        return CachedCall.multicall([cmt.details for cmt in cmts])

    def schedule(self, ordinal, curator=None):
        """ Returns `scheduled_quest` instance. """
        scheduled_quest = ScheduledQuest.get_or_create(self)

        if not scheduled_quest.curator:
            scheduled_quest.curator = curator
            scheduled_quest.timestamp = Services.time.time()

        scheduled_quest.sort = ordinal
        scheduled_quest.save()
        return scheduled_quest

    def is_currently_scheduled(self):
        """ 'currently scheduled' means it's the quest of the day. """
        scheduled_quest = ScheduledQuest.objects.get(id=redis.get('dq:current_scheduled_quest'))
        return scheduled_quest.quest_id == self.id

    def is_onboarding_quest(self):
        return str(knobs.ONBOARDING_QUEST_ID) == str(self.id)

    def user_has_completed(self, user):
        """ Whether `user` has contributed a drawing for this quest. """
        return self.replies.filter(author=user).exclude(reply_content__isnull=True).exists()

    def _details(self):
        content_details = self.reply_content.details().to_backend() if self.reply_content else {}

        ts = self.timestamp
        if self.scheduledquest_set.exists():
            ts = self.scheduledquest_set.all().order_by('-appeared_on')[0].appeared_on or ts

        return {
            'id': self.id,
            'content': content_details,
            'timestamp': ts,
            'title': self.title,
            'comments_url': self.comments_url,
            'author_count': self.author_count(),
            'drawing_count': self.drawing_count(),
            'visibility': self.visibility,
        }

    @classmethod
    def details_by_id(cls, quest_id):
        from drawquest.apps.quests.details_models import QuestDetails

        def inner_call():
            return cls.all_objects.get(id=quest_id)._details()

        return CachedCall(
            'quest:{}:details_v6'.format(quest_id),
            inner_call,
            24*60*60,
            promoter=QuestDetails,
        )

    @property
    def details(self):
        return self.details_by_id(self.id)

def scheduled_quest_previews():
    return [QuestPreview.get_from_scheduled_quest(st) for st in ScheduledQuest.unarchived()]

def suggested_quests():
    scheduled_ids = ScheduledQuest.objects.all().values_list('quest_id', flat=True)

    quests = Quest.public.filter(parent_comment__isnull=True).order_by('-timestamp')
    quests = [quest for quest in quests if quest.id not in scheduled_ids]
    quests = quests[:300]

    return [QuestPreview.get_from_quest(quest) for quest in quests]

@cached_function(timeout=td(days=7), key=[
    'completed_quest_ids',
    lambda user: getattr(user, 'id', user),
])
def completed_quest_ids(user):
    from drawquest.apps.quest_comments.models import QuestComment

    comments = QuestComment.objects.filter(author=user).exclude(reply_content__isnull=True)
    return list(comments.values_list('parent_comment_id', flat=True).distinct())

# Cache invalidation for completed_quest_ids.
post_save.connect(
    lambda sender, instance, **kwargs: completed_quest_ids.delete_cache(instance.author_id),
    sender=QuestComment, dispatch_uid='post_save_for_completed_quest_ids_api', weak=False
)

def archived_quests():
    """ Returns quest details. """
    archived_quests = ScheduledQuest.archived(select_quests=True)
    quests = CachedCall.multicall([archived.quest.details for archived in archived_quests])

    return quests

def current_quest_details():
    try:
        quest = ScheduledQuest.current_scheduled_quest().quest
    except AttributeError:
        return None

    return quest.details()

