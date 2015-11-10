import unittest

import factlib

class UnescapeFixture(object):
    def testSimple(self):
        self.assertEqual("hello world", self.unescape("hello world"))

    def testEscapes(self):
        self.assertEqual("\x01\x11\x19", self.unescape(r"\x01\x11\x19"))
        
    def testMixed(self):
        self.assertEqual('"Hello world!"', self.unescape(r"\x22Hello world!\x22"))
        self.assertEqual('bl\nah', self.unescape(r"bl\x0Aah"))        
        
class PurePythonUnescape(UnescapeFixture, unittest.TestCase):
    def setUp(self):
        self.unescape = factlib._python_nginx_unescape

if factlib._factlib:
    # Don't run test if we're missing the dylib
    class CFactlibUnescape(UnescapeFixture, unittest.TestCase):
        def setUp(self):
            self.unescape = factlib._c_nginx_unescape
        
if __name__ == "__main__":
    unittest.main()
    