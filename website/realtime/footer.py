from cStringIO import StringIO
import os
import platform
import subprocess

import Image
from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import *

from canvas import knobs, util
from canvas.redis_models import redis
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.util import base36encode
from website.canvas.models import Comment
from website.canvas.templatetags.helpers import TemplateComment
from django.conf import settings


class Footer(object):
    app = None

    def __init__(self, comment):
        self.comment = comment

    @classmethod
    def get_app(cls):
        qt_args = ['-display', ':0.0']
        return QCoreApplication.instance() or QApplication(qt_args, True)

    def render(self, web=None):
        """ Renders to a StringIO instance. """
        self.app = self.get_app()
        web = web or QWebPage()

        self._load_finished = False

        @web.loadFinished.connect
        def loadFinished(success):
            # Sometimes gets called several times for some reason. Ignore it.
            if self._load_finished:
                return

            if not success:
                self.app.quit()
                raise Exception("Comment footer was not rendered successfully. Comment ID:"
                                + str(self.comment.id))

            # Prepare renderer.
            web.setViewportSize(web.mainFrame().contentsSize())

            palette = web.palette()
            palette.setBrush(QPalette.Base, Qt.transparent)
            web.setPalette(palette)

            image = QImage(web.viewportSize(), QImage.Format_ARGB32)
            image.fill(Qt.transparent)

            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            painter.setRenderHint(QPainter.HighQualityAntialiasing, True)

            # Render it.
            web.mainFrame().render(painter)
            painter.end()
            self._image_data = _qimage_to_stringio(image)
            self._load_finished = True
            self.app.quit()

        # Prepare the webview.
        web.mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)
        web.mainFrame().setScrollBarPolicy(Qt.Vertical,   Qt.ScrollBarAlwaysOff)
        web.settings().setUserStyleSheetUrl(QUrl("data:text/css,html,body{overflow-y:hidden !important;}"))
        web.settings().setAttribute(QWebSettings.PluginsEnabled, False)

        # Do this thing.
        html = self.comment.footer.render_html()
        web.mainFrame().setHtml(html, QUrl('http://' + settings.DOMAIN))

        # Do it synchronously. (This isn't hot-spinning, it's just using the Qt event loop.)
        while not self._load_finished:
            self.app.processEvents()

        return self._image_data


def _qimage_to_stringio(img):
    buf = QBuffer()
    buf.open(QIODevice.ReadWrite)
    img.save(buf, 'PNG')
    strio = StringIO()
    strio.write(buf.data())
    buf.close()
    strio.seek(0)
    return strio


class CommentFooter(object):
    def __init__(self, comment):
        self.comment = comment

    def should_exist(self):
        """ Whether the comment should have a footer. """
        comment = self.comment.details()
        return comment.reply_content and not comment.is_animated()

    def call_update_in_new_process(self, enabled=not settings.TESTING):
        if enabled and self.comment.reply_content:
            for _ in xrange(knobs.FOOTER_UPDATE_ATTEMPTS):
                try:
                    subprocess.check_call(
                        ["env", "python", "/var/canvas/website/manage.py", "generate_footer", str(self.comment.id)],
                        env={'DISPLAY': ':0'}
                    )
                except subprocess.CalledProcessError:
                    continue
                break

    def update(self, fs=None, web=None):
        """
        Renders the footer image and saves it to the filesystem (i.e. S3 in production).

        `web` is an optional perf optimization.
        """
        from canvas.thumbnailer import generate_thumbnails
        data = self.render_image().getvalue()
        footer_meta = generate_thumbnails(data, fs=fs, image_type='footer', filename=self.get_path())

        # Update the Content details.
        content_key = self.comment.reply_content.details_key
        old_raw_meta = redis.get(content_key)
        if old_raw_meta:
            meta = util.loads(old_raw_meta)
        else:
            meta = {}
        meta.update(footer_meta)
        redis.set(content_key, util.dumps(meta))

        self.comment.reply_content.details.force()
        self.comment.details.force()

        return meta

    def render_image(self, web=None):
        return Footer(self.comment).render(web=web)

    def render_html(self):
        from apps.monster.models import MONSTER_GROUP

        comment = TemplateComment(self.comment.details())

        top_sticker = comment.top_sticker()
        if top_sticker is None:
            sticker = knobs.DEFAULT_FOOTER_STICKER
        else:
            sticker = top_sticker['name']

        if comment.category == MONSTER_GROUP and comment.parent_comment is not None:
            top = TemplateComment(self.comment.parent_comment.details())
            url = "/monster/{0}/{1}".format(base36encode(top.id), comment.id)
            return render_jinja_to_string('comment/stitched_monster.html', {
                'top': top,
                'bottom': comment,
                'sticker': sticker,
                'knobs': knobs,
                'url': url,
            })
        else:
            return render_jinja_to_string('comment/footer.html', {
                'comment': comment,
                'sticker': sticker,
                'knobs': knobs,
            })

    @classmethod
    def get_path_from_comment_details(self, comment_details):
        prefix = ''
        if comment_details.is_remix():
            prefix = 'remix_'
        return os.path.join('p', 'canvas_{0}{1}.png'.format(prefix, util.base36encode(comment_details.id)))

    def get_path(self):
        return CommentFooter.get_path_from_comment_details(self.comment.details())

    def get_absolute_url(self):
        return '/ugc/' + self.get_path()

