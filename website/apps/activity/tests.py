from django.core.urlresolvers import reverse
from django.contrib.sessions.models import Session

from apps.activity.redis_models import ActivityStream, StickerActivity, BaseActivity, ThreadReplyActivity
from canvas import util, stickers, bgwork
from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_user,
                                        create_group, create_comment, pretty_print_etree)
from canvas.knobs import STICKER_SCHEDULE, STICKER_REWARDS


class ExampleActivity(BaseActivity):
    TYPE = '__example__'


class TestModels(CanvasTestCase):
    def test_activity_stream(self):
        user = create_user()
        stream = ActivityStream(user.id, activity_types={ExampleActivity.TYPE: ExampleActivity})
        self.assertEqual(0, len(list(stream)))

        activity = ExampleActivity({'foo': 'bar'}, actor=user)
        stream.push(activity)
        activity = list(stream)[0]
        self.assertEqual(activity.type, '__example__')

    def test_actor(self):
        author = create_user()
        op = create_comment(author=author, reply_content=create_content())

        replier = create_user()
        reply = create_comment(replied_comment=op, author=replier)

        activity = ThreadReplyActivity.from_comment(replier, reply)
        self.assertEqual(activity.actor['id'], replier.id)

    def test_anonymous_actor(self):
        author = create_user()
        op = create_comment(author=author, reply_content=create_content())

        for anon in [True, False]:
            replier = create_user()
            reply = create_comment(replied_comment=op, author=replier, anonymous=anon)

            activity = ThreadReplyActivity.from_comment(replier, reply)
            self.assertEqual(activity.is_actor_anonymous, anon)


class TestViews(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()
        self._epic_sticker = stickers.get('nyancat')

    def before_tearDown(self):
        self.user = create_user()

    def _sticker(self, user, sticker_type_id=1, sender=None):
        comment = create_comment(author=user)
        sender = sender or create_user()
        result = self.api_post('/api/sticker/comment',
                               {'type_id': str(sticker_type_id), 'comment_id': comment.id}, user=sender)

    def _give_epic_sticker(self):
        sender = create_user()
        sender.kv.stickers[self._epic_sticker.type_id].increment(1)
        self._sticker(self.user, sticker_type_id=self._epic_sticker.type_id, sender=sender)

        self.user.kv.update()
        for notification in self.user.redis.notifications.get():
            self.api_post('/api/notification/acknowledge', {'nkey': notification['nkey']}, user=self.user)

    def _get_stream(self):
        return '<html><body>' + self.api_post('/api/activity/activity_stream', user=self.user) + '</body></html>'

    def test_sticker(self):
        resp = self._get_stream()
        self.assertNumCssMatches(0, resp, '.sticker_activity')

        self._sticker(self.user)
        resp = self._get_stream()
        self.assertNumCssMatches(1, resp, '.sticker_activity')

    def test_many_stickers(self):
        resp = self._get_stream()
        self.assertNumCssMatches(0, resp, '.sticker_activity')

        COUNT = 5
        for _ in xrange(5):
            self._sticker(self.user)
        resp = self._get_stream()
        self.assertNumCssMatches(COUNT, resp, '.sticker_activity')

    def test_sticker_thumbnail(self):
        resp = self._get_stream()
        self.assertNumCssMatches(0, resp, '.thumbnail')

        self._sticker(self.user)
        resp = self._get_stream()
        self.assertNumCssMatches(1, resp, '.thumbnail')

    def test_epic_sticker(self):
        resp = self._get_stream()
        self.assertNumCssMatches(0, resp, '.epic_sticker_activity')

        self._give_epic_sticker()

        resp = self._get_stream()
        self.assertNumCssMatches(1, resp, '.epic_sticker_activity')

    def test_markup_is_unescaped(self):
        self._sticker(self.user)
        resp = self._get_stream()
        self.assertNumCssMatches(1, resp, '.sticker_container')

    def test_level_up(self):
        resp = self._get_stream()
        self.assertNumCssMatches(0, resp, '.level_up_activity')

        self.user.redis.user_kv.hincrby('sticker_inbox', STICKER_SCHEDULE[0])
        self.api_post('/api/user/level_up', {}, user=self.user)

        resp = self._get_stream()
        self.assertNumCssMatches(1, resp, '.level_up_activity')
        (message,) = self.css_select(resp, '.level_up_activity')
        self.assertTrue(str(STICKER_REWARDS[0]) in message.xpath('string()'))

    def test_remix(self):
        resp = self._get_stream()
        self.assertNumCssMatches(0, resp, '.remix_activity')

        original_content = create_content()
        remix_content = create_content()
        remix_content.remix_of = original_content
        remix_content.save()

        op = self.post_comment(reply_content=create_content().id)
        original = self.post_comment(parent_comment=op.id, reply_content=original_content.id, user=self.user)
        remixer = create_user()
        remix = self.post_comment(parent_comment=op.id, reply_content=remix_content.id)

        resp = self._get_stream()
        self.assertNumCssMatches(1, resp, '.remix_activity')

    def test_reply_to_your_thread(self):
        def check(count):
            resp = self._get_stream()
            self.assertNumCssMatches(count, resp, '.thread_reply_activity')

        check(0)

        op = self.post_comment(reply_content=create_content().id, user=self.user)
        check(0)

        for n in xrange(1, 2):
            reply = self.post_comment(parent_comment=op.id, reply_content=create_content().id)
            check(n)

    def test_at_reply(self):
        def check(count):
            resp = self._get_stream()
            self.assertNumCssMatches(count, resp, '.reply_activity')

        check(0)

        op = self.post_comment(reply_content=create_content().id, user=self.user)
        check(0)

        reply = self.post_comment(parent_comment=op.id, reply_content=create_content().id)
        check(0)

        at_reply = self.post_comment(parent_comment=op.id, reply_content=create_content().id, replied_comment=op.id)
        check(1)

