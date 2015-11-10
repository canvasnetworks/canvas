from django.conf import settings

from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff,
                                           create_quest, create_current_quest, create_quest_comment)
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.drawquest_auth.details_models import PrivateUserDetails
from canvas.exceptions import ServiceError, ValidationError
from services import Services, override_service

USERNAME = 'bob123456789z'
PASSWORD = 'doledoledole'


class TestApi(CanvasTestCase):
    def _signup(self, username, password, email):
        return self.api_post('/api/auth/signup', data={
            'username': username,
            'password': password,
            'email': email,
        })

    def _login(self, username, password, email=None):
        data = {
            'username': username,
            'password': password,
        }
        if email is not None:
            data['email'] = email
        return self.api_post('/api/auth/login', data=data)

    def test_login(self):
        self._signup(USERNAME, PASSWORD, 'bob.dole@hotmail.com')
        resp = self._login(USERNAME, PASSWORD)
        self.assertAPISuccess(resp)

    def test_login_wrong_password(self):
        self._signup(USERNAME, PASSWORD, 'bob.dole@hotmail.com')
        resp = self._login(USERNAME, 'what@what.com')
        self.assertAPIFailure(resp)

    def test_login_canvas_user_wrong_password(self):
        resp = self._login('ae', 'wrongpassword')
        self.assertAPIFailure(resp)

    #def test_login_canvas_user(self):
    #    resp = self._login('dq_migrate_test2', 'Password123$')
    #    print resp
    #    self.assertAPISuccess(resp)

    #def test_signup_canvas_user(self):
    #    resp = self._signup('dq_migrate_test2', 'Password123$', 'whatever@example.example')
    #    print resp
    #    self.assertAPISuccess(resp)

    def test_signup(self):
        resp = self._signup(USERNAME, PASSWORD, 'bob.dole@hotmail.com')
        self.assertTrue(resp['success'])
        user = User.objects.get(username=USERNAME)
        self.assertEqual(user.id, resp['user']['id'])

    def test_signup_with_blank_email(self):
        resp = self._signup(USERNAME, PASSWORD, '')
        self.assertFalse(resp['success'])

    def test_signup_with_blank_username(self):
        for username in ['', ' ', '     ']:
            resp = self._signup(username, PASSWORD, 'bob.dole@hotmail.com')
            self.assertFalse(resp['success'], "Username: " + username)

    def test_signup_for_login(self):
        for _ in range(2):
            resp = self._signup(USERNAME, PASSWORD, 'bob.dole@hotmail.com')
            self.assertTrue(resp['success'])

    def test_login_with_ae(self):
        resp = self._signup(USERNAME, PASSWORD, 'bob.dole@hotmail.com')
        user = User.objects.get(username=USERNAME)
        user.username = 'ae'
        user.save()
        user.details.force()
        resp = self._login('ae', PASSWORD)
        self.assertTrue(resp['success'])

    def test_username_available(self):
        def available(username):
            return self.api_post('/api/auth/username_available', data={'username': username})

        resp = available(USERNAME)
        self.assertTrue(resp['available'])

        user = create_user()
        resp = available(user.username)
        self.assertFalse(resp['available'])

    #def test_username_reserved(self):
    #    resp = self.api_post('/api/auth/username_available', data={'username': 'drawquest'})
    #    self.assertTrue(resp['available'])
    #    self.assertTrue(resp['reserved_from_canvas'])

    def test_email_is_unused(self):
        resp = self.api_post('/api/auth/email_is_unused', data={'email': 'foo@bar.com'})
        self.assertTrue(resp['email_is_unused'])

    def _change_password(self, old, new):
        self._signup(USERNAME, PASSWORD, 'whatever@huh.com')
        user = User.objects.get(username=USERNAME)
        return self.api_post('/api/user/change_profile', data={
            'old_password': old,
            'new_password': new,
        }, user=user, password=PASSWORD)

    def test_change_password(self):
        resp = self._change_password(PASSWORD, PASSWORD + '2')
        self.assertTrue(resp['success'])

    def test_change_password_with_wrong_old_password(self):
        resp = self._change_password(PASSWORD + '1', PASSWORD + '2')
        self.assertFalse(resp['success'])
        self.assertEqual(resp['error_type'], 'ValidationError')

    def test_deactivation(self):
        def cmts():
            return self.api_post('/api/quest_comments/user_comments', {'username': user.username})['comments']

        quest = create_current_quest()
        content = create_content()
        user = create_user()
        comment = self.api_post('/api/quest_comments/post', {
            'quest_id': quest.id,
            'content_id': content.id, 
        }, user=user)['comment']
        self.assertEqual(cmts()[0]['id'], comment['id'])

        self.api_post('/api/auth/actually_deactivate', user=user)
        self.assertFalse(cmts())

    def test_deactivation_via_email(self):
        resp = self.api_post('/api/auth/deactivate', user=create_user())
        self.assertAPISuccess(resp)

    def test_change_email(self):
        NEW_EMAIL = 'abcfds@sgsdtgdsf.com'
        self._signup(USERNAME, PASSWORD, 'whatever@huh.com')
        user = User.objects.get(username=USERNAME)
        self.api_post('/api/user/change_profile', data={
            'new_email': NEW_EMAIL,
        }, user=user, password=PASSWORD)
        user = User.objects.get(username=USERNAME)
        self.assertEqual(user.email, NEW_EMAIL)

    def test_private_user_details_has_email(self):
        email = 'whatever@huh.com'
        self._signup(USERNAME, PASSWORD, email)
        user = User.objects.get(username=USERNAME)
        user_details = PrivateUserDetails.from_id(user.id).to_client()
        print PrivateUserDetails.from_id(user.id).to_client()
        self.assertEqual(user_details['email'], email)

