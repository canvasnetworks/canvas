import datetime
import numbers
import string

from django.contrib.auth import models as django_models

from canvas.cache_patterns import CachedCall
from configuration import Config
from services import Services


class _BaseUserMixin(object):
    MINIMUM_PASSWORD_LENGTH = 5

    def __unicode__(self):
        return unicode(self.to_client())

    def to_client(self):
        return dict(username=self.username, id=self.id)

    def found_limit_reached(self):
        from canvas.models import Category
        return self.founded_groups.count() >= Category.FOUND_LIMIT


class User(django_models.User, _BaseUserMixin):
    class Meta:
        proxy = True

    @classmethod
    def users_over_one_day_old(cls, cutoff=None):
        """
        Returns a queryset of all users who signed up at least 24 hours ago.

        Optionally specify a `cutoff` datetime - the returned users will have signed up after this.
        """
        today = Services.time.today()
        yesterday = today - datetime.timedelta(days=1)
        users = cls.objects.filter(date_joined__lte=yesterday)
        if cutoff:
            users = users.filter(date_joined__gte=cutoff)
        return users

    @property
    def redis(self):
        from canvas.models import UserRedis
        return UserRedis(self.id, self.is_staff)

    @property
    def kv(self):
        if not self.id:
            raise Exception("User object doesn't have an id yet. "
                            "Make sure you .save() before accessing the kv store!")
        if not hasattr(self, '_kv'):
            from canvas.models import UserKV
            self._kv = UserKV(self)
        return self._kv

    def change_email(self, new_email):
        """
        This will send out a confirmation email to the user before it is actually changed.

        Returns the EmailConfirmation object that is created.
        """
        from apps.user_settings.models import EmailConfirmation
        confirmation = EmailConfirmation.objects.create_confirmation(self, new_email)
        confirmation.send_confirmation()
        return confirmation

    @classmethod
    def validate_password(cls, password):
        """ Returns whether the given password validates. """
        return len(password) >= cls.MINIMUM_PASSWORD_LENGTH

    @classmethod
    def validate_username(cls, username):
        """ Returns None if the username is valid and does not exist. """
        un = username.lower()

        if (un in Config['blocked_usernames']
                or any(fragment in un for fragment in Config['blocked_username_fragments'])
                or any(fragment in un for fragment in Config['autoflag_words'])):
            return "Sorry, this username is not allowed."

        if len(un) < 3:
            return "Username must be 3 or more characters."

        if len(un) > 16:
            return "Username must be 16 characters or less."

        alphabet = string.lowercase + string.uppercase + string.digits + '_'
        if not all(char in alphabet for char in username):
            return "Usernames can only contain letters, digits and underscores."
        if User.objects.filter(username__iexact=username):
            return "This username is taken :("

    @classmethod
    def validate_email(cls, email):
        """ Checks whether the email address appears to be well-formed. Very liberal. """
        return '@' in email and "." in email and len(email) >= 5 and all(ord(c) < 256 for c in email)

    @classmethod
    def email_is_unused(cls, email):
        try:
            cls.objects.get(email=email, is_active=True)
        except cls.DoesNotExist:
            return True
        except cls.MultipleObjectsReturned:
            return False
        else:
            return False

    def has_lab(self, lab_name):
        return bool(int(self.redis.user_kv.hget('labs:' + lab_name) or 0))

    def join_lab(self, lab_name):
        self.redis.user_kv.hset('labs:' + lab_name, 1)

    def has_posted(self):
        """ Whether this user has posted a comment or remix. """
        from canvas.models import Comment
        return self.comments.exists()

    def has_stickered(self):
        """ Whether this user has ever stickered a post. """
        from canvas.models import CommentSticker
        return self.commentsticker_set.exists()

    def follow(self, user_to_follow):
        if self == user_to_follow:
            raise ValueError("Can't follow self.")

        from canvas.notifications.actions import Actions
        Actions.followed_by_user(self, user_to_follow)

        self.redis.following.sadd(user_to_follow.id)
        user_to_follow.redis.followers.sadd(self.id)

    def unfollow(self, user_to_unfollow):
        self.redis.following.srem(user_to_unfollow.id)
        user_to_unfollow.redis.followers.srem(self.id)

    def followers(self):
        return User.objects.in_bulk_list(self.redis.followers.smembers())

    def follow_thread(self, comment):
        self.redis.followed_threads.sadd(comment.id)

    def unfollow_thread(self, comment):
        self.redis.followed_threads.srem(comment.id)

    def is_following(self, user):
        if not isinstance(user, numbers.Integral):
            user = user.id
        return user in self.redis.following

    @property
    def can_moderate_flagged(self):
        return self.is_staff

    @property
    def can_bestof_all(self):
        return self.is_staff

    @property
    def can_moderate_visibility(self):
        if not self.is_staff:
            return []
        else:
            from canvas.models import Visibility
            return dict(Visibility.choices).keys()

    @property
    def remix_invites(self):
        from apps.invite_remixer.models import RemixInviteArchive
        return RemixInviteArchive(self)

    def _avatar_details(self):
        avatar_details = {}
        if (self.userinfo is not None
            and self.userinfo.profile_image is not None
            and self.userinfo.profile_image.reply_content is not None):
            avatar_details = self.userinfo.profile_image.reply_content.details().to_client()
        return avatar_details

    #TODO
    @classmethod
    def avatar_by_username(cls, username):
        return CachedCall(
            "avatar:%s:details_v1" % username,
            lambda: cls.objects.get(username=username)._avatar_details(),
            24*60*60,
        )


class AnonymousUser(django_models.AnonymousUser, _BaseUserMixin):
    """
    Note that Django auth will still sometimes return its own AnonymousUser. So we have a middleware to patch
    request.user when anonymous.
    """
    class Meta:
        proxy = True

    def has_lab(self, lab_name):
        return False


@property
def logged_out_kv(self):
    from canvas.models import LoggedOutKV
    return LoggedOutKV()

AnonymousUser.kv = logged_out_kv

# Monkey-patch django
django_models.AnonymousUser.kv = logged_out_kv

