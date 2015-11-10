from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.test.client import Client

from apps.canvas_auth.models import User, AnonymousUser
from canvas.models import EmailUnsubscribe
from canvas.tests.tests_helpers import CanvasTestCase, NotOkay, create_content, create_user, create_group, redis, PASSWORD
from forms import EmailChangeForm, PasswordChangeForm, SubscriptionForm, SecureOnlyForm
from apps.user_settings.models import EmailConfirmation


class TestEmailConfirmation(CanvasTestCase):
    def setUp(self):
        super(TestEmailConfirmation, self).setUp()
        self.old_email = 'old@old.com'
        self.new_email = 'new@new.net'

    def test_change_and_confirm(self):
        user = create_user(email=self.old_email)

        confirmation = user.change_email(self.new_email)
        self.assertEqual(user.email, self.old_email)
        
        # Confirm it.
        confirmation = EmailConfirmation.objects.confirm_email(
            confirmation.confirmation_key)

        # Refresh the user object after confirming.
        user = User.objects.get(pk=user.pk)

        # Verify the change happened.
        self.assertNotEqual(confirmation, None)
        self.assertEqual(confirmation.user.pk, user.pk)
        self.assertEqual(confirmation.new_email, self.new_email)
        self.assertFalse(confirmation.key_expired())
        self.assertEqual(user.email, self.new_email)

    def test_key_changes(self):
        user = create_user(email=self.old_email)
        confirmation = EmailConfirmation.objects.create_confirmation(
            user, self.new_email)
        confirmation2 = EmailConfirmation.objects.create_confirmation(
            user, 'newer' + self.new_email)
        self.assertNotEqual(confirmation.confirmation_key,
                            confirmation2.confirmation_key)

    def test_key_generation(self):
        key = EmailConfirmation.objects._generate_key(self.old_email)
        key2 = EmailConfirmation.objects._generate_key(self.new_email)
        self.assertTrue(key is not None)
        self.assertTrue(key)
        self.assertNotEqual(key, key2)

    def test_confirmation_email_contents(self):
        user = create_user(email=self.old_email)
        confirmation = user.change_email(self.new_email)
        subject, msg = confirmation._generate_confirmation_email()

        # Make sure it has the right links with the confirmation key in the email body.
        self.assertTrue(confirmation.confirmation_key in msg)
        self.assertTrue(confirmation._activate_url() in msg)

    def test_confirm_page(self):
        user = create_user(email=self.old_email)
        confirmation = user.change_email(self.new_email)

        url = confirmation._activate_url()
        resp = self.get(url)
        self.assertTrue(resp.status_code in [302, 200])

        # Now make sure that visiting the page confirmed it.
        user = User.objects.get(pk=user.pk)
        self.assertEqual(user.email, self.new_email)
        
    def test_invalid_confirm_key(self):
        url = reverse('apps.user_settings.views.confirm_email', args=['foo'])
        resp = self.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(self.new_email in resp.content)
        self.assertTrue('invalid' in resp.content.lower())
        
    def test_form(self):
        user = create_user(email=self.old_email)
        form = EmailChangeForm(user=user, data={'email': self.new_email})

        if form.is_valid():
            form.save()

        # Refresh the user object.
        user = User.objects.get(pk=user.pk)
        
        # Check that a confirmation was sent.
        self.assertEqual(EmailConfirmation.objects.all().count(), 1)
        self.assertNotEqual(user.email, self.new_email)
    
    def test_unchanged_email_form(self):
        user = create_user(email=self.old_email)
        form = EmailChangeForm(user=user, data={'email': user.email})

        if form.is_valid():
            form.save()

        # Refresh the user object.
        user = User.objects.get(pk=user.pk)
        
        # Check that a confirmation was not sent, since the email hasn't been changed.
        self.assertEqual(EmailConfirmation.objects.all().count(), 0)

    def test_multiple_confirmations(self):
        user = create_user(email=self.old_email)
        confirmation = EmailConfirmation.objects.create_confirmation(
            user, 'first' + self.new_email)
        confirmation = EmailConfirmation.objects.create_confirmation(
            user, self.new_email)
        self.assertEqual(EmailConfirmation.objects.all().count(), 1)
        self.assertEqual(EmailConfirmation.objects.all()[0].new_email, self.new_email)

    def test_confirmation_cancellation(self):
        user = create_user(email=self.old_email)
        confirmation = EmailConfirmation.objects.create_confirmation(
            user, self.new_email)
        self.assertEqual(EmailConfirmation.objects.all().count(), 1)
        self.get(confirmation.cancellation_url(), user=user)
        self.assertEqual(EmailConfirmation.objects.all().count(), 0)
    
    def test_wrong_user_cancellation(self):
        user = create_user(email=self.old_email)
        user2 = create_user(email=self.old_email)
        confirmation = EmailConfirmation.objects.create_confirmation(
            user, self.new_email)
        self.assertEqual(EmailConfirmation.objects.all().count(), 1)
        try:
            resp = self.get(confirmation.cancellation_url(), user=user2)
        except NotOkay, e:
            resp = e.response
        else:
            raise Exception('Cancellation URL worked with the wrong user!')
        self.assertNotEqual(resp.status_code, 200)
        self.assertEqual(EmailConfirmation.objects.all().count(), 1)

    def test_send_confirmation(self):
        user = create_user(email=self.old_email)
        confirmation = EmailConfirmation.objects.create_confirmation(
            user, self.new_email)
        confirmation.send_confirmation()


class TestPasswordForm(CanvasTestCase):
    def test_pw_length(self):
        user = create_user()
        for pw, success in [('a', False,), ('a' * User.MINIMUM_PASSWORD_LENGTH, True,)]:
            form = PasswordChangeForm(user=user, data={
                'old_password': PASSWORD,
                'new_password1': pw,
                'new_password2': pw,
            })
            self.assertEqual(form.is_valid(), success)

    def test_pw_change(self):
        user = create_user()
        pw = 'new_pass1'
        form = PasswordChangeForm(user=user, data={
            'old_password': PASSWORD,
            'new_password1': pw,
            'new_password2': pw,
        })
        form.is_valid()
        form.save()
        self.assertTrue(form.password_changed())

    def test_pw_change_frontend_notification(self):
        user = create_user()
        pw = 'newpw1337'
        client = self.get_client(user=user)
        resp = self.post(reverse('apps.user_settings.views.user_settings'), data={
            'old_password': PASSWORD,
            'new_password1': pw,
            'new_password2': pw,
            'email': user.email,
        }, user=user, client=client)
        self.assertTrue(client.session.get('password_updated'))
        self.assertEqual(resp.status_code, 302)
        resp = self.get(reverse('apps.user_settings.views.user_settings'), client=client)
        self.assertContains(resp, 'password has been updated')


class TestSubscriptionForm(CanvasTestCase):
    def test_subscribe(self):
        email = 'fooo@baar.com'
        user = create_user(email=email)
        form = SubscriptionForm(user=user, data={'newsletter': 'on'})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(EmailUnsubscribe.objects.get_or_none(email=email), None)
        form = SubscriptionForm(user=user, data={})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertNotEqual(EmailUnsubscribe.objects.get_or_none(email=email), None)

    def test_change_email_and_unsubscribe_at_once(self):
        email = 'unsubscribe_test@what.com'
        new_email = 'new@what.com'
        user = create_user(email=email)
        # Unsubscribe while changing the address
        resp = self.post(reverse('apps.user_settings.views.user_settings'), data={
            'email': new_email,
        }, user=user)
        user=User.objects.all()[0]

        # Check that the old email is unsubscribed.
        EmailUnsubscribe.objects.get(email=email)
        
        # Confirm new email.
        confirmation = EmailConfirmation.objects.all()[0]
        EmailConfirmation.objects.confirm_email(confirmation.confirmation_key)

        # Check that the new email is now unsubscribed.
        EmailUnsubscribe.objects.get(email=new_email)
        

class TestDisableUser(CanvasTestCase):
    def test_disable(self):
        user = create_user()
        self.assertTrue(user.is_active)
        resp = self.post(reverse('apps.user_settings.views.disable_account'), data={}, user=user)

        # Refresh the user object and verify.
        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.is_active)
        self.assertRedirects(resp, '/')


class TestSecureOnly(CanvasTestCase):
    def test_secure_only_form(self):
        user = create_user()
        resp = HttpResponse()
        cookies = {}
        self.assertFalse(resp.cookies.get('secure_only', False))
        form = SecureOnlyForm(user, cookies, resp, data={'force_https': True})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(resp.cookies['secure_only'])
        form = SecureOnlyForm(user, {'secure_only': 'true'}, resp)
        self.assertTrue(form.fields['force_https'].initial)

    def test_secure_only_middleware(self):
        user = create_user()
        client = self.get_client(user=user)
        url = reverse('apps.user_settings.views.user_settings')

        # First set Force HTTPS
        resp = self.post(url, data={
            'email': user.email,
            'force_https': 'on',
        }, user=user, client=client)
        
        # Now try visiting a page without the cookie, and see that it gets set.
        client = self.get_client(user=user)
        resp = self.get('/', user=user, client=client)
        self.assertTrue(resp.cookies.get('secure_only'))

        # Unset it and check the redis value is gone.
        self.assertTrue(int(user.redis.user_kv.hget('secure_only') or 0))

        def do_form_post():
            return self.post(url, data={
                'email': user.email,
            }, user=user, client=client, https=True)

        resp = do_form_post()
        self.assertRedirectsNoFollow(resp, 'https://testserver:80' + url)

        # Mock SSL and re-POST
        client.defaults['wsgi.url_scheme'] = 'https'
        do_form_post()

        # Now check it had an effect.
        self.assertFalse(int(user.redis.user_kv.hget('secure_only') or 0))

    def test_secure_only_middleware_anonymously(self):
        self.assertStatus(200, '/', user=AnonymousUser())


