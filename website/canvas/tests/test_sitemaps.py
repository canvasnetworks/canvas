# -*- coding: utf-8 -*-
from itertools import ifilter
import os

from canvas.models import CommentSticker
from canvas.tests.tests_helpers import CanvasTestCase, create_group

class TestSitemaps(CanvasTestCase):
    def test_smoketest(self):
        # Create a group with a unicode name.
        #group_name = u"محمود"
        #group = create_group(name=group_name)
        test = self.get('/sitemap.xml', {"foo": 1})
        print test
        assert "http://example" not in str(test)

