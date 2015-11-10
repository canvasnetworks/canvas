from canvas.tests.tests_helpers import CanvasTestCase

class TestTabs(CanvasTestCase):
    def test_hard_tabs_do_not_exist(self):
        """
        Currently only checks Python, CSS and JS files inside website/ for hard tabs.
        """
        EXTENSIONS = ['js', 'css', 'scss', 'py', 'html', 'conf']
        IGNORED_PATHS = ['*/static/CACHE', '*/static/lib', '*/website/debug_toolbar']

        website_dir = '/var/canvas/website'

        self.assertNoGrepMatches(r'\t', website_dir, ignored_paths=IGNORED_PATHS, extensions=EXTENSIONS)

