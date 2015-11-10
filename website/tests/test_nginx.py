from copy import copy
import os
import re
import tempfile
import urllib2

from canvas.tests.tests_helpers import CanvasTestCase
import nginx
from django.conf import settings

class TestNginx(CanvasTestCase):
    def assert200(self, url):
        self.assertEqual(200, urllib2.urlopen(url).code)

    def test_nginx_accepts_ping_from_domain(self):
        print "http://{}:{}/ping".format(settings.DOMAIN, settings.SELF_PORT)
        self.assert200("http://{}:{}/ping".format(settings.DOMAIN, settings.SELF_PORT))

    # Not relevant and broken for DrawQuest, so disabled for now.
    #def test_nginx_accepts_ping_from_localhost(self):
    #    self.assert200("http://localhost:%s/ping" % settings.SELF_PORT)

    #def test_nginx_accepts_ping_from_ip(self):
    #    self.assert200("http://127.0.0.1:%s/ping" % settings.SELF_PORT)

class TestNginxConf(CanvasTestCase):
    def after_setUp(self):
        self._paths = (nginx.WEBSITE_PATH, nginx.TEMPLATE_PATH)
        nginx.TEMPLATE_PATH = copy(nginx.WEBSITE_PATH)
        nginx.WEBSITE_PATH = tempfile.mkdtemp()
        os.mkdir(nginx.WEBSITE_PATH + '/run')
        class FakeOptions(object):
            project = settings.PROJECT
            factlog = True
        nginx.options = FakeOptions()

    def before_tearDown(self):
        nginx.WEBSITE_PATH, nginx.TEMPLATE_PATH = self._paths

    def _assert_conf(self, conf_name, context=None, server_name=None):
        nginx.write_nginx_conf(conf_name, context=context)
        with open(nginx.WEBSITE_PATH + '/{0}.conf'.format(conf_name)) as f:
            conf = f.read()
        self.assertTrue(conf)
        if server_name:
            # I have to put the '{' in like this because Vim screws up if I write it in the literal. Thanks, Vim.
            regex = r'\s*upstream {0}_server {1}\s*server {2}.*'.format(server_name,
                                                                        '\{',
                                                                        re.escape(context[server_name + '_host']))
            self.assertTrue(re.search(regex, conf))

    def test_servers(self):
        ctx = nginx.get_nginx_context()
        self._assert_conf('nginx', context=ctx, server_name='twisted')

    def test_factlog(self):
        self._assert_conf('nginx-factlog')

