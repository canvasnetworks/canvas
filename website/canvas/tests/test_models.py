# -*- coding: utf-8 -*-
import datetime, time

from boto.exception import BotoServerError
from django.core.exceptions import PermissionDenied
from django.http import Http404

from apps.canvas_auth.models import User, AnonymousUser
from canvas.browse import (get_browse_tiles, get_user_stickered, TileDetails, LastReplyTileDetails,
                           get_front_comments, Navigation, get_user_data)
from canvas.management.commands import send_24h_email
from canvas.models import (Comment, Visibility, Category, DisabledCategory, FollowCategory, CommentSticker,
                           YouTubeContent, ExternalContent, send_email,
                           WelcomeEmailRecipient, flagged_comments, Content)
from canvas.details_models import CommentDetails
from canvas.tests.tests_helpers import (create_comment, create_content, create_group, create_user, CanvasTestCase,
                                        FakeRequest, create_staff, create_rich_user)
from canvas import api, stickers, mocks, util
from canvas.notifications.email_channel import EmailChannel
from configuration import Config
from services import Services, override_service, FakeTimeProvider, FakeMetrics, FakeExperimentPlacer


class TestCommentStickers(CanvasTestCase):
    def test_sticker_from_user(self):
        user = create_user()
        comment = create_comment()
        self.assertFalse(CommentSticker.get_sticker_from_user(comment.id, user))

        self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': comment.id}, user=user)
        self.assertTrue(CommentSticker.get_sticker_from_user(comment.id, user))


class TestCategory(CanvasTestCase):
    def test_everything_url(self):
        self.assertEquals(Category.ALL.details()['url'], '/x/everything')

    def test_following_url(self):
        self.assertEquals(Category.MY.details()['url'], '/x/following')

    def test_nonspecial_url(self):
        group = create_group(name="jailbait")
        self.assertEquals(group.details()['url'], '/x/jailbait')

    def test_top_curation(self):
        group = create_group()
        for x in range(3):
            user = create_user()
            FollowCategory(user=user, category=group).save()
            group.details.force()
        self.assertTrue(group.name in [top['name'] for top in Category.get_top_details()],
                        repr(Category.get_top_details()))

        group.visibility = Visibility.CURATED
        group.save()
        self.assertFalse(group.name in [top['name'] for top in Category.get_top_details()])

    def test_disabled_group(self):
        group = create_group()
        self.assertFalse(isinstance(Category.get(group.name), DisabledCategory))

        group.visibility = Visibility.DISABLED
        group.save()
        self.assertTrue(isinstance(Category.get(group.name), DisabledCategory))

        group.visibility = Visibility.CURATED
        group.save()
        self.assertFalse(isinstance(Category.get(group.name), DisabledCategory))

    def test_whitelisted_categories(self):
        group = create_group(name=Config['featured_groups'][0])
        group2 = create_group(name='foobar')
        self.assertTrue(group.id in Category.get_whitelisted())
        self.assertFalse(group2.id in Category.get_whitelisted())


class TestUserData(CanvasTestCase):
    def test_user_stickered_deleted_comment(self):
        cmt = self.post_comment(reply_content=create_content().id)

        # Now another user sticks it.
        user = create_user()
        result = self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': cmt.id}, user=user)

        # Then the author deletes it.
        self.api_post('/api/comment/delete', {'comment_id': cmt.id}, user=cmt.author)

        stickered = get_user_stickered(user)
        self.assertEqual(len(stickered), 0)

    def test_user_data_with_invalid_type_404s(self):
        user = create_user()
        nav_data = {'userpage_type': 'stickered', 'user': create_user().username}
        nav = Navigation.load_json_or_404(nav_data)
        nav.userpage_type = 'INVALID_TYPE'
        self.assertRaises(Http404, lambda: get_user_data(user, nav))


class TestCommentDetails(CanvasTestCase):
    def after_setUp(self):
        # Create a bunch of comments
        for i in range(1, 10):
            create_comment(author=create_user())
        self.comments = Comment.all_objects.all()

    def test_from_queryset_with_pins(self):
        self.assertTrue(self.comments)

        tiles = TileDetails.from_queryset_with_pins(self.comments)
        self.assertTrue(tiles)
        for tile in tiles:
            self.assertNotEqual(tile.pins, None)
            self.assertIsInstance(tile.comment, CommentDetails)

    def test_from_queryset_with_viewer_stickers(self):
        user = create_user()
        def tiles():
            return TileDetails.from_queryset_with_viewer_stickers(user, self.comments)

        for tile in tiles():
            self.assertEqual(tile.viewer_sticker, None)
            self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': tile.comment.id},
                          user=user)

        for tile in tiles():
            self.assertEqual(tile.viewer_sticker.type_id, 1)

    def test_properties_dont_get_serialized(self):
        # CommentDetails should only serialize its dict contents, not any of its member properties.
        cmt = create_comment().details()
        cmt.test_foo_property = 1

        d = util.loads(util.dumps(cmt))
        self.assertFalse('test_foo_property' in d)

    def test_empty_reply_content(self):
        cmt = create_comment().details()
        self.assertEqual(cmt.reply_content, {})


class TestCommentDetailsStickers(CanvasTestCase):
    def _make_stickers(self, sticks=['smiley', 'banana', 'frowny', 'frowny'], top='banana', per=2):
        self.top_id = stickers.get(top).type_id
        self.stickers = map(stickers.get, sticks)
        self.cmt = self.post_comment(reply_content=create_content().id)
        from canvas import economy
        for sticker in self.stickers:
            for _ in xrange(per):
                user = create_rich_user()
                if sticker.cost:
                    user.kv.stickers.add_limited_sticker(sticker)
                    economy.purchase_stickers(user, sticker.type_id, 1)
                    #user.redis.user_kv.hset('sticker:%s:count' % STORE_ITEM, 1)
                self.api_post('/api/sticker/comment', {
                    'type_id': sticker.type_id,
                    'comment_id': self.cmt.id,
                }, user=user)

    def test_sorted_sticker_counts(self):
        self._make_stickers()
        counts = self.cmt.details().sorted_sticker_counts()
        self.assertEqual(counts[0]['type_id'], self.top_id)
        self.assertEqual(counts[0]['count'], 2)

    def test_top_sticker(self):
        self._make_stickers()
        top_stick = self.cmt.details().top_sticker()
        self.assertFalse(top_stick is None)
        self.assertEqual(top_stick['type_id'], self.top_id)

    def test_smiley_vs_frowny(self):
        self._make_stickers()
        counts = self.cmt.details().sorted_sticker_counts()
        self.assertEqual(counts[2]['type_id'], stickers.get('smiley').type_id)
        self.assertEqual(counts[1]['type_id'], stickers.get('frowny').type_id)

    def test_num1(self):
        self._make_stickers(sticks=['cool', 'smiley'], top='cool', per=1)
        top_stick = self.cmt.details().top_sticker()
        self.assertEqual(top_stick['type_id'], self.top_id)


class TestComment(CanvasTestCase):
    def test_get_deep_replies(self):
        op = create_comment()
        def reply(to):
            return create_comment(parent_comment=op, replied_comment=to)
        r1 = reply(op)
        r2 = reply(op)
        r3 = reply(op)
        r4 = reply(r3)
        r5 = reply(r4)
        r6 = reply(r4)
        r7 = reply(op)
        self.assertEqual(len(r3.get_deep_replies()), 3)
        r8 = reply(r3)
        self.assertEqual(len(r3.get_deep_replies()), 4)

    def test_update_score(self):
        user = create_user()
        comment = create_comment(author=user)

        for sticker in stickers.primary_types:
            user = create_user()
            user.kv.stickers.currency.increment(100)
            # Sticker the comment a bunch.
            request = FakeRequest(user)
            api._sticker_comment(request, comment, sticker.type_id)

        # Update score
        comment.update_score()

    def test_make_post_anonymous_by_author(self):
        usr = create_user()
        cmt = create_comment(author=usr, anonymous=True)
        self.assertTrue(cmt.anonymous)
        cmt.make_non_anonymous(usr)
        self.assertFalse(cmt.anonymous)

    def test_make_post_anonymous_by_other(self):
        author = create_user()
        bad_user = create_user()
        cmt = create_comment(author=author, anonymous=True)
        with self.assertRaises(PermissionDenied):
            cmt.make_non_anonymous(bad_user)

    def test_details_replies_no_replies(self):
        cmt = create_comment(timestamp=123)
        d = cmt.details()

        self.assertEqual(d.reply_count, 0)
        self.assertEqual(d.last_reply_id, None)
        # This should be the timestamp of the OP in this case.
        self.assertEqual(d.last_reply_time, 123)

    def test_details_replies_one_reply(self):
        with override_service('time', FakeTimeProvider):
            cmt = create_comment()
            Services.time.step()
            child = create_comment(parent_comment=cmt)
            d = cmt.details()

            self.assertEqual(d.reply_count, 1)
            self.assertEqual(d.last_reply_id, child.id)
            self.assertAlmostEqual(d.last_reply_time, child.timestamp, places=4)

    def test_details_replies_two_replies(self):
        cmt = create_comment()
        first = create_comment(parent_comment=cmt, timestamp=1)
        second = create_comment(parent_comment=cmt, timestamp=2)
        d = cmt.details()

        self.assertEqual(d.reply_count, 2)
        self.assertEqual(d.last_reply_id, second.id)
        self.assertEqual(d.last_reply_time, second.timestamp)

    def test_details_disabled_parent_url(self):
        cmt = self.post_comment(reply_content=create_content().id)
        reply = self.post_comment(parent_comment=cmt.id, reply_content=create_content().id)
        self.assertNotEqual(cmt.details().url, None)
        self.assertEqual(reply.details().parent_url, cmt.details().url)

        cmt.moderate_and_save(Visibility.UNPUBLISHED, cmt.author)
        self.assertEqual(reply.details.force().parent_url, None)

    def test_details_replies_two_replies_last_curated(self):
        # The last reply should include curated replies to prevent "stuck" active/pinned curated OPs auto-curating
        # their replies.
        cmt = create_comment()
        first = create_comment(parent_comment=cmt, timestamp=1)
        second = create_comment(parent_comment=cmt, timestamp=2)
        second.moderate_and_save(Visibility.CURATED, second.author)
        d = cmt.details()

        self.assertEqual(d.reply_count, 2)
        self.assertEqual(d.last_reply_id, second.id)
        self.assertEqual(d.last_reply_time, second.timestamp)

    def test_details_repost_zero_for_different_content(self):
        content = create_content()
        cmt = create_comment(reply_content=content)

        self.assertEqual(cmt.details().repost_count, 0)

        content2 = create_content()
        cmt2 = create_comment(reply_content=content2)

        self.assertEqual(cmt.details.force().repost_count, 0)
        self.assertEqual(cmt2.details().repost_count, 0)

    def test_details_repost_one_for_repost(self):
        content = create_content()
        cmt = create_comment(reply_content=content)
        cmt2 = create_comment(reply_content=content)

        self.assertEqual(cmt.details.force().repost_count, 0)
        self.assertEqual(cmt2.details().repost_count, 1)

    def test_details_repost_zero_for_text_posts(self):
        # These will have the same reply_content_id (None), but we should handle that and not count them as reposts.
        cmt = create_comment()
        cmt2 = create_comment()

        self.assertEqual(cmt.details().repost_count, 0)
        self.assertEqual(cmt2.details().repost_count, 0)

    def test_details_repost_zero_for_audio_remix(self):
        content = create_content()
        cmt = create_comment(reply_content=content)
        cmt2 = create_comment(reply_content=content)
        external_content = ExternalContent.from_dict(dict(
            type="yt",
            end_time=10.0,
            start_time=0.0,
            source_url="123445555"
        ))
        external_content.parent_comment = cmt2
        external_content.save()

        self.assertEqual(cmt2.details().repost_count, 0)

    def test_details_repost_op_isnt_curated(self):
        content = create_content()
        cmt = self.post_comment(reply_content=content.id)
        cmt2 = self.post_comment(reply_content=content.id)

        self.assertEqual(cmt.details().visibility, Visibility.PUBLIC)
        self.assertEqual(cmt2.details().visibility, Visibility.PUBLIC)

    def test_details_repost_reply_is_curated(self):
        content = create_content()
        cmt = self.post_comment(reply_content=content.id)
        cmt2 = self.post_comment(reply_content=content.id, parent_comment=cmt.id)

        self.assertEqual(cmt.details().visibility, Visibility.PUBLIC)
        self.assertEqual(cmt2.details().visibility, Visibility.CURATED)

    def test_details_reply_to_public_is_public(self):
        content = create_content()
        cmt = self.post_comment(reply_content=content.id)
        cmt2 = self.post_comment(reply_text="bar", parent_comment=cmt.id)
        self.assertEqual(cmt2.details().visibility, Visibility.PUBLIC)

    def test_details_reply_to_curated_is_curated(self):
        content = create_content()
        cmt = self.post_comment(reply_content=content.id)
        cmt.moderate_and_save(Visibility.CURATED, cmt.author)
        cmt2 = self.post_comment(reply_text="bar", parent_comment=cmt.id)
        self.assertEqual(cmt2.details().visibility, Visibility.CURATED)

    def test_details_reply_to_hidden_is_curated(self):
        content = create_content()
        cmt = self.post_comment(reply_content=content.id)
        cmt.moderate_and_save(Visibility.HIDDEN, cmt.author)
        cmt2 = self.post_comment(reply_text="bar", parent_comment=cmt.id)
        self.assertEqual(cmt2.details().visibility, Visibility.CURATED)

    def test_details_reply_to_disabled_fails(self):
        content = create_content()
        cmt = self.post_comment(reply_content=content.id)
        cmt.moderate_and_save(Visibility.DISABLED, cmt.author)
        response = self.post_comment(fetch_comment=False, reply_text="bar", parent_comment=cmt.id)
        self.assertFalse(response['success'])

    def test_downvoted_comment(self):
        cmt = self.post_comment(reply_content=create_content().id)
        for _ in xrange(Comment.DOWNVOTES_REQUIRED):
            self.assertFalse(cmt.is_downvoted())
            self.assertFalse(cmt.is_collapsed())
            self.api_post('/api/sticker/comment', {
                'type_id': stickers.downvote.type_id,
                'comment_id': cmt.id,
            }, user=create_user())
        self.assertTrue(cmt.is_downvoted())
        self.assertTrue(cmt.is_collapsed())

    def test_reply_to_offtopic_op_url(self):
        op = self.post_offtopic_comment()
        reply = self.post_comment(parent_comment=op.id, reply_text="hello")
        self.assertEqual(op.get_absolute_url(), reply.get_absolute_url()[:len(op.get_absolute_url())])
        self.assertNotEqual(op.get_absolute_url(), reply.get_absolute_url())

    def test_reply_to_offtopic_op_parent_url(self):
        op = self.post_offtopic_comment()
        reply = self.post_comment(parent_comment=op.id, reply_text="hello")
        self.assertEqual(reply.get_parent_url(), op.get_absolute_url())

    def test_share_page_url(self):
        op = self.post_offtopic_comment()
        reply = self.post_comment(parent_comment=op.id, reply_text="hello")
        self.assertEqual(reply.get_share_page_url()[:3], '/d/')


class TestContent(CanvasTestCase):
    def after_setUp(self):
        self.old_function = Content._get_details

    def before_tearDown(self):
        Content._get_details = self.old_function

    def test_details_does_not_trigger_recursion(self):
        that = self
        def test_wrapper(self, **kwargs):
            test_wrapper.calls_to_get_details += 1
            return that.old_function(self, **kwargs)

        test_wrapper.calls_to_get_details = 0

        Content._get_details = test_wrapper

        op = create_comment(reply_content=create_content())
        reply = op
        for i in range(15):
            last = reply
            reply = create_comment(parent_comment=op,
                                   reply_content=create_content(remix_of=last.reply_content))

        reply.details()
        self.assertEqual(test_wrapper.calls_to_get_details, 4)


class TestLastReplyTileDetails(CanvasTestCase):
    def test_in_reply_to(self):
        op = create_comment()
        reply = create_comment(parent_comment=op)
        tile = LastReplyTileDetails.from_comment_id(op.id)
        self.assertEqual(tile.comment.thread.op.id, op.id)


class TestCanvasUser(CanvasTestCase):
    def test_unsubscribe(self):
        user = create_user()

        # Sanity checks
        # Note that the default is the EmailChannel.
        assert user.kv.subscriptions
        self.assertTrue(user.kv.subscriptions.can_receive('remixed'))

        # Now unsubscribe
        user.kv.subscriptions.unsubscribe('remixed')
        self.assertFalse(user.kv.subscriptions.can_receive('remixed'))


class TestExternalContent(CanvasTestCase):
    def test_you_tube_content(self):
        comment = create_comment()
        content = YouTubeContent(parent_comment=comment)
        content.source_url = "12345"
        content.content_type = "yt"

        START_TIME = 400
        content.start_time = START_TIME
        assert content.start_time == START_TIME
        details = content.details()
        assert "start_time" in details
        assert details.get("start_time") == START_TIME

        END_TIME = 410
        content.end_time = END_TIME
        assert content.end_time == END_TIME
        details = content.details()
        assert "end_time" in details
        assert details.get("end_time") == END_TIME

        loop_length = content.loop_length
        assert int(loop_length) == END_TIME - START_TIME

        content.save()

        # Make sure we can pull the external content from the comment
        assert content in comment.external_content.all()

        ec = comment.external_content.all()[0]
        assert ec

        assert ec.proxy
        print ec.proxy.to_client()
        print ec.proxy.source_url
        assert ec.proxy.source_url

        details = comment.details()
        self.assertTrue(hasattr(details, 'external_content'))
        ec_details = details.external_content.pop()
        self.assertTrue(ec_details)
        print ec_details
        self.assertTrue('source_url' in ec_details)

    def test_from_dict(self):
        comment = create_comment()
        external_content_dict = dict(type="yt", end_time=10.0, start_time=0.0, source_url="123445555")
        external_content = ExternalContent.from_dict(external_content_dict)
        assert isinstance(external_content, ExternalContent)
        assert isinstance(external_content, YouTubeContent)


class TestUserKV(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.sticker = stickers.Sticker(1234, "foobar", limited=True, maximum=10, cost=10)
        stickers.add_sticker(self.sticker)

    def tearDown(self):
        CanvasTestCase.tearDown(self)
        stickers.remove_sticker(self.sticker)

    def test_sticker_kv_purchase_markers(self):
        sticker = self.sticker
        user = create_user()

        assert user.kv.stickers.did_purchase(sticker) == False
        user.kv.stickers.mark_sticker_purchased(sticker)
        assert user.kv.stickers.did_purchase(sticker) == True


class TestEmail(CanvasTestCase):
    def test_ses_blacklist_silently_fails(self):
        def send_fail(messages):
            raise BotoServerError(400, "Bad Request",
            """<ErrorResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
                 <Error>
                   <Type>Sender</Type>
                   <Code>MessageRejected</Code>
                   <Message>Address blacklisted.</Message>
                 </Error>
                 <RequestId>a693e02d-00f2-11e1-9a52-ed3836840b28</RequestId>
               </ErrorResponse>""")

        with mocks.override_send_messages(send_fail):
            send_email('to@example.com', 'from@example.com', 'subjek', 'test', {})

    def test_repeating_exception_bubbles_out(self):
        def send_fail(messages):
            raise Exception

        with self.assertRaises(Exception):
            with mocks.override_send_messages(send_fail):
                send_email('a@b.com', 'b@c.com', 'subjek', 'test', {})


class TestTileData(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()
        self.COMMENT_COUNT = 7
        self.GROUP = create_group(name=Config['featured_groups'][0])
        self.TODAY = datetime.datetime(year=2011, month=2, day=3)

        with override_service('time', FakeTimeProvider):
            #TODO refactor into tests_helpers and consolidate w/ other tests that do this (email_channel, models)
            Services.time.t = time.mktime(self.TODAY.timetuple())

            self.comments = [self.post_comment(reply_content=create_content().id, category=self.GROUP.name)
                            for _ in xrange(self.COMMENT_COUNT - 1)]

            self.comments.append(self.post_comment(reply_content=create_content().id, category=self.GROUP.name,
                                                   parent_comment=self.comments[-1].id))

            Services.time.step(60*60)

            for cmt in self.comments:
                self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': cmt.id}, user=create_user())
                Services.time.step()
                Services.time.step(60*60)
                cmt.update_score()

    def _tiles(self):
        return get_browse_tiles(self.user, Navigation(sort='hot', offset=0, category=Category.ALL))

    def test_get_browse_tiles_without_dupes(self):
        tiles = get_browse_tiles(create_user(), Navigation(sort='hot', offset=0, category=Category.ALL))

        self.assertTrue(tiles)

        tile_ids = [tile.comment.id for tile in tiles]
        self.assertEqual(sorted(tile_ids), sorted(list(set(tile_ids))))

    def test_tiles_exist(self):
        self.assertTrue(self._tiles())

    def test_get_browse_tiles_with_hidden_comments(self):
        for cmt in self.comments:
            self.user.redis.hidden_comments.hide_comment(cmt)
        self.assertFalse(self._tiles())

    def test_get_browse_tiles_with_hidden_threads(self):
        for cmt in self.comments:
            self.user.redis.hidden_threads.hide_thread(cmt)
        self.assertFalse(self._tiles())

    def test_logged_out_best_everything_returns_enough_comments(self):
        with override_service('time', FakeTimeProvider):
            Services.time.t = time.mktime(self.TODAY.timetuple())
            for category in [Category.ALL] + list(Category.objects.all()):
                category.merge_top_scores()
            cmts = get_front_comments(AnonymousUser(), Navigation(sort='best',
                                                                  offset=0,
                                                                  year=2011,
                                                                  category=Category.ALL))
            self.assertEqual(len(cmts), self.COMMENT_COUNT)


class TestWelcomeEmailRecipients(CanvasTestCase):
    def test_already_received(self):
        with override_service('time', FakeTimeProvider):
            # Create dummy first, so count of users and count of recipients is unequal.
            create_user()
            Services.time.step(60*60*48)

            user = create_user()
            self.assertFalse(user in send_24h_email.recipients())

            Services.time.step(60*60*48)
            WelcomeEmailRecipient.objects.create(recipient=user)
            recipients = send_24h_email.recipients()
            self.assertFalse(user in recipients)
            self.assertFalse(recipients)

    def test_not_yet_receieved(self):
        with override_service('time', FakeTimeProvider):
            user = create_user()
            Services.time.step(60*60*24)
            recipients = send_24h_email.recipients()
            self.assertTrue(user in recipients)

    def test_send_email_happens_once_per_recipient(self):
        with override_service('time', FakeTimeProvider):
            user = create_staff()
            Services.time.step(60*60*24)
            (recipient,) = send_24h_email.recipients()
            self.assertEqual(recipient, user)

            with override_service('metrics', FakeMetrics):
                def send():
                    for user in send_24h_email.recipients():
                        send_24h_email.send_welcome_email(user)
                self.assertEqual(0, len(Services.metrics.email_sent.records))
                send()
                self.assertEqual(1, len(Services.metrics.email_sent.records), "The digest email wasn't sent.")
                send()
                self.assertEqual(1, len(Services.metrics.email_sent.records), "The email was sent twice.")

    def test_really_old_users_dont_get_it(self):
        with override_service('time', FakeTimeProvider):
            user = create_user()
            Services.time.step(60*60*24)
            self.assertTrue(user in send_24h_email.recipients())
            Services.time.step(60*60*24*30) # a month later.
            self.assertFalse(user in send_24h_email.recipients())


class TestFlaggedData(CanvasTestCase):
    def after_setUp(self):
        self.author = create_user()
        self.cmt = self.post_comment(reply_content=create_content().id, user=self.author)
        self.api_post('/api/comment/flag', {'comment_id': self.cmt.id})

    def test_real_username(self):
        (cmt,) = flagged_comments()
        self.assertEqual(self.author.username, cmt.to_client()['real_username'])
        self.assertEqual(self.author.username, cmt.real_username)

