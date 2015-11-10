from datetime import timedelta as td

from django.conf import settings
from django.conf.urls.defaults import url, patterns, include

from drawquest.api_cache import cached_api
from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff,
                                           create_quest, create_current_quest, create_quest_comment,
                                           fake_api_request)
from drawquest.api_decorators import api_decorator
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.drawquest_auth.models import User
from canvas.exceptions import ServiceError, ValidationError
from canvas import util
from canvas.models import Visibility
from services import Services, override_service


class TestProfile(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()
    
    def test_bio(self):
        bio = 'my new bio'
        self.api_post('/api/user/change_profile', {'bio': bio}, user=self.user)
        self.assertEqual(self.api_post('/api/user/profile', {'username': self.user.username})['bio'], bio)

    def test_realtime_sync(self):
        resp = self.api_post('/api/realtime/sync', user=self.user)
        self.assertAPISuccess(resp)
        self.assertTrue(self.user.redis.activity_stream_channel.channel in resp['channels'])

    def test_create_share_url_for_channel_via_api(self):
        cmt = create_quest_comment()
        result = self.api_post('/api/share/create_for_channel',
                               {'comment_id': cmt.id, 'channel': 'testing'}, user=self.user)
        self.assertAPISuccess(result)
        url = result['share_url']
        rmatch = '/s/1j'
        self.assertEqual(url[url.rfind(rmatch):], rmatch)

    def test_heavy_state_sync(self):
        state = self.api_post('/api/heavy_state_sync', user=self.user)
        self.assertAPISuccess(state)
        self.assertEqual(state['user_profile']['user']['username'], self.user.username)


class TestFlags(CanvasTestCase):
    def test_auto_moderation_from_flags(self):
        cmt = create_quest_comment()

        for i in range(1, settings.AUTO_MODERATE_FLAGGED_COMMENTS_THRESHOLD + 1):
            resp = self.api_post('/api/comment/flag', {'comment_id': cmt.id})

            cmt = QuestComment.all_objects.get(pk=cmt.pk)
            getattr(self, 'assert' + str(i == settings.AUTO_MODERATE_FLAGGED_COMMENTS_THRESHOLD))(
                cmt.visibility == Visibility.DISABLED)

        self.assertTrue(cmt.id in [qc.id for qc in QuestComment.unjudged_flagged()])

    def test_self_flag(self):
        cmt = create_quest_comment()
        resp = self.api_post('/api/comment/flag', {'comment_id': cmt.id}, user=cmt.author)


class TestCache(CanvasTestCase):
    def after_setUp(self):
        urls = patterns('')
        self.api = api_decorator(urls)

    def _api(self, api_func, data={}):
        return util.loads(api_func(fake_api_request('', data=data)).content)

    def test_cache_hit(self):
        i = [0]

        @self.api('test_cache')
        @cached_api(td(days=2), key='test_cache')
        def test_cache(request):
            i[0] += 1
            return {'i': i[0]}

        for _ in range(2):
            print self._api(test_cache)
            self.assertEqual(self._api(test_cache)['i'], 1)

    def test_uncached(self):
        i = [0]

        @self.api('test_uncached')
        def test_cache(request):
            i[0] += 1
            return {'i': i[0]}

        for j in range(1, 2):
            self.assertEqual(self._api(test_cache)['i'], j)

