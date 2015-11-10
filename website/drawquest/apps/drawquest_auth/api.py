from collections import defaultdict

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import IntegrityError

from canvas.exceptions import ServiceError, ValidationError
from canvas.models import UserInfo, FacebookUser, Visibility
from canvas.view_guards import require_user
from canvas.view_helpers import check_rate_limit
from drawquest import economy
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.details_models import PrivateUserDetails
from drawquest.apps.drawquest_auth.inactive import inactive_user_http_response
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.push_notifications.models import is_subscribed

urlpatterns = []
api = api_decorator(urlpatterns)

@api('username_available')
def username_available(request, username):
    if User.objects.filter(username__iexact=username):
        return {'available': False}

    return {
        'available': True,
        'reserved_from_canvas': User.is_username_reserved(username),
    }

@api('email_is_unused')
def email_is_unused(request, email):
    return {'email_is_unused': User.email_is_unused(email)}

@api('signup')
def signup(request, username, password, email, facebook_access_token=None):
    if check_rate_limit(request, username):
        raise ServiceError("Too many signup attempts. Wait a minute and try again.")

    try:
        return _login(request, password, username=username, email=email)
    except ValidationError:
        pass

    migrated_from_canvas_account = False
    errors = defaultdict(list)

    fb_user = None
    if facebook_access_token:
        fb_user = FacebookUser.create_from_access_token(facebook_access_token)

    def username_taken():
        # Ugly hack.
        for error in errors['username']:
            if 'taken' in error:
                return

        errors['username'].append("Sorry! That username is already taken.")

    if not password:
        errors['password'].append("Please enter a password.")

    if not User.validate_password(password):
        errors['password'].append("Sorry, your password is too short. "
                                  "Please use {} or more characters.".format(User.MINIMUM_PASSWORD_LENGTH))

    if not email:
        errors['email'].append("Please enter your email address.")
    elif not User.validate_email(email):
        errors['email'].append("Please enter a valid email address.")

    username_error = User.validate_username(username)
    if username_error:
        errors['username'].append(username_error)

    if not User.email_is_unused(email):
        errors['email'].append("Sorry! That email address is already being used for an account.")
    elif User.is_username_reserved(username):
        try:
            user = User.migrate_canvas_user(request, username, password, email=email)
        except IntegrityError:
            username_taken()
        except ValidationError:
            errors['username'] = ["""Sorry! This username is taken. Please pick a different username, """ +
                                  """or if you are "{}," enter your password to sign in.""".format(username)]
        else:
            migrated_from_canvas_account = True

    if errors:
        if fb_user:
            fb_user.delete()
        raise ValidationError(errors)

    if not migrated_from_canvas_account:
        try:
            user = User.objects.create_user(username, email, password)
        except IntegrityError:
            username_taken()
            raise ValidationError(errors)

        UserInfo.objects.create(user=user)

    if fb_user:
        fb_user.user = user
        fb_user.save()
        fb_user.notify_friends_of_signup(facebook_access_token)

        user.migrate_facebook_avatar(request, facebook_access_token)

    user = auth.authenticate(username=username, password=password)

    # auth.login starts a new session and copies the session data from the old one to the new one
    auth.login(request, user)

    return {
        'user': PrivateUserDetails.from_id(user.id).to_client(),
        'user_bio': user.userinfo.bio_text,
        'user_subscribed_to_starred': is_subscribed(user, 'starred'),
        'sessionid': request.session.session_key,
        'migrated_from_canvas_account': migrated_from_canvas_account,
    }

@api('login_with_facebook')
def login_with_facebook(request, facebook_access_token):
    try:
        fb_user = FacebookUser.get_from_access_token(facebook_access_token)
    except FacebookUser.DoesNotExist:
        raise PermissionDenied("No DrawQuest user exists for this Facebook account.")

    user = fb_user.user

    if not user.is_active:
        return inactive_user_http_response()

    # this is a total hack because we don't care to write a backend for the above authenticate method
    user.backend = settings.AUTHENTICATION_BACKENDS[0]

    auth.login(request, user)

    return {
        'user': PrivateUserDetails.from_id(user.id).to_client(),
        'user_bio': user.userinfo.bio_text,
        'user_subscribed_to_starred': is_subscribed(user, 'starred'),
        'sessionid': request.session.session_key,
    }

def _login(request, password, username=None, email=None):
    migrated_from_canvas_account = False

    def wrong_password():
        raise ValidationError({
            'password': "The password you entered is incorrect. "
                        "Please try again (make sure your caps lock is off)."
        })

    def wrong_username(username):
        raise ValidationError({
            'username': """The username you entered, "{}", doesn't exist. """.format(username) +
                        """Please try again, or enter the e-mail address you used to sign up."""
        })

    def get_username_from_email(email):
        if not email:
            wrong_username(email)

        try:
            return User.objects.get(email=email).username
        except User.DoesNotExist:
            wrong_username(email)

    if not username and not email:
        raise ValidationError({'username': "Username is required to sign in."})

    if not username:
        username = get_username_from_email(email)

    user = auth.authenticate(username=username, password=password)

    if user is None:
        # Maybe they entered an email into the username field?
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                #TODO This might be broken - should probably pass username.
                username = get_username_from_email(email)
                user = auth.authenticate(username=username, password=password)
            except ValidationError:
                # No such username exists.
                # See if it's a example.com account we need to migrate over.
                if User.is_username_reserved(username):
                    try:
                        user = User.migrate_canvas_user(request, username, password, email=email)
                    except ValidationError as e:
                        wrong_password()
                    else:
                        migrated_from_canvas_account = True

    if user is None:
        wrong_password()

    if not user.is_active:
        return inactive_user_http_response()

    auth.login(request, user)

    return {
        'user': PrivateUserDetails.from_id(user.id).to_client(),
        'user_bio': user.userinfo.bio_text,
        'user_subscribed_to_starred': is_subscribed(user, 'starred'),
        'sessionid': request.session.session_key,
        'migrated_from_canvas_account': migrated_from_canvas_account,
    }

@api('login')
def login(request, password, username=None, email=None):
    return _login(request, password, username=username, email=email)

@api('logout')
@require_user
def logout(request):
    user_id = request.user.id
    auth.logout(request)
    return {'user': PrivateUserDetails.from_id(user_id).to_client()}

@api('deactivate')
@require_user
def deactivate_user(request):
    """ Sends us an email. """
    subject = "User deactivation request ({})".format(request.user.username)
    admin_url = 'http://example.com/admin/api_console'
    message = "{}\n\n{}\n\n{}".format(request.user.username, request.user.email, admin_url)
    from_ = "support@example.com"
    to = "support@example.com"
    send_mail(subject, message, from_, [to])

@api('actually_deactivate')
@require_user
def actually_deactivate_user(request):
    for comment in request.user.comments.all():
        if comment.is_visible():
            comment.moderate_and_save(Visibility.UNPUBLISHED, request.user, undoing=True)

    request.user.is_active = False
    request.user.save()

