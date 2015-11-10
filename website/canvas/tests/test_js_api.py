from canvas.js_api import generate_api_javascript, get_api_js_filename
from canvas.tests.tests_helpers import CanvasTestCase

class TestJSApi(CanvasTestCase):
    def test_js_api_is_up_to_date(self):
        on_disk_api = file(get_api_js_filename(), 'r').read()
        expected_api = generate_api_javascript()

        print expected_api

        self.assertEqual(expected_api, on_disk_api, "Please run ./manage generate_js_api and then manually test any javascript changes you've made")
        
