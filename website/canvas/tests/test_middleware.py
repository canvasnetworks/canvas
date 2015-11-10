import datetime
import urllib

from django.http import HttpRequest, HttpResponse

from apps.canvas_auth.models import AnonymousUser
from canvas import bgwork
from canvas.middleware import (RequestSetupMiddleware, DeferredWorkMiddleware, ExceptionLogger, ResponseGuard,
                               safe_middleware)
from canvas.models import Metrics
from canvas.tests.tests_helpers import CanvasTestCase, FakeRequest, create_user, create_staff, CB
from services import Services, FakeTimeProvider, with_override_service

class MockUrlopen(object):
    def read(self):
        return 'twisted pong'

class TestPingMiddleware(CanvasTestCase):
    def setUp(self):
        super(TestPingMiddleware, self).setUp()
        self.urlopen = urllib.urlopen
        urllib.urlopen = lambda path: MockUrlopen()
        
    def tearDown(self):
        super(TestPingMiddleware, self).tearDown()
        urllib.urlopen = self.urlopen
        
    def test_logged_out(self):
        path = '/ping'
        resp = self.get(path, user=AnonymousUser())
        self.assertStatus(200, path)
        self.assertEqual(resp.content, 'pong')

    def test_logged_in(self):
        path = '/ping'
        resp = self.get(path)
        self.assertStatus(200, path)
        self.assertEqual(resp.content, 'pong')

@safe_middleware
class RecordingMiddleware(object):
    def __init__(self):
        self.calls = []

    def process_request(self, request):
        self.calls.append("process_request")

    def process_response(self, request, response):
        self.calls.append("process_response")

class TestSafeMiddleware(CanvasTestCase):
    def test_prevents_process_response_without_corresponding_process_request(self):
        rm = RecordingMiddleware()
        rm.process_response(HttpRequest(), HttpResponse())
        self.assertEqual(rm.calls, [])

    def test_allows_process_response_if_corresponding_process_request(self):
        rm = RecordingMiddleware()
        request = HttpRequest()

        rm.process_request(request)
        rm.process_response(request, HttpResponse())

        self.assertEqual(rm.calls, ['process_request', 'process_response'])

    def test_prevents_process_response_if_process_request_raises_exception(self):
        calls = []

        class ExpectedException(Exception): pass

        @safe_middleware
        class NaughtyMiddleware(object):
            def process_request(self, request):
                raise ExpectedException()

            def process_response(self, request, response):
                calls.append("process_response")

        nm = NaughtyMiddleware()
        request = HttpRequest()

        with self.assertRaises(ExpectedException):
            nm.process_request(request)

        nm.process_response(request, HttpResponse())

        self.assertEqual(calls, [])

class TestResponseGuard(CanvasTestCase):
    def test_raise_TypeError_if_response_is_not_http_response(self):
        response = []
        mw = ResponseGuard()
        self.assertRaises(TypeError, lambda: mw.process_response(FakeRequest(None), response))
    
    def test_through_full_django_stack(self):
        self.assertRaises(TypeError, lambda: self.post("/staff/noop", user=create_staff()))
        
class TestRequestSetupMiddleware(CanvasTestCase):
    @with_override_service('time', FakeTimeProvider)
    def assertViewCount(self, request, response, count):
        now_dt = datetime.datetime.fromtimestamp(Services.time.time())

        bgwork.clear()
        RequestSetupMiddleware().process_request(request)
        RequestSetupMiddleware().process_response(request, response)
        
        view_previous = Metrics.view.daily_count(now_dt)
        bgwork.perform()
        view_current = Metrics.view.daily_count(now_dt)

        self.assertEqual(view_current - view_previous, count)

    def test_pageview_records_view_metric(self):
        self.assertViewCount(FakeRequest(create_user(), path="/user/foobar"), HttpResponse(status=200), 1)
        
    def test_api_does_not_record_view_metric(self):
        self.assertViewCount(FakeRequest(create_user(), path="/api/do_stuff"), HttpResponse(status=200), 0)

class TestDeferredWorkMiddleware(CanvasTestCase):
    def test_deferred_method_called_on_success(self):
        dwm = DeferredWorkMiddleware()
        request = HttpRequest()
        cb = CB()
        
        dwm.process_request(request)
        request.on_success.defer(cb)
        dwm.process_response(request, HttpResponse(status=200))
        
        self.assertEqual(cb.called, 0)
        
        bgwork.perform()
        
        self.assertEqual(cb.called, 1)

    def test_deferred_method_not_called_on_failure(self):
        dwm = DeferredWorkMiddleware()
        request = HttpRequest()
        cb = CB()

        dwm.process_request(request)
        request.on_success.defer(cb)
        dwm.process_response(request, HttpResponse(status=500))

        bgwork.perform()

        self.assertEqual(cb.called, 0)

