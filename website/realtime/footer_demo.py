import sys

from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import *

qt_args = [sys.argv[0], '-display', ':0']
app = QApplication(qt_args, True)
web = QWebPage()

@web.loadFinished.connect
def loadFinished(success):
    if not success:
        print 'WHAT'
        sys.exit(1)

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
    image.save('output.png')
    sys.exit(0)

# Prepare the webview.
web.mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)
web.mainFrame().setScrollBarPolicy(Qt.Vertical,   Qt.ScrollBarAlwaysOff)
web.settings().setUserStyleSheetUrl(QUrl("data:text/css,html,body{overflow-y:hidden !important;}"))
web.settings().setAttribute(QWebSettings.PluginsEnabled, False)

# Do this thing.
web.mainFrame().load(QUrl('http://savnac.com/static/qt_footer/'))

sys.exit(app.exec_())

