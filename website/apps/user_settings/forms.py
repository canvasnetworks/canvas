from django import forms
from django.forms import ModelForm, Form
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm

from apps.canvas_auth.models import User
from canvas.models import subscribe_newsletter, unsubscribe_newsletter


class EmailChangeForm(Form):
    email = forms.EmailField()

    def __init__(self, user=None, *args, **kwargs):
        super(EmailChangeForm, self).__init__(*args, **kwargs)
        self.old_email = user.email
        self.user = user
        self.fields['email'].initial = user.email

    def save(self):
        '''
        Does nothing if this is the same email already associated with the user's account.

        Returns the EmailConfirmation object, or the User object if the password was not changed.
        '''
        user = self.user
        new_email = self.cleaned_data['email']
        if self.old_email != new_email:
            if not hasattr(user, 'change_email'):
                user = User.objects.get(pk=user.pk)
            return user.change_email(new_email)
        return user


class PasswordChangeForm(DjangoPasswordChangeForm):
    '''
    Special version of the standard password change form, which doesn't raise errors if it's empty.
    '''
    _attrs = {'autocomplete': 'off'}
    old_password  = forms.CharField(label='Old password',
                                    widget=forms.PasswordInput(render_value=False, attrs=_attrs))
    new_password1 = forms.CharField(label='New password',
                                    widget=forms.PasswordInput(render_value=False, attrs=_attrs))
    new_password2 = forms.CharField(label='New password confirmation',
                                    widget=forms.PasswordInput(render_value=False, attrs=_attrs))

    def __init__(self, user, *args, **kwargs):
        super(PasswordChangeForm, self).__init__(user, *args, **kwargs)
        self.old_pw_hash = user.password

    def _is_empty(self):
        return all(not val for key, val in self.cleaned_data.iteritems())

    def clean_new_password2(self):
        new_password2 = super(PasswordChangeForm, self).clean_new_password2()
        if not User.validate_password(new_password2):
            raise forms.ValidationError(
                    'Sorry, your password is too short. It must be at least {0} characters long.'.format(
                    User.MINIMUM_PASSWORD_LENGTH))
        return new_password2

    def clean(self):
        # Only call the parent if the form is not empty.
        if self._is_empty():
            self._errors = []
        else:
            super(PasswordChangeForm, self).clean()
        return self.cleaned_data

    def save(self, *args, **kwargs):
        # Only try saving if the form is not empty.
        if not self._is_empty():
            return super(PasswordChangeForm, self).save(*args, **kwargs)

    def password_changed(self):
        return self.user.password != self.old_pw_hash


class SubscriptionForm(Form):
    newsletter = forms.BooleanField(required=False)

    def __init__(self, user=None, *args, **kwargs):
        super(SubscriptionForm, self).__init__(*args, **kwargs)
        self.user = user

    def save(self, *args, **kwargs):
        if self.cleaned_data['newsletter']:
            subscribe_newsletter(self.user.email)
        else:
            unsubscribe_newsletter(self.user.email)


class BrowsingSettingsForm(Form):
    root_is_following = forms.BooleanField(required=False)
    hide_reposts = forms.BooleanField(required=False)
    hide_userpage_from_google = forms.BooleanField(required=False)
    LABS = ['root_is_following', 'hide_reposts', 'hide_userpage_from_google']

    def __init__(self, user, *args, **kwargs):
        super(BrowsingSettingsForm, self).__init__(*args, **kwargs)
        self.user = user
        for lab in self.LABS:
            self.fields[lab].initial = user.kv.get('labs:' + lab)

    def save(self, *args, **kwargs):
        for lab in self.LABS:
            self.user.kv.set('labs:' + lab, self.cleaned_data[lab])


class ConnectionsForm(Form):
    enable_timeline = forms.BooleanField(required=False)

    def __init__(self, user=None, *args, **kwargs):
        super(ConnectionsForm, self).__init__(*args, **kwargs)
        self.user = user
        self.fields['enable_timeline'].initial = self.user.userinfo.enable_timeline

    def save(self, *args, **kwargs):
        if self.cleaned_data['enable_timeline']:
            self.user.userinfo.enable_timeline = True
        else:
            self.user.userinfo.enable_timeline = False
        self.user.userinfo.save()


class SecureOnlyForm(Form):
    force_https = forms.BooleanField(required=False)

    def __init__(self, user, cookies, http_response=None, *args, **kwargs):
        '''
        `cookies` should be `request.COOKIES`.

        When this form is saved, it will modify the given `http_response` object.
        '''
        super(SecureOnlyForm, self).__init__(*args, **kwargs)
        self.user = user
        self.http_response = http_response

        self.fields['force_https'].initial = bool(int(self.user.redis.user_kv.hget('secure_only') or 0))

    def save(self):
        if self.cleaned_data['force_https']:
            self.user.kv.secure_only.set(True)
            self.http_response.set_cookie('secure_only', 'true')
        else:
            self.user.kv.secure_only.set(False)
            self.http_response.delete_cookie('secure_only')

