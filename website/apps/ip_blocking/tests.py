import datetime

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse

from apps.ip_blocking.models import IPBlock, is_ip_blocked
from apps.signup.views import signup
from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group, create_comment,
                                        create_staff, pretty_print_etree, FakeRequest)
from canvas.util import Now
from canvas.views import canvas_login
from services import Services, override_service, FakeTimeProvider


class TestModel(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()
        self.staff = create_staff()
        self.ip = '1.3.3.7'
        self.request = FakeRequest()
        self.request.META['REMOTE_ADDR'] = self.ip

    def test_banned(self):
        IPBlock.objects.create(
            ip=self.ip,
            moderator=self.staff,
            timestamp=Now(),
        )
        self.assertTrue(is_ip_blocked(self.request))

    def test_not_banned(self):
        IPBlock.objects.create(
            ip='.'.join(reversed(self.ip.split('.'))),
            moderator=self.staff,
            timestamp=Now(),
        )
        self.assertFalse(is_ip_blocked(self.request))


class TestRestrictedViews(CanvasTestCase):
    def after_setUp(self):
        self.ip = '13.33.33.7'
        IPBlock.objects.create(
            ip=self.ip,
            moderator=create_staff(),
            timestamp=Now(),
        )
        self.request = FakeRequest()
        self.request.META['REMOTE_ADDR'] = self.ip

    def _try_view(self, view):
        self.request.path = reverse(view)
        self.assertRaises(PermissionDenied, lambda: view(self.request))

    def test_signup(self):
        self._try_view(signup)

    def test_login(self):
        self._try_view(canvas_login)

