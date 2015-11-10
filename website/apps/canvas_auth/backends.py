import base64

from django.contrib.auth.backends import ModelBackend

from apps.canvas_auth.models import User, AnonymousUser

def authenticate(username, password):
    try:
        user = User.objects.get(username=username)
        if user.check_password(password):
            return user
    except User.DoesNotExist:
        return None


class CanvasAuthBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        return None
        return authenticate(username, password)

    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()

