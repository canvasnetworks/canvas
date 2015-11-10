from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group, create_comment,
                                        create_staff)
from services import Services, override_service


class TestFeed(CanvasTestCase):
    def test_page_loads(self):
        self.assertStatus(200, '/feed', user=create_staff())

    def test_page_loads_with_feed_item(self):
        user = create_staff()
        other = create_user()
        user.follow(other)

        create_comment(author=other, reply_content=create_content())

        self.assertStatus(200, '/feed', user=user)


