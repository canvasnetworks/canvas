from canvas.exceptions import ServiceError
from drawquest import economy
from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff, create_quest, create_quest_comment)
from drawquest.apps.stars import models
from services import Services, override_service


class TestStars(CanvasTestCase):
    def after_setUp(self):
        self.comment = create_quest_comment()
        self.user = create_user()

    def _star(self, api=False, user=None):
        if user is None:
            user = self.user

        if api:
            self.api_post('/api/stars/star', {'comment_id': self.comment.id}, user=user)
        else:
            models.star(user, self.comment)

    def _unstar(self, api=False):
        if api:
            self.api_post('/api/stars/unstar', {'comment_id': self.comment.id}, user=self.user)
        else:
            models.unstar(self.user, self.comment)

    def test_star(self):
        self._star()
        self.assertEqual(self.comment.get_stars()[0]['user'].id, self.user.id)

    def test_unstar(self):
        self._star()
        self._unstar()
        self.assertEqual(len(self.comment.get_stars()), 0)

    def test_unstar_without_star(self):
        self.assertRaises(ServiceError, self._unstar)

    def test_star_api(self):
        self._star(api=True)
        self.assertEqual(self.comment.get_stars()[0]['user'].id, self.user.id)

    def test_unstar_api(self):
        self._star()
        self._unstar(api=True)
        self.assertEqual(len(self.comment.get_stars()), 0)

    def test_restar(self):
        def num(num):
            self.assertEqual(len(self.comment.get_stars()), num)

        self._star(api=True)
        num(1)
        self._unstar(api=True)
        num(0)
        self._star(api=True)
        num(1)

    def test_self_star_reward_is_nothing(self):
        balance = economy.balance(self.comment.author)
        self._star(user=self.comment.author)
        self.assertEqual(economy.balance(self.comment.author), balance)

