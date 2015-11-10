import itertools

from django.conf import settings
from django.db.models import *

from canvas import fact, bgwork
from services import Services
from canvas.cache_patterns import CachedCall
from canvas.models import BaseCanvasModel, Comment, Content, CommentSticker, Visibility, CommentFlag
from canvas.notifications.actions import Actions
from canvas.redis_models import redis
from drawquest import economy
from drawquest.apps.drawquest_auth.details_models import UserDetails
from drawquest.apps.drawquest_auth.models import User, AnonymousUser
from services import Services
from website.apps.share_tracking.models import ShareTrackingUrl


class QuestCommentManager(Visibility.PublicOnlyManager):
    def get_query_set(self):
        return super(QuestCommentManager, self).get_query_set().filter(parent_comment__isnull=False)


class QuestCommentAllManager(Manager):
    def get_query_set(self):
        return super(QuestCommentAllManager, self).get_query_set().filter(parent_comment__isnull=False)


class QuestCommentPublishedManager(Visibility.PublishedOnlyManager):
    def get_query_set(self):
        return super(QuestCommentPublishedManager, self).get_query_set().filter(parent_comment__isnull=False)


class QuestComment(Comment):
    objects = QuestCommentManager()
    all_objects = QuestCommentAllManager()
    published = QuestCommentPublishedManager()

    class Meta(object):
        proxy = True

    @classmethod
    def posting_would_complete_quest_of_the_day(cls, author, quest):
        if not author.is_authenticated():
            return quest.is_currently_scheduled()

        return quest.is_currently_scheduled() and not quest.user_has_completed(author)

    @classmethod
    def posting_would_complete_archived_quest(cls, author, quest):
        if not author.is_authenticated():
            return not quest.is_currently_scheduled()

        return not quest.is_currently_scheduled() and not quest.user_has_completed(author)

    @classmethod
    def posting_would_reward_streak(cls, author, quest):
        from drawquest.apps.quests.models import ScheduledQuest

        if not cls.posting_would_complete_quest_of_the_day(author, quest):
            return None

        STREAKS = [3, 10, 100]

        ts_cutoff = Services.time.time() - ((max(STREAKS) + 1) * 60*60*24)

        scheduled_quests = ScheduledQuest.archived(select_quests=True)[:max(STREAKS)]

        current_streak = 1

        for scheduled_quest in scheduled_quests:
            quest = scheduled_quest.quest

            if not quest.user_has_completed(author):
                break

            current_streak += 1

        if current_streak in STREAKS:
            return current_streak

    @classmethod
    def posting_in_first_quest(cls, author):
        return not author.comments.exists()

    @classmethod
    def create_and_post(cls, request, author, content, quest, fact_metadata=None):
        from drawquest.apps.quests.models import Quest

        if not isinstance(quest, Quest):
            quest = Quest.objects.get(id=quest.id)

        was_first_quest = QuestComment.posting_in_first_quest(request.user)
        was_quest_of_the_day = cls.posting_would_complete_quest_of_the_day(author, quest)
        was_archived_quest = cls.posting_would_complete_archived_quest(author, quest)

        comment = super(QuestComment, cls).create_and_post(
            request,
            author,
            False,
            None,
            content,
            parent_comment=quest,
            fact_metadata=fact_metadata,
            posted_on_quest_of_the_day=quest.is_currently_scheduled(),
        )

        streak = QuestComment.posting_would_reward_streak(author, quest)
        if streak:
            economy.credit_streak(author, streak)

        if was_first_quest:
            economy.credit_first_quest(author)
        elif was_quest_of_the_day:
            economy.credit_quest_of_the_day_completion(author)
        elif was_archived_quest:
            economy.credit_archived_quest_completion(author)

        @bgwork.defer
        def followee_posted():
            Actions.followee_posted(author, comment)

        return comment

    @classmethod
    def by_author(cls, author):
        return cls.objects.filter(author=author).order_by('-id')

    @property
    def drawquest_author(self):
        return User.objects.get(id=self.author_id)

    def get_stars(self):
        """
        Returns a list of `{username, timestamp, id}` dicts.
        """
        stickers = CommentSticker.objects.filter(comment=self, type_id=settings.STAR_STICKER_TYPE_ID)
        stickers = stickers.values('user_id', 'timestamp', 'id')
        return [
            {
                'user': User.details_by_id(sticker['user_id'])(),
                'timestamp': sticker['timestamp'],
                'id': sticker['id'],
            }
            for sticker in stickers
        ]

    def get_reactions(self):
        """
        Includes just stars and playbacks, for now, interleaved by timestamp.
        """
        stars = self.get_stars()
        for star in stars:
            star['reaction_type'] = 'star'

        playbacks = [{
            'id': playback.id,
            'user': UserDetails.from_id(playback.viewer_id),
            'timestamp': playback.timestamp,
            'reaction_type': 'playback',
        } for playback in self.playbacks.all()]

        reactions = itertools.chain(stars, playbacks)
        return sorted(reactions, key=lambda reaction: reaction['timestamp'], reverse=True)

    def _details(self):
        content_details = self.reply_content.details().to_backend() if self.reply_content else {}

        return {
            'author_id': self.author_id,
            'content': content_details,
            'id': self.id,
            'quest_id': self.parent_comment_id,
            'quest_title': self.parent_comment.title,
            'reply_count': self.get_replies().count(),
            'timestamp': self.timestamp,
            'reactions': self.get_reactions(),
            'star_count': len(self.get_stars()),
            'playback_count': len(self.get_stars()),
            'posted_on_quest_of_the_day': self.posted_on_quest_of_the_day,

            # Shims for canvas internals.
            'sticker_counts': self.get_sticker_counts(),
            'repost_count': 0,
        }

    @classmethod
    def details_by_id(cls, comment_id, promoter=None):
        from drawquest.apps.quest_comments.details_models import QuestCommentDetails

        if promoter is None:
            promoter = QuestCommentDetails

        def inner_call():
            return cls.all_objects.get(id=comment_id)._details()

        return CachedCall(
            'quest_comment:{}:details_v15'.format(comment_id),
            inner_call,
            24*60*60,
            promoter=promoter,
        )

    @property
    def quest(self):
        return self.parent_comment

    @property
    def details(self):
        return self.details_by_id(self.id)

    @property
    def flagged_details(self):
        #TODO: create a more elegant role syystem for comment detail types
        from canvas.details_models import FlaggedCommentDetails
        return QuestComment.details_by_id(self.id, promoter=FlaggedCommentDetails)

    def flag_count(self):
        return CommentFlag.objects.filter(comment=self, undone=False, type_id=0).count()

    def star(self, user):
        from drawquest.apps.stars.models import star
        return star(user, self)

    def unstar(self, user):
        from drawquest.apps.stars.models import unstar
        return unstar(user, self)

    def get_share_page_url(self, absolute=False):
        url = self.details().share_page_url
        if absolute:
            url = 'http://' + settings.DOMAIN + url
        return url

    def get_share_page_url_with_tracking(self, sharer, channel, request=None, absolute=False):
        url = self.get_share_page_url(absolute=absolute)
        share = ShareTrackingUrl.create(sharer, url, channel)

        if request and channel != 'testing':
            fact.record('create_share_url', request, dict(url=url, channel=channel, share=share.id))

        return share.url_for_channel()

