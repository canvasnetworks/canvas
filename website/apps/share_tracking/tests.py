from apps.canvas_auth.models import AnonymousUser
from apps.share_tracking.models import ShareTrackingUrl
from canvas.tests.tests_helpers import CanvasTestCase, create_user, create_content 
from services import with_override_service, FakeMetrics, Services


class TestSharing(CanvasTestCase):
    def test_browse_to_share_url_redirects(self):
        user = create_user()
        share_tracking_url = ShareTrackingUrl.create(user, url='/test_url/123', channel="testing")
        response = self.get(share_tracking_url.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/test_url/123')
        
    def test_create_share_url_via_api(self):
        user = create_user()
        result = self.api_post('/api/share/create', {'url': '/testing/999', 'channel': "testing"}, user=user)
        self.assertEqual(result['share_url'], '/s/1j')
        self.assertEqual(result['share_get_arg'], 's=1j')        

    def test_create_share_url_via_api_without_logged_in_user(self):
        user = AnonymousUser()
        result = self.api_post('/api/share/create', {'url': '/testing/999', 'channel': "testing"}, user=user)
        self.assertEqual(result['share_url'], '/s/1j')
        self.assertEqual(result['share_get_arg'], 's=1j')

    @with_override_service('metrics', FakeMetrics)
    def test_clickthrough_tracking_records_clickthrough_metric(self):
        self.assertEqual(0, len(Services.metrics.email_clickthrough.records))
        self.assertStatus(200, "/?ct=email")
        self.assertEqual(1, len(Services.metrics.email_clickthrough.records))

    @with_override_service('metrics', FakeMetrics)
    def test_clickthrough_tracking_records_metric_with_ct_prefixed_metadata(self):
        self.assertStatus(200, "/?ct=email&ct_foo=bar")
        request, metadata = Services.metrics.email_clickthrough.records[0]
        self.assertEqual("bar", metadata["ct_foo"])

    @with_override_service('metrics', FakeMetrics)
    def test_clickthrough_tracking_records_metric_with_ct_prefixed_metadata2(self):
        self.assertStatus(200, "/?ct=email&foo=bar")
        request, metadata = Services.metrics.email_clickthrough.records[0]
        self.assertFalse("foo" in metadata)

