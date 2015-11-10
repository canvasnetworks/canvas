from apps.invite_remixer import urls
from apps.monster.models import MONSTER_GROUP, MONSTER_MOBILE_GROUP
from canvas.exceptions import ServiceError
from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_user,
                                        create_group, create_comment, pretty_print_etree)


class TestModels(CanvasTestCase):
    def after_setUp(self):
        self.inviter = create_user()
        self.invitee = create_user()
        self.comment = create_comment(author=self.inviter, reply_content=create_content())

    def test_invite_remixers(self):
        self.assertFalse(self.invitee.id in self.comment.remix_invites)

        self.comment.remix_invites.invite(self.inviter, self.invitee)
        self.assertTrue(self.invitee.id in self.comment.remix_invites)

        self.assertRaises(ServiceError, lambda: self.comment.remix_invites.invite(self.inviter, self.invitee))

    def test_invite_archive(self):
        def get_invites(m='invites'):
            return [c.id for c in getattr(self.invitee.remix_invites, m)()]

        self.assertFalse(get_invites())

        self.comment.remix_invites.invite(self.inviter, self.invitee)
        self.assertTrue(self.comment.id in get_invites())

        self.assertFalse(self.comment.id in get_invites('mobile_monster_invites'))


class TestUrls(CanvasTestCase):
    def after_setUp(self):
        self.inviter = create_user()
        self.comment = create_comment()

    def test_reverse(self):
        invite_id = urls.invite_id(self.inviter, comment_id=self.comment.id)
        
        inviter2, url = urls.reverse_invite_id(invite_id)
        self.assertEqual(self.comment.get_absolute_url(), url)
        self.assertEqual(self.inviter.id, inviter2.id)

    def test_url(self):
        invite_url = urls.invite_url(self.inviter, comment_id=self.comment.id)
        self.assertTrue(invite_url)


class TestApi(CanvasTestCase):
    def after_setUp(self):
        self.inviter = create_user()
        self.invitee = create_user()
        self.comment = create_comment(author=self.inviter, reply_content=create_content(),
                                      category=create_group(name=MONSTER_MOBILE_GROUP))

    def test_monster_invites(self):
        def result():
            return self.api_post('/api/invite_remixer/all_mobile_monster_completion_invites', user=self.invitee)

        self.assertFalse(result()['invites'])

        self.comment.remix_invites.invite(self.inviter, self.invitee, type='monster')
        self.assertTrue(result()['invites'])

