import time

from django.conf import settings

from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff, create_quest, create_quest_comment,
                                           action_recipients)
from canvas.models import CommentSticker
from services import Services, override_service


class TestPushNotificationSubscriptions(CanvasTestCase):
    def test_unsubscribe(self):
        author = create_user()
        def recipients():
            actor = create_user()
            cmt = create_quest_comment(author=author)
            sticker = CommentSticker.objects.create(
                comment=cmt,
                timestamp=time.time(),
                type_id=settings.STAR_STICKER_TYPE_ID,
                user=actor,
                ip='0.0.0.0',
            )
            r = action_recipients('starred', actor, sticker, channel='PushNotificationChannel')
            return (r, cmt)

        r, cmt = recipients()
        self.assertIn(author.id, [u.id for u in r])

        self.api_post('/api/push_notifications/unsubscribe', {'notification_type': 'starred'}, user=author)
        r, cmt = recipients()
        self.assertNotIn(author.id, [u.id for u in r])

        self.api_post('/api/push_notifications/resubscribe', {'notification_type': 'starred'}, user=author)
        r, cmt = recipients()
        self.assertIn(author.id, [u.id for u in r])

