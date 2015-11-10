from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff,
                                           create_quest, create_current_quest, create_quest_comment)
from drawquest import knobs
from services import Services, override_service


class TestQuestApi(CanvasTestCase):
    def after_setUp(self):
        self.old_quest = create_current_quest()
        self.quest = create_current_quest()
        self.user = create_user()
        knobs.ONBOARDING_QUEST_ID = self.quest.id

    def test_quest_archive(self):
        archive = self.api_post('/api/quests/archive')['quests']
        self.assertEqual(len(archive), 1)
        self.assertEqual(archive[0]['id'], self.old_quest.id)

    def test_quest_comments(self):
        cmt = create_quest_comment(self.quest)
        cmts = self.api_post('/api/quests/comments', {'quest_id': self.quest.id})['comments']
        self.assertEqual(cmts[0]['id'], cmt.id)

    def test_current_quest(self):
        quest = self.api_post('/api/quests/current')['quest']
        self.assertEqual(quest['id'], self.quest.id)

    def test_onboarding_quest(self):
        quest = self.api_post('/api/quests/onboarding')['quest']
        self.assertEqual(int(quest['id']), int(self.quest.id))

