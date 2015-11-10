from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group, create_comment,
                                        create_staff)
from services import Services, override_service


class TestSimpleThing(CanvasTestCase):
    def test_basic_addition(self):
        """ Tests that 1 + 1 always equals 2. """
        self.failUnlessEqual(1 + 1, 2)

