from contextlib import contextmanager

from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

_dispatch = None

@contextmanager
def override_send_messages(fun):
    global _dispatch
    old_email_backend = settings.EMAIL_BACKEND
    settings.EMAIL_BACKEND = 'canvas.mocks.MockEmailBackend'
    old_dispatch = _dispatch
    _dispatch = fun
    try:
        yield
    finally:
        _dispatch = old_dispatch
        settings.EMAIL_BACKEND = old_email_backend


class MockEmailBackend(BaseEmailBackend):
                
    def send_messages(self, messages):
        if _dispatch:
            _dispatch(messages)
