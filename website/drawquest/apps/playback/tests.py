from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff, create_quest, create_quest_comment,)
from services import Services, override_service


class TestPlayback(CanvasTestCase):
    def _check(self, cmt, playback_data):
        resp = self.api_post('/api/playback/playback_data', {'comment_id': cmt.id})
        self.assertAPISuccess(resp)
        self.assertEqual(resp['playback_data'], playback_data)

    def test_empty_playback_data(self):
        self._check(create_quest_comment(), None)

    def test_playback_data(self):
        data = {'foo': 'bar'}
        self._check(create_quest_comment(playback_data=data), data)

    def test_set_playback_data_without_comment_id(self):
        resp = self.api_post('/api/playback/set_playback_data')
        self.assertAPIFailure(resp)

