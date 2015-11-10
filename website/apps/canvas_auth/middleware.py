import base64
from functools import wraps

from django.contrib.auth.models import AnonymousUser as DjangoAnonymousUser, User as DjangoUser
from django.http import HttpResponse

from apps.canvas_auth.backends import authenticate
from apps.canvas_auth.http import HttpUnauthorizedException
from apps.canvas_auth.models import AnonymousUser, User
from django.conf import settings


class AnonymousUserMiddleware(object):
    """ Replaces request.user with our own AnonymousUser instead of Django's (if request.user is anonymous). """
    def process_request(self, request):
        if isinstance(request.user, DjangoAnonymousUser):
            request.user = AnonymousUser()


class SessionMigrationMiddleware(object):
    """
    Migrates the "_auth_backend_model" field in user sessions to the first backend listed in AUTHENTICATION_BACKENDS.
    Does nothing if AUTHENTICATION_BACKENDS is empty.

    Must come after "django.middleware.SessionMiddleware", and before
    "django.contrib.auth.middleware.AuthenticationMiddleware".
    """
    BACKEND_KEY = '_auth_user_backend'

    def process_request(self, request):
        if settings.AUTHENTICATION_BACKENDS:
            auth_backend = settings.AUTHENTICATION_BACKENDS[0]

            if request.session.get(self.BACKEND_KEY, auth_backend) != auth_backend:
                request.session['_old_auth_user_backend'] = request.session[self.BACKEND_KEY]
                request.session[self.BACKEND_KEY] = auth_backend

 
# http://djangosnippets.org/snippets/1720/
class HttpBasicAuthMiddleware(object):
    """ Should be after your regular authentication middleware. """
    def _unauthorized(self, request):
        raise HttpUnauthorizedException("Basic Realm='%s'" % settings.HTTP_AUTH_REALM)

    def process_request(self, request):
        # At this point, the user is either not logged in, or must log in using
        # http auth.  If they have a header that indicates a login attempt, then
        # use this to try to login.
        if 'HTTP_AUTHORIZATION' not in request.META:
            return

        try:
            (auth_type, data) = request.META['HTTP_AUTHORIZATION'].split()
            if auth_type.lower() != 'basic':
                return self._unauthorized(request)
            user_pass = base64.b64decode(data)
        except ValueError:
            return self._unauthorized(request)

        bits = user_pass.split(':')

        if len(bits) != 2:
            self._unauthorized(request)

        user = authenticate(bits[0], bits[1])

        if user is None:
            return self._unauthorized(request)

        request.user = user

