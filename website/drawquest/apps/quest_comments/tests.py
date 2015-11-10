from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.playback.models import Playback
from drawquest.apps.stars import models as star_models
from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff,
                                           create_quest, create_current_quest, create_quest_comment)
from services import Services, override_service


class TestQuestCommentApi(CanvasTestCase):
    def after_setUp(self):
        self.quest = create_current_quest()
        self.content = create_content()

    def _post(self, user=None, quest=None):
        if user is None:
            user = create_user()

        quest_id = getattr(quest, 'id', None) or self.quest.id
        self.comment = self.api_post('/api/quest_comments/post', {
            'quest_id': quest_id,
            'content_id': self.content.id, 
        }, user=user)['comment']

    def test_post(self):
        self.assertEqual(self.quest.author_count(), 0)

        self._post()
        self.assertEqual(self.quest.author_count(), 1)
        self.assertEqual(self.comment['quest_id'], self.quest.id)

    def test_flag(self):
        self._post()
        flag = self.api_post('/api/quest_comments/flag', {'comment_id': self.comment['id']})
        self.assertEqual(flag['flag_counts']['0'], 1)

    def test_user_comments(self):
        user = create_user()
        self._post(user=user)
        cmts = self.api_post('/api/quest_comments/user_comments', {'username': user.username})['comments']
        self.assertEqual(cmts[0]['id'], self.comment['id'])

    def test_reactions(self):
        cmt = create_quest_comment()

        star_models.star(create_user(), cmt)
        Playback.append(comment=cmt, viewer=create_user())

        cmt = QuestComment.objects.get(id=cmt.id)
        reactions = cmt.details().reactions
        self.assertEqual(len(reactions), 2)

    def test_streak_rewards(self):
        user = create_user()

        def post():
            quest = create_current_quest()

            def rewards():
                resp = self.api_post('/api/quest_comments/rewards_for_posting', {'quest_id': quest.id}, user=user)
                self.assertAPISuccess(resp)
                return resp['rewards']

            before = rewards()
            self._post(user=user, quest=quest)
            after = rewards()
            return (before, after,)

        current_streak = 0
        streaks = [3, 10, 100]

        for _ in xrange(11):
            before, after = post()

            for streak in streaks:
                msg = 'After posting this, the current streak would be: {}'.format(current_streak + 1)
                if (current_streak + 1) == streak:
                    self.assertTrue('streak_' + str(streak) in before, msg)
                    self.assertFalse('streak_' + str(streak) in after, msg)
                else:
                    self.assertFalse('streak_' + str(streak) in before, msg)

            current_streak += 1

