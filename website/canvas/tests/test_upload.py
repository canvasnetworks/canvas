from canvas import util
from canvas.tests.tests_helpers import CanvasTestCase

class TestUploads(CanvasTestCase):
    def _test_upload(self, filename):
        f = file("static/img/tests/" + filename, "rb")
        http_response = self.post('/api/upload', { "file": f })
        response = util.loads(http_response.content)
        self.assertTrue(response['success'])

    def test_upload_animated_gif(self):
        self._test_upload("animated.gif")

    def test_upload_opaque_jpeg(self):
        self._test_upload("opaque.jpg")

    def test_upload_transparent_png(self):
        self._test_upload("transparent.png")
