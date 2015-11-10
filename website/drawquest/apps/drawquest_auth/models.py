import httplib
import socket
import string
import urllib2

from cachecow.cache import invalidate_namespace
from django.conf import settings
from django.db import models
from django.db.models import signals
from facebook import GraphAPI, GraphAPIError

from canvas import json
from canvas.exceptions import ServiceError
from canvas.cache_patterns import CachedCall
from canvas.exceptions import ValidationError
from canvas.models import Content, UserInfo, FacebookUser, UserRedis
from canvas.upload import upload_from_url
from configuration import Config
from drawquest.activities import WelcomeActivity
from website.apps.canvas_auth.models import User as CanvasUser, AnonymousUser


_CANVAS_TIMEOUT = 6

def _canvas_api(endpoint, data):
    data = json.dumps(data)
    headers = {
        'Authorization': 'Basic ZHJhd3F1ZXN0OkRUZ3JnWTJT', # DTgrgY2S
        'Content-Type': 'application/json',
        'Content-Length': len(data),
        'X_REQUESTED_WITH': 'XMLHttpRequest',
        'ACCEPT': '*/*',
    }
    req = urllib2.Request('https://example.com/api' + endpoint, data, headers)
    f = urllib2.urlopen(req, timeout=_CANVAS_TIMEOUT)
    resp = json.loads(f.read())
    f.close()
    return resp


class User(CanvasUser):
    class Meta:
        proxy = True

    def __repr__(self):
        return '<drawquest user: {}>'.format(self.username)

    def delete(self):
        """
        DON'T USE THIS except for in extreme circumstances. Instead, just set is_active=False.
        Has leftover side-effects like not updating follower/following count. Only use this
        if you're prepared to fix it, or do some manual work afterward.
        """
        from drawquest.apps.playback.models import Playback, PlaybackData
        from drawquest.apps.quest_comments.models import QuestComment
        from drawquest.apps.stars.models import Unstar
        from drawquest.apps.iap.models import IapReceipt
        from apps.canvas_auth.models import User as CanvasUser

        self.activity_set.all().update(actor=None)

        Playback.objects.filter(viewer=self).delete()
        Unstar.objects.filter(user=self).delete()
        IapReceipt.objects.filter(purchaser=self).delete()

        for comment in self.comments.all():
            quest_comment = QuestComment.all_objects.get(pk=comment.pk)
            quest_comment.playbacks.all().delete()
            try:
                quest_comment.playback_data.delete()
            except PlaybackData.DoesNotExist:
                pass
            comment.delete()

        CanvasUser.objects.get(pk=self.pk).delete()

        invalidate_namespace('comments')

    @classmethod
    def validate_username(cls, username, skip_uniqueness_check=False):
        """ Returns None if the username is valid and does not exist. """
        un = username.lower()

        if (un in Config['blocked_usernames']
                or any(fragment in un for fragment in Config['blocked_username_fragments'])
                or any(fragment in un for fragment in Config['autoflag_words'])):
            return "Sorry, this username is not allowed."

        if not un:
            return "Please enter a username."
        elif len(un) < 3:
            return "Username must be 3 or more characters."
        elif len(un) > 16:
            return "Username must be 16 characters or less."

        alphabet = string.lowercase + string.uppercase + string.digits + '_'
        if not all(char in alphabet for char in username):
            return "Usernames can only contain letters, digits and underscores."

        if not skip_uniqueness_check:
            if cls.objects.filter(username__iexact=username):
                return "Sorry! This username is taken. Please pick a different username."

    @classmethod
    def is_username_reserved(cls, username):
        """ Checks if it's a reserved example.com username. """
        try:
            return _canvas_api('/user/actually_exists', {'username': username})['exists']
        except (urllib2.URLError, httplib.BadStatusLine, socket.timeout,):
            return False

    @classmethod
    def canvas_account_info(self, username):
        try:
            ret = _canvas_api('/user/info_for_drawquest_migration', {'username': username})
        except (urllib2.URLError, socket.timeout, httplib.BadStatusLine,):
            raise ServiceError("Couldn't migrate Canvas account to DrawQuest. Please try again later.")
        if not ret['success']:
            raise Exception("Couldn't migrate Canvas account to DrawQuest.")
        del ret['success']
        return ret

    @classmethod
    def check_canvas_account_password(self, username, password):
        try:
            ret = _canvas_api('/user/check_password', {'username': username, 'password': password})
        except (urllib2.URLError, socket.timeout, httplib.BadStatusLine,):
            raise ServiceError("Couldn't migrate Canvas account to DrawQuest. Please try again later.")
        if not ret['success']:
            raise Exception("Couldn't migrate Canvas account to DrawQuest.")
        del ret['success']
        return ret['correct']

    @classmethod
    def upload_avatar_from_url(cls, request, url):
        resp = upload_from_url(request, url)
        return Content.all_objects.get_or_none(id=resp['content']['id'])

    @classmethod
    def migrate_canvas_user(cls, request, canvas_username, canvas_password, email=None):
        """
        Will error out if the password isn't correct, with an (empty) ValidationError.

        `email` will override whatever email the example.com account had.

        May also raise an IntegrityError if the user already exists in drawquest.

        Returns the new `User` instance.
        """
        canvas_user = User.canvas_account_info(canvas_username)

        if email is None:
            email = canvas_user['email']
        elif not User.validate_email(email):
            raise ValidationError("Please enter a valid email address.")

        user = User.objects.create_user(canvas_username, email, canvas_password)

        # this is a total hack because we don't care to write a backend for this authenticate method
        user.backend = settings.AUTHENTICATION_BACKENDS[0]

        if User.check_canvas_account_password(canvas_username, canvas_password):
            avatar = None

            if canvas_user.get('profile_image_url'):
                avatar = User.upload_avatar_from_url(request, canvas_user['profile_image_url'])

            UserInfo.objects.create(user=user, bio_text=canvas_user['bio'], avatar=avatar)
        else:
            user.delete()
            raise ValidationError("Wrong password for Canvas account.")

        return user

    def migrate_facebook_avatar(self, request, facebook_access_token):
        fb = GraphAPI(facebook_access_token)
        avatar = fb.get_object('me/picture', type='large', redirect='false')['data']

        if avatar.get('is_silhouette'):
            return

        self.userinfo.avatar = User.upload_avatar_from_url(request, avatar.get('url'))
        self.userinfo.save()

    def _details(self):
        ret = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
        }

        if self.userinfo.avatar:
            ret['avatar_url'] = self.userinfo.avatar.details().get_absolute_url_for_image_type('archive')

        return ret

    @classmethod
    def details_by_id(cls, user_id, promoter=None):
        from drawquest.apps.drawquest_auth.details_models import UserDetails

        if promoter is None:
            promoter = UserDetails

        def inner_call():
            return cls.objects.get(id=user_id)._details()

        return CachedCall(
            'dq:user:{}:details_v6'.format(user_id),
            inner_call,
            24*60*60,
            promoter=promoter,
        )

    @property
    def details(self):
        return self.details_by_id(self.id)

    def to_client(self):
        return self.details().to_client()

    def violation_count(self):
        """ Number of times this user's drawings have been removed. """
        from canvas.models import Visibility
        from drawquest.apps.quest_comments.models import QuestComment

        return QuestComment.objects.filter(author=self, judged=True, visibility=Visibility.DISABLED).count()

def associate_facebook_account(user, facebook_access_token):
    try:
        user.facebookuser
        # User already has a FB account.
        #TODO recreate it instead of reusing the old one, since they could have logged into a different account.
        # But we only use FacebookUser for accounting purposes anyway, so it's low priority. It'll still get posted
        # to the correct timeline.
        return
    except FacebookUser.DoesNotExist:
        pass

    fb_user = FacebookUser.get_or_create_from_access_token(facebook_access_token)

    fb_user.user = user
    fb_user.save()

    fb_user.notify_friends_of_signup(facebook_access_token)

def user_post_save(sender, instance, created, **kwargs):
    if created:
        UserRedis(instance.id).activity_stream.push(WelcomeActivity())
signals.post_save.connect(user_post_save, sender=User)

