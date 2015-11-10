import os
from tempfile import TemporaryFile

from django.core.files.temp import gettempdir

from canvas import stickers
from canvas.tests.tests_helpers import CanvasTestCase, create_comment, create_content, create_user
from canvas.thumbnailer import Thumbnailer
from realtime.resources import LocalDiskFS


class TestThumbnailer(CanvasTestCase):
    def setUp(self):
        super(TestThumbnailer, self).setUp()
        dir_ = os.path.abspath(gettempdir())
        def mkdir(name):
            try:
                os.mkdir(os.path.join(dir_, name))
            except:
                pass
        mkdir('processed')
        mkdir('original')
        mkdir('p')

        self.fs = LocalDiskFS(dir_).operation()

    def test_thumbnailer(self):
        data = open("/var/canvas/website/static/img/stickers/lol.png", "r").read()
        t = Thumbnailer(self.fs)
        stored_data = t.store(data)

        print stored_data.keys()
        for key in Thumbnailer.META:
            self.assertIn(key, stored_data)

    def test_footer(self):
        cmt = create_comment(reply_content=create_content())
        cmt.footer.update(fs=self.fs)


class TestFooter(CanvasTestCase):
    def after_setUp(self):
        self.comment = self.post_comment(reply_content=create_content().id, user=create_user())

    def _html(self):
        return self.comment.footer.render_html()

    def test_sticker(self):
        html = self._html()
        self.assertFalse(self.css_select(html, '.frowny'))

        stick = stickers.get('frowny')
        result = self.api_post('/api/sticker/comment', {
            'type_id': str(stick.type_id),
            'comment_id': self.comment.id,
        })
        html = self._html()
        self.assertTrue(self.css_select(html, '.frowny'))

    def test_smiley_default(self):
        html = self._html()
        self.assertTrue(self.css_select(html, '.smiley'))

