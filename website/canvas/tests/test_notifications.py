import time

from apps.user_settings.forms import EmailChangeForm
from canvas import stickers, bgwork
from canvas.models import CommentSticker
from canvas.notifications import expander
from canvas.notifications.actions import Actions
from canvas.notifications.email_channel import EmailChannel
from canvas.notifications.notification_models import Notification
from canvas.tests import tests_helpers as utils
from canvas.tests.tests_helpers import CanvasTestCase, create_user, create_comment, create_content


class TestExpander(CanvasTestCase):
    def tearDown(self):
        # We disable performing the bgwork coz we do not want to send the email
        # notifiations just yet.
        pass
            
    def test_op_author_expander_notifies_author(self):
        author = utils.create_user()
        comment = utils.create_comment()
        comment.author = author
        comment.save()

        self.assertEqual(comment.thread.op.author, author)

        another_user = utils.create_user()

        pn = Actions.replied(another_user, comment)

        replied_expander = expander.get_expander(pn)()
        notifications = replied_expander.expand(pn)
        recipients = [n.recipient for n in notifications]

        #self.assertEqual(len(recipients), 1)
        self.assertIn(author, recipients)

    def test_expander_honors_unsubscribe_per_channel(self):
        author = utils.create_user()
        comment = utils.create_comment()
        comment.author = author
        comment.save()
        
        self.assertEqual(comment.thread.op.author, author)
        
        another_user = utils.create_user()
        
        pn = Actions.replied(another_user, comment)
        
        notifications = expander.expand(pn)
        self.assertTrue(notifications)

        notification = filter(lambda n: n.channel == 'EmailChannel', notifications)[0]
        self.assertEqual(author, notification.recipient)
        
        # Now, let the user unsubscribe to the reply action.
        author.kv.subscriptions.unsubscribe('thread_replied')
        pn = Actions.replied(another_user, comment)
        notifications = expander.expand(pn)
        recipients = [n.recipient for n in notifications if n.channel == 'EmailChannel']
        self.assertFalse(author in recipients)
    
    def test_newsletter_expander(self):
        user = create_user()
        pn = Actions.newsletter(user)
        
        notifications = expander.expand(pn)
        self.assertEqual(len(notifications), 1)
        notification = notifications.pop()
        self.assertEqual(notification.recipient, user)
    
    def test_newsletter_expander_for_user_with_no_email(self):
        user = create_user(email="")
        pn = Actions.newsletter(user)
        self.assertFalse(user.email)
        notifications = expander.expand(pn)
        self.assertEqual(len(notifications), 0)

    def test_digest_expander(self):
        user = create_user()
        pn = Actions.digest(user)
        
        notifications = expander.expand(pn)
        self.assertEqual(len(notifications), 1)
        notification = notifications.pop()
        self.assertEqual(notification.recipient, user)


class TestRepliedExpander(CanvasTestCase):
    def test_replied_to_own_thread_does_not_email_self(self):
        user = create_user()
        comment = create_comment(author=user)

        assert comment.author == user

        reply = create_comment(replied_comment=comment)
        assert comment == reply.replied_comment

        pn = Actions.replied(user, reply)
        notifications = expander.expand(pn)

        recipients = [n.recipient for n in notifications]
        self.assertNotIn(user, recipients)

    def test_replied_op_only_tells_author(self):
        author = create_user()
        content = create_content()
        op = create_comment(author=author, reply_content=content)

        user = create_user()
        reply = create_comment(replied_comment=op, author=user)

        self.assertEqual(reply.replied_comment, op)

        pn = Actions.replied(user, reply)

        notifications = expander.expand(pn)

        for n in notifications:
            print n
        self.assertEqual(len(filter(lambda n: n.channel == 'EmailChannel', notifications)), 1)
        notification = notifications.pop()

        # Note that it will be 'replied', not 'thread_replied'. The former is more specific.
        self.assertEqual(notification.action, 'replied')

    def test_replied_tells_author_and_op_author(self):
        # Some dude starts a thread
        author = create_user()
        content = create_content()
        op = create_comment(author=author, reply_content=content)

        # Another dude posts a reply
        guest_author = create_user()
        reply = create_comment(replied_comment=op, author=guest_author, parent_comment=op)
        
        self.assertEqual(reply.thread.op, op)
        
        # A third dude replies to the guest author
        guest_author_2 = create_user()
        reply_2 = create_comment(replied_comment=reply, author=guest_author_2, parent_comment=op)

        self.assertTrue(reply_2.thread.op.author, author)

        # Issue the action
        pn = Actions.replied(guest_author_2, reply_2)

        notifications = expander.expand(pn)
        print notifications
        # Now, we should tell both the OP author, and the guest author.
        notifications = filter(lambda n: n.channel == 'EmailChannel', notifications)
        self.assertEqual(len(notifications), 2)
        n1 = notifications[0]
        n2 = notifications[1]

        self.assertEqual(n1.action, 'replied')
        self.assertEqual(n1.recipient, guest_author)

        self.assertEqual(n2.action, 'thread_replied')
        self.assertEqual(n2.recipient, author)


class TestStickeredExpander(CanvasTestCase):
    def test_notifies_author(self):
        author = utils.create_user()
        comment = utils.create_comment()
        comment.author = author
        comment.save()
        another_user = utils.create_user()

        comment_sticker = CommentSticker(comment=comment,
                                         type_id=stickers.get("num1").type_id,
                                         timestamp=time.time(),
                                         ip="127.0.0.1",
                                         user=another_user)
        pn = Actions.stickered(another_user, comment_sticker)
        
        ex = expander.get_expander(pn)()
        recipients = ex.decide_recipients(pn)
        self.assertEqual(len(recipients), 1)
        self.assertIn(author, recipients)       


class TestDailyFreeStickers(CanvasTestCase):
    def test_user_receives(self):
        user = utils.create_user()
        pn = Actions.daily_free_stickers(user, 5)
        ex = expander.get_expander(pn)()
        recipients = ex.decide_recipients(pn)
        self.assertEqual(len(recipients), 1)
        self.assertIn(user, recipients)       


class TestUserNotificationSubscription(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()
        
    def test_unsubscribe_from_all(self):
        user = self.user

        self.assertTrue(user.kv.subscriptions.can_receive('remixed'))
        self.assertTrue(user.kv.subscriptions.can_receive('replied'))
        
        # Now unsubscribe from all
        user.kv.subscriptions.unsubscribe_from_all()

        self.assertFalse(user.kv.subscriptions.can_receive('remixed'))
        self.assertFalse(user.kv.subscriptions.can_receive('replied'))
    
    def test_unsubscribe_from_all_semantics(self):
        user = create_user()
        subs = user.kv.subscriptions
        assert subs.can_receive("ALL")
        assert subs.can_receive("ALL")
        
        subs.unsubscribe_from_all()
        assert not subs.can_receive("ALL")
        for a in EmailChannel.all_handled_actions():
            assert not subs.can_receive(a)
        
        subs.subscribe("ALL")
        assert subs.can_receive("ALL")
        assert subs.can_receive("ALL")
        for a in EmailChannel.all_handled_actions():
            assert subs.can_receive(a)
        
    def test_unsubscribe(self):
        user = self.user

        self.assertTrue(user.kv.subscriptions.can_receive('remixed'))
        self.assertTrue(user.kv.subscriptions.can_receive('replied'))
        
        user.kv.subscriptions.unsubscribe('remixed')
        self.assertFalse(user.kv.subscriptions.can_receive('remixed'))
        # Make sure it did not affect other subscriptions
        self.assertTrue(user.kv.subscriptions.can_receive('replied'))
    
    def test_subscribe(self):
        user = self.user
        subs = user.kv.subscriptions
        self.assertTrue(subs.can_receive('replied'))

        subs.unsubscribe('replied')
        self.assertFalse(subs.can_receive('replied'))
        
        subs.subscribe('replied')        
        print subs.hash.hgetall()
        self.assertTrue(subs.can_receive('replied'))
    

class TestNotificationModels(CanvasTestCase):
    def tearDown(self):
        # We disable performing the bgwork coz we do not want to send the email
        # notifiations just yet.
        bgwork.clear()
        
    def test_Notification_from_pn(self):
        pn = Actions.replied(create_user(), create_comment())
        notification = Notification.from_pending_notification(pn, create_user, "EmailChannel")
        assert notification.recipient
        for key in pn.data:
            self.assertEqual(getattr(notification, key), getattr(pn, key))
        assert pn.comment
        assert notification.comment

