from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group, create_comment,
                                        create_staff)
from services import Services, override_service


class TestApi(CanvasTestCase):
    def test_no_completed_mobile_monsters(self):
        self.assertFalse(self.api_post('/api/monster/all_completed_mobile_monsters')['bottoms'])

