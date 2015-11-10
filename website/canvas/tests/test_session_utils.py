import datetime

from canvas.session_utils import store_ephemeral, get_ephemeral
from canvas.tests.tests_helpers import CanvasTestCase, FakeRequest


class TestSessionUtils(CanvasTestCase):
    def test_store_ephemeral(self):
        request = FakeRequest(None)
        request.session = {}
        
        key = "key"
        value = "value"
        
        ret = store_ephemeral(request, key, value)
        self.assertEqual(ret, value)
        self.assertEqual(request.session.get(key), value)
        
        self.assertEqual(len(request.session.keys()), 2)

        ret = get_ephemeral(request, key, ttl=datetime.timedelta(days=1))
        self.assertEqual(ret, value)
        
        ret = get_ephemeral(request, key, ttl=datetime.timedelta(days=-1))
        self.assertFalse(ret)
        self.assertFalse(request.session.get(key))

    def test_get_ephemeral_default_value(self):        
        request = FakeRequest(None)
        request.session = {}
        
        key = "key"
        value = "value"
        
        store_ephemeral(request, key, value)
        
        # Test default value
        default = 10
        ret = get_ephemeral(request, key, datetime.timedelta(days=-1), default)
        self.assertEqual(ret, default)

