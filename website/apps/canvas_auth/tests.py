# -*- coding: utf-8 -*-
import base64
import datetime

from django.test.client import Client

from apps.canvas_auth.models import AnonymousUser, User
from canvas.tests.tests_helpers import CanvasTestCase, create_content, create_user, create_comment, PASSWORD
from services import Services, override_service, FakeTimeProvider


class TestUser(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()

    def test_hasnt_posted(self):
        self.assertFalse(self.user.has_posted())

    def test_has_posted(self):
        self.post_comment(reply_content=create_content().id, user=self.user)
        self.assertTrue(self.user.has_posted())

    def test_hasnt_stickered(self):
        self.assertFalse(self.user.has_stickered())

    def test_has_stickered(self):
        result = self.api_post('/api/sticker/comment', {
            'type_id': str(1), 'comment_id': create_comment().id,
        }, user=self.user)
        self.assertTrue(self.user.has_stickered())

    def test_admins_can_moderate(self):
        admin = create_user(staff=True)
        self.assertTrue(admin.can_moderate_flagged)
        self.assertTrue(admin.can_bestof_all)
        self.assertNotEqual([], admin.can_moderate_visibility)

    def test_nonadmins_cant_moderate(self):
        admin = create_user()
        self.assertFalse(admin.can_moderate_flagged)
        self.assertFalse(admin.can_bestof_all)
        self.assertEqual([], admin.can_moderate_visibility)

    def test_session_migration(self):
        user = self.user
        c = self.get_client(user=user)
        c.get('/')

        session = c.session
        self.assertFalse(session.modified)
        session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
        session.save()
        self.assertTrue(session.modified)

        resp = c.get('/')


class TestUserClassMethods(CanvasTestCase):
    def test_users_over_one_day_old(self):
        with override_service('time', FakeTimeProvider):
            beginning_count = User.users_over_one_day_old().count()
            def assert_count(count, cutoff=None):
                self.assertEqual(beginning_count + count, User.users_over_one_day_old(cutoff=cutoff).count())
            assert_count(0)

            [create_user() for _ in xrange(2)]
            assert_count(0)

            Services.time.step(60*60*48)
            assert_count(2)
            create_user()
            assert_count(2)
            Services.time.step(60*60)
            assert_count(2)
            assert_count(0, cutoff=(Services.time.today() - datetime.timedelta(days=1)))

        
class TestUsernameValidation(CanvasTestCase):
    def test_uppercase_disallowed_chars(self):
        name = u'DİEL'
        self.assertTrue('Usernames can only contain' in User.validate_username(name))


class TestEmailValidation(CanvasTestCase):
    def test_basic(self):
        self.assertTrue(User.validate_email('foo@bar.com'))

    def test_malformed(self):
        for email in ['foo@bar', 'foobar.com', 'foo@bar@com']:
            self.assertFalse(User.validate_email(email))

    def test_unused(self):
        unused="this_email_is@unus.ed"
        self.assertTrue(User.email_is_unused(unused))
        user = create_user(email=unused)
        self.assertFalse(User.email_is_unused(unused))
        user.is_active = False
        user.save()
        self.assertTrue(User.email_is_unused(unused))

    def test_used(self):
        email = 'obama@whitehouse.gov'
        self.signup(email=email)
        dupe = create_user(email=email)
        self.assertFalse(User.email_is_unused(email))


class TestBasicAuth(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()

    def test_valid(self):
        auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic '
                + base64.b64encode('{}:{}'.format(self.user.username, PASSWORD)),
        }
        c = Client()
        response = c.get('/feed', **auth_headers)
        self.assertEqual(200, response.status_code)

