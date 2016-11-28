import sys
from PyQt4.QtGui import QApplication, QIcon
from PyQt4.QtCore import QUrl, qInstallMsgHandler
from PyQt4.QtWebKit import QWebPage, QWebSettings

# comment this line to show QT warnings/errors:
qInstallMsgHandler(lambda *args: None)


class Render(QWebPage):
    def __init__(self, cb, dump_file):
        self.app = QApplication(sys.argv)
        self.app.setWindowIcon(QIcon('rift_scuttler_icon.png'))
        QWebPage.__init__(self)
        self.mainFrame().loadFinished.connect(self._loadFinished)
        self.cb = cb
        self.html_dump = dump_file
        self.settings().setAttribute(QWebSettings.AutoLoadImages, False)
        self.settings().setAttribute(QWebSettings.PluginsEnabled, False)

    def crawl(self, url):
        print('Downloading', url)
        self.mainFrame().load(QUrl(url))
        self.app.exec_()

    def _loadFinished(self, result):
        frame = self.mainFrame()
        url = str(frame.url().toString())

        html = frame.toHtml()
        self.cb(url, html)
        with open(self.html_dump, 'w', encoding='utf-8') as dump:
            dump.write(html)
        self.app.quit()


def callback(url, html):  # no idea if this function is even necessary but if it ain't broke...
    print('Got {0} bytes of HTML'.format(len(html)))

if __name__ == "__main__":
    the_url = sys.argv[1]
    the_dump_file = sys.argv[2]
    r = Render(callback, the_dump_file)
    r.crawl(the_url)

