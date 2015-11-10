from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from canvas import view_guards
from canvas.tests.tests_helpers import CanvasTestCase, FakeRequest, create_user, create_staff

class TestViewGuards(CanvasTestCase):
    def setUp(self):
        super(TestViewGuards, self).setUp()
        self.text = 'yeah ok'

        for guard_name in ['require_secure',
                           'require_staff',
                           'require_user', 
                           'require_POST']:
            guard = getattr(view_guards, guard_name)
            @guard
            def foo(request):
                return HttpResponse(self.text)
            setattr(self, guard_name, foo)

    def test_secure_without_https(self):
        request = FakeRequest()
        response = self.require_secure(request)
        self.assertEqual(response.status_code, 302)

    def test_secure_with_https(self):
        request = FakeRequest()
        request.META['HTTP_X_FORWARDED_PROTO'] = 'https'
        response = self.require_secure(request)
        self.assertEqual(response.content, self.text)

    def test_POST_with_GET(self):
        request = FakeRequest()
        response = self.require_POST(request)
        self.assertEqual(response.status_code, 405) # Not Allowed.

    def test_POST_with_POST(self):
        request = FakeRequest()
        request.method = 'POST'
        response = self.require_POST(request)
        self.assertEqual(response.status_code, 200)
        
    def test_user_with_anon(self):
        request = FakeRequest()
        self.assertRaises(PermissionDenied, lambda: self.require_user(request))

    def test_user_with_user(self):
        request = FakeRequest(user=create_user())
        response = self.require_user(request)
        self.assertEqual(response.status_code, 200)

    def test_staff_with_anon(self):
        request = FakeRequest()
        self.assertRaises(PermissionDenied, lambda: self.require_staff(request))

    def test_staff_with_nonstaff_user(self):
        request = FakeRequest(user=create_user())
        self.assertRaises(PermissionDenied, lambda: self.require_staff(request))

    def test_staff_with_staff(self):
        request = FakeRequest(user=create_staff())
        response = self.require_staff(request)
        self.assertEqual(response.status_code, 200)

