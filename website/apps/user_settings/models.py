'''
Inspired by jtauber's django-email-confirmation.
(https://github.com/jtauber/django-email-confirmation/)
'''
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import models
from django.template.loader import render_to_string
from django.utils.hashcompat import sha_constructor
from random import random
from signals import user_email_changed
from django.conf import settings


MAX_KEY_LENGTH = 40
CONFIRMATION_EMAIL_ADDRESS = 'Canvas <emailconfirmation@example.com>'


class EmailConfirmationManager(models.Manager):
    def confirm_email(self, confirmation_key):
        '''
        Returns the (now deleted) confirmation object after updating the user's email.

        If the confirmation object with the given `confirmation_key` was not found,
        or if the confirmation is expired, then this returns None.
        '''
        try:
            confirmation = self.get(confirmation_key=confirmation_key)
        except self.model.DoesNotExist:
            return None

        if not confirmation.key_expired():
            user = confirmation.user
            old_email = user.email
            user.email = confirmation.new_email
            user.save()
            confirmation.delete()
            user_email_changed.send(sender=self, user=user,
                                    old_email=old_email, new_email=confirmation.new_email)
            return confirmation

    def _generate_key(self, email):
        salt = sha_constructor(str(random())).hexdigest()[:5]
        return sha_constructor(salt + email).hexdigest()[:MAX_KEY_LENGTH]

    def create_confirmation(self, user, new_email):
        '''
        Make sure to call `send_confirmation` on this object.

        If an EmailConfirmation object already exists for this user, this will delete it
        before creating a new one.
        '''
        existing = self.get_or_none(user=user)
        if existing:
            existing.delete()
        return self.create(
            user=user,
            new_email=new_email,
            confirmation_key=self._generate_key(new_email),
        )

    def delete_expired_confirmations(self):
        for confirmation in self.all():
            if confirmation.key_expired():
                confirmation.delete()


class EmailConfirmation(models.Model):
    '''
    Used for confirming changes to a user's email address.
    '''
    objects = EmailConfirmationManager()

    user = models.ForeignKey(User, unique=True)
    new_email = models.EmailField()
    sent = models.DateTimeField(blank=True, null=True)
    confirmation_key = models.CharField(max_length=MAX_KEY_LENGTH, unique=True)

    def __unicode__(self):
        return u'confirmation for {0}'.format(self.new_email)

    def _activate_url(self):
        path = reverse('apps.user_settings.views.confirm_email', args=[self.confirmation_key])
        return u'https://example.com' + path

    def cancellation_url(self):
        return reverse('apps.user_settings.views.cancel_email_confirmation', args=[self.confirmation_key])

    def _generate_changed_email(self):
        '''
        Returns a tuple of the email subject and message.
        '''
        context = {'user': self.user}
        subject = render_to_string('user_settings/email_changed_subject.django.txt', context)
        subject = ''.join(subject.splitlines()) # Remove superfluous linebreaks.
        message = render_to_string('user_settings/email_changed_message.django.txt', context)
        return (subject, message,)

    def _generate_confirmation_email(self):
        '''
        Returns a tuple of the email subject and message.
        '''
        context = {
            'user': self.user,
            'activate_url': self._activate_url(),
            'confirmation_key': self.confirmation_key,
        }

        subject = render_to_string('user_settings/email_confirmation_subject.django.txt', context)
        subject = ''.join(subject.splitlines()) # Remove superfluous linebreaks.
        message = render_to_string('user_settings/email_confirmation_message.django.txt', context)
        return (subject, message,)

    def send_confirmation(self):
        '''
        Sends a confirmation email that, once confirmed, will change the user's email.

        Also sends a notification to the old address that the account email has changed.
        '''
        for email, subject, message in list([(self.user.email,) + self._generate_changed_email(),
                                            (self.new_email,) + self._generate_confirmation_email()]):
            send_mail(subject, message, CONFIRMATION_EMAIL_ADDRESS, [email])

        self.sent = datetime.now()
        self.save()

    def key_expired(self):
        expiration_date = self.sent + timedelta(
            days=settings.EMAIL_CONFIRMATION_DAYS)
        return expiration_date <= datetime.now()

