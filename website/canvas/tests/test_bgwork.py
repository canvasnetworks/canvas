import os
import time
import urllib2
import uuid

from configuration import Config
from canvas import util
from canvas.bgwork import WorkQueue
from canvas.tests.tests_helpers import CanvasTestCase, CB
from django.conf import settings


class TestBgWork(CanvasTestCase):
    def test_noop_doesnt_raise(self):
        bgwork = WorkQueue()
        bgwork.perform()

    def test_callable_gets_called(self):
        bgwork = WorkQueue()
        cb = CB()
        bgwork.defer(cb)
        bgwork.perform()

        self.assertEqual(1, cb.called)

    def test_performing_clears_deferred_jobs(self):
        bgwork = WorkQueue()
        cb = CB()
        bgwork.defer(cb)
        bgwork.perform()
        bgwork.perform()

        self.assertEqual(1, cb.called)

    def test_calling_clear_clears_deferred_jobs(self):
        bgwork = WorkQueue()
        cb = CB()
        bgwork.defer(cb)

        bgwork.clear()

        bgwork.perform()
        self.assertEqual(0, cb.called)

    def test_multiple_callables_get_called(self):
        bgwork = WorkQueue()
        cb1 = CB()
        cb2 = CB()

        bgwork.defer(cb1)
        bgwork.defer(cb2)

        bgwork.perform()

        self.assertEqual(1, cb1.called)
        self.assertEqual(1, cb2.called)

    def test_deferred_bgwork_can_create_more_deferred_bgwork(self):
        bgwork = WorkQueue()
        final_cb = CB()

        @bgwork.defer
        def create_more_work():
            bgwork.defer(final_cb)

        bgwork.perform()

        self.assertEqual(1, final_cb.called)

    def test_exceptions_are_isolated(self):
        bgwork = WorkQueue()

        def fail():
            raise Exception('Just testing bgwork exceptions - not a real error.')
        after_exception = CB()

        bgwork.defer(fail)
        bgwork.defer(after_exception)

        bgwork.perform()

        self.assertEqual(1, after_exception.called)

    def test_full_stack(self):
        path = Config['test_bgwork_path']
        if os.path.isfile(path):
            os.remove(path)

        # Post a fact.
        resp = urllib2.urlopen('http://{}/api/testing/test_bgwork'.format(settings.DOMAIN))

        # Look for the fact.
        TIMEOUT = 10 # s
        t = time.time()
        while True:
            time.sleep(.3)
            if os.path.isfile(Config['test_bgwork_path']):
                break
            if time.time() - t > TIMEOUT:
                raise Exception("test_bgwork flag file wasn't written.")

