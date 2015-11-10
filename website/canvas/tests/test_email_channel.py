import datetime, time

from canvas import util, knobs
from canvas.models import Category
from canvas.notifications.actions import Actions
from canvas.notifications.beautiful_premailer.beautiful_premailer import transform
from canvas.notifications.email_channel import EmailChannel
from canvas.notifications.notification_models import Notification
from canvas.tests.tests_helpers import CanvasTestCase, create_user, create_comment, create_group, create_content
from configuration import Config
from services import Services, override_service, FakeMetrics, FakeExperimentPlacer, FakeTimeProvider


class TestEmailChannel(CanvasTestCase):
    def test_no_reply_notifications_for_muted_threads(self):
        author = create_user()
        comment = create_comment(author=author)

        action_func_list = [Actions.remixed,
                            Actions.replied,
                            Actions.thread_replied]

        # First make sure that the user can receive all possible "comment"
        # related notifications, like replied, remixed ... etc
        for func in action_func_list:
            pending_notification = func(author, comment)
            self.assertTrue(EmailChannel.enabled_for_recipient_action(pending_notification.action,
                                                             author,
                                                             pending_notification))
        # Now, mute the thread
        author.redis.mute_thread(comment)

        for func in action_func_list:
            pending_notification = func(author, comment)
            self.assertFalse(EmailChannel.enabled_for_recipient_action(pending_notification.action,
                                                             author,
                                                             pending_notification))

    def test_no_reply_notifications_for_inactive_users(self):
        author = create_user()

        comment = create_comment(author=author)

        action_func_list = [Actions.remixed,
                            Actions.replied,
                            Actions.thread_replied]

        # First make sure that the user can receive all possible "comment"
        # related notifications, like replied, remixed ... etc
        for func in action_func_list:
            pending_notification = func(author, comment)
            self.assertTrue(EmailChannel.enabled_for_recipient_action(pending_notification.action,
                                                             author,
                                                             pending_notification))

        author.is_active = False

        author.save()
        for func in action_func_list:
            pending_notification = func(author, comment)
            self.assertFalse(EmailChannel.enabled_for_recipient_action(pending_notification.action,
                                                             author,
                                                             pending_notification))


    def test_user_can_unsubscribe_through_header_link(self):
        user = create_user(email="foo@bar.com")
        comment = create_comment()
        comment2 = create_comment(author=user, replied_comment=comment)

        pn = Actions.replied(user, comment2)
        notification = Notification.from_pending_notification(pn, user, "EmailChannel")

        email_message = EmailChannel().make_message(notification, force=True)
        message = EmailChannel().make_email_backend_message(email_message)
        email_message.record_sent(notification.action)

        assert message.extra_headers
        unsubscribe_link = message.extra_headers.get("List-Unsubscribe")
        assert unsubscribe_link

        # Use should be able to receive notifications ...
        self.assertTrue(user.kv.subscriptions.can_receive('replied'))
        # Now, 'curl' the unsubscribe link
        self.assertStatus(200, unsubscribe_link)
        # Now, this action should be disabled in the notifications subscriptions.
        self.assertFalse(user.kv.subscriptions.can_receive('replied'))

    def test_24h_digest_email(self):
        user = create_user(email="foo@bar.com")
        pn = Actions.digest(user)
        notification = Notification.from_pending_notification(pn, user, "EmailChannel")

        email_message = EmailChannel().make_message(notification, force=True)
        message = EmailChannel().make_email_backend_message(email_message)
        email_message.record_sent(notification.action)

    def test_24h_digest_email_has_top_comments(self):
        COMMENT_COUNT = knobs.TWENTYFOUR_HOUR_EMAIL_COMMENT_COUNT
        GROUP = create_group(name=Config['featured_groups'][0])
        TODAY = datetime.datetime(year=2011, month=2, day=3)

        with override_service('time', FakeTimeProvider):
            #TODO refactor into tests_helpers and consolidate w/ other tests that do this (email_channel, models)
            # Make posts to show up in 'best'.
            Services.time.t = time.mktime(TODAY.timetuple())

            comments = [self.post_comment(reply_content=create_content().id, category=GROUP.name)
                        for _ in xrange(COMMENT_COUNT)]
            Services.time.step(60*60)
            # Sticker them.
            for cmt in comments:
                self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': cmt.id}, user=create_user())
                Services.time.step(60*60)
                cmt.update_score()

            def merge_scores():
                for category in [Category.ALL] + list(Category.objects.all()):
                    category.merge_top_scores()
            merge_scores()

            def get_email_message():
                user = create_user()
                pn = Actions.digest(user)
                notification = Notification.from_pending_notification(pn, user, "EmailChannel")

                return EmailChannel().make_message(notification, force=True)
            email_message = get_email_message()

            for cmt in comments:
                self.assertTrue(cmt.get_absolute_url() in email_message.body_html)

            # Wait a couple months, and make sure the comments disappear (so we're only showing top of the month,
            # not top of the year).
            Services.time.step(60*60*24*30*2)
            for cmt in comments:
                cmt.update_score()
            merge_scores()
            email_message = get_email_message()
            for cmt in comments:
                self.assertFalse(cmt.get_absolute_url() in email_message.body_html)

    def test_not_enabled_if_user_has_no_email(self):
        user = create_user(email="foobar@gmail.com")
        for action in EmailChannel.recipient_actions:
            assert EmailChannel.enabled_for_recipient_action(action, user)
        for action in EmailChannel.actor_actions:
            assert EmailChannel.enabled_for_actor_action(action, user)

        user.email = ""
        user.save()

        for action in EmailChannel.recipient_actions:
            assert not EmailChannel.enabled_for_recipient_action(action, user)
        for action in EmailChannel.actor_actions:
            assert not EmailChannel.enabled_for_actor_action(action, user)

    def test_delivering_email_records_email_sent_metric(self):
        with override_service('experiment_placer', FakeExperimentPlacer, kwargs={'email_notifications': 'experimental'}):
            user = create_user(email="foo@bar.com")

            comment = create_comment()
            comment2 = create_comment(author=user, replied_comment=comment)

            pn = Actions.replied(user, comment2)
            notification = Notification.from_pending_notification(pn, user, "EmailChannel")
            channel = EmailChannel()

            with override_service('metrics', FakeMetrics):
                channel.deliver(notification)
                self.assertEqual(1, len(Services.metrics.email_sent.records))


class TestPremailer(CanvasTestCase):
    def test_no_linebreak_added_to_links(self):
        html = """foo<a href="huh.bmp">bar</a>baz"""
        transformed = transform(html, base_url="http://bar.com")
        self.assertEqual("""foo<a href="http://bar.com/huh.bmp">bar</a>baz""", transformed)

    def test_comments(self):
        html = """foo<!-- bar -->baz"""
        transformed = transform(html, base_url="http://bar.com")
        self.assertEqual('foobaz', transformed)

    def test_doctype_is_not_comments(self):
        html = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">"""
        transformed = transform(html, base_url="http://bar.com")
        self.assertEqual(html, transformed)

