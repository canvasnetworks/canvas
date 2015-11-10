"""
We need to make sure that we don't branch on TESTING or PRODUCTION in our non-config code.
"""
from canvas.tests.tests_helpers import CanvasTestCase

class TestConfigBranching(CanvasTestCase):
    def after_setUp(self):
        self.WEBSITE_DIR = '/var/canvas/website'
        self.EXTENSIONS = ['html', 'py']
        self.IGNORED_PATHS = map(lambda p: '/var/canvas/website/' + p, [
            'canvas/management/commands/rethumbnail_images.py',
            'canvas/management/commands/update_footers.py',
            'nginx.py',
            'realtime/resources.py',
            'realtime/server.py',
            'realtime/footer.py',
            'settings.py',
            'settings_common.py',
            'settings_gunicorn.py',
            'settings_sentry_common.py',
            'settings_drawquest.py',
            'settings_sentry_gunicorn.py',
            'tests/test_config_branching.py',
            'apps/suggest/migrations/0001_ensure_followed_users.py',
            'canvas/knobs.py',
            'drawquest/apps/push_notifications/models.py',
        ])
        self.GREP_KWARGS = dict(ignored_paths=self.IGNORED_PATHS, extensions=self.EXTENSIONS)

    def test_PRODUCTION(self):
        self.assertNoGrepMatches('PRODUCTION', self.WEBSITE_DIR, **self.GREP_KWARGS)

    def test_TESTING(self):
        self.assertNoGrepMatches('TESTING', self.WEBSITE_DIR, **self.GREP_KWARGS)

