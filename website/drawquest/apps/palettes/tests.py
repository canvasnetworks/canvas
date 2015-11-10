from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group, create_comment,
                                        create_staff)
from drawquest.apps.drawquest_auth.models import AnonymousUser
from services import Services, override_service


class TestPalettes(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()

    def _user_palettes(self):
        resp = self.api_post('/api/palettes/user_palettes', user=self.user)
        self.assertAPISuccess(resp)
        return resp['palettes']

    def _buyable(self):
        resp = self.api_post('/api/palettes/purchasable_palettes', user=self.user)
        self.assertAPISuccess(resp)
        return resp['palettes']

    def _user_has_palette(self, palette):
        return palette['name'] in [p['name'] for p in self._user_palettes()]

    def _purchase(self, palette):
        return self.api_post('/api/palettes/purchase_palette', {
            'palette_name': palette['name'],
            'username': self.user.username,
        }, user=self.user)

    def test_purchase_with_insufficient_balance(self):
        palette = self._buyable()[0]
        self.assertAPIFailure(self._purchase(palette))
        self.assertFalse(self._user_has_palette(palette))

    def test_user_doesnt_have_other_palettes_before_purchasing(self):
        palette = self._buyable()[0]
        self.assertFalse(self._user_has_palette(palette))

    def test_purchase(self):
        palette = self._buyable()[0]
        self.user.kv.stickers.currency.increment(palette['cost'])
        self.assertAPISuccess(self._purchase(palette))
        self.assertTrue(self._user_has_palette(palette))

    def test_anonymous_palettes(self):
        user = AnonymousUser()
        palettes = self._user_palettes()
        self.assertEqual(palettes[0]['name'], 'default')

