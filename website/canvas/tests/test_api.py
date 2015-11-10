import os.path
import urlparse

from canvas.models import (Category, Comment, CommentPin, FollowCategory, CommentSticker, AnonymousUser, Visibility,
                           APIApp, APIAuthToken, Content, YouTubeContent, UserInfo)
from canvas.tests.tests_helpers import (CanvasTestCase, NotOkay, FakeRequest, create_content, create_user,
                                        create_group, redis, create_staff, create_comment)
from canvas import last_sticker, economy, stickers, bgwork, knobs
from canvas.api_decorators import api_decorator
from canvas.notifications.actions import Actions
from canvas.tests import tests_helpers
from canvas.util import get_or_create
from canvas.view_guards import require_POST
from services import Services, override_service, FakeTimeProvider, FakeMetrics
from django.conf import settings

STORE_ITEM = '103'


class TestApiDecorator(CanvasTestCase):
    def test_wrong_decorator_order(self):
        def wrong_order():
            api = api_decorator([])
            @require_POST
            @api('whatever', skip_javascript=True)
            def foo(request):
                pass
        self.assertRaises(TypeError, wrong_order)

    def test_correct_decorator_order(self):
        api = api_decorator([])
        @api('whatever', skip_javascript=True)
        @require_POST
        def foo(request):
            pass

class TestStickerComment(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.author = create_user()
        self.comment = self.post_comment(reply_content=create_content().id, user=self.author)

    def test_unlimited_sticker(self):
        result = self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': self.comment.id})
        for k,v in {'success': True, 'new_counts': {'1': 1}, 'remaining': None}.iteritems():
            self.assertEqual(result[k], v)

    def test_downvote_sticker(self):
        result = self.api_post('/api/sticker/comment',
                               {'type_id': stickers.downvote.type_id, 'comment_id': self.comment.id})
        # Actually check 503 here as the Javascript does this.
        for k,v in {'success': True, 'new_counts': {'503': 1}, 'remaining': None}.iteritems():
            self.assertEqual(result[k], v)

    def test_downvote_api(self):
        result = self.api_post('/api/comment/downvote_action',
                               {'comment_id': self.comment.id})
        self.assertAPISuccess(result)

    def test_logged_out_downvote_api(self):
        def downvote():
            user = AnonymousUser()
            try:
                self.api_post('/api/comment/downvote_action', {'comment_id': self.comment.id}, user=user)
            except NotOkay, e:
                return e.status
            raise Exception("The api_post call should have failed with a 403.")
        self.assertEqual(downvote(), 403)

    def test_limited_sticker_noinventory(self):
        result = self.api_post('/api/sticker/comment', {'type_id': '7', 'comment_id': self.comment.id})
        self.assertEqual(result, {'success': False, 'reason': 'Out of inventory.'})

    def test_limited_sticker_withinventory(self):
        user = create_user()
        user.redis.user_kv.hset('sticker:7:count', 10)
        result = self.api_post('/api/sticker/comment', {'type_id': '7', 'comment_id': self.comment.id}, user=user)
        for k,v in {'success': True, 'new_counts': {'7': 1}, 'remaining': 9}.iteritems():
            self.assertEqual(result[k], v)

    def test_invalid_sticker(self):
        result = self.api_post('/api/sticker/comment', {'type_id': '2001', 'comment_id': self.comment.id})
        self.assertEqual(result, {'success': False, 'reason': 'Invalid sticker.'})

    def test_hidden_sticker(self):
        result = self.api_post('/api/sticker/comment', {'type_id': '500', 'comment_id': self.comment.id})
        self.assertEqual(result, {'success': False, 'reason': 'Invalid sticker.'})

    def test_inventory_sticker_noinventory(self):
        result = self.api_post('/api/sticker/comment', {'type_id': STORE_ITEM, 'comment_id': self.comment.id})
        for k,v in {'success': False, 'reason': 'Out of inventory.'}.iteritems():
            self.assertEqual(result[k], v)

    def test_inventory_sticker_withinventory(self):
        user = create_user()
        user.redis.user_kv.hset('sticker:%s:count' % STORE_ITEM, 1)
        result = self.api_post('/api/sticker/comment',
                               {'type_id': STORE_ITEM, 'comment_id': self.comment.id}, user=user)
        for k,v in {'success': True, 'new_counts': {STORE_ITEM: 1}, 'remaining': 0}.iteritems():
            self.assertEqual(result[k], v)

    def test_send_small_sticker_get_point_immediately(self):
        sender = create_user()

        result = self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': self.comment.id}, user=sender)
        self.author.kv.update()

        self.assertTrue(result['success'])
        self.assertEqual(self.author.kv.sticker_inbox.get(), 1)

    def test_send_sticker_sets_recipients_header_info(self):
        sender = create_user()
        result = self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': self.comment.id}, user=sender)
        self.author.kv.update()

        header_info = last_sticker.get_info(self.author)

        self.assertTrue(bool(header_info['timestamp']))
        self.assertTrue(bool(header_info['url']))
        self.assertEqual(header_info['type_id'], 1)
        self.assertEqual(header_info['comment_id'], self.comment.id)


class TestCommentOfftopicMarking(CanvasTestCase):
    def test_as_staff(self):
        group = create_group()
        user = create_staff()
        cmt = self.post_comment(reply_content=create_content().id,
                                category=group.name)
        self.assertFalse(cmt.is_offtopic())
        result = self.api_post('/api/comment/mark_offtopic', {'comment_id': cmt.id, 'ot_hidden': True}, user=user)
        self.assertAPIFailure(result)
        group.moderators.add(user)
        result = self.api_post('/api/comment/mark_offtopic', {'comment_id': cmt.id, 'ot_hidden': True}, user=user)
        self.assertAPISuccess(result)
        cmt = Comment.all_objects.get(pk=cmt.pk)
        self.assertTrue(cmt.is_offtopic())

        # Now undo it.
        result = self.api_post('/api/comment/mark_offtopic', {'comment_id': cmt.id, 'ot_hidden': False}, user=user)
        cmt = Comment.objects.get(pk=cmt.pk)
        self.assertFalse(cmt.is_offtopic())


class TestCommentDelete(CanvasTestCase):
    def test_deleting_doesnt_flag(self):
        cmt = self.post_comment(reply_content=create_content().id)
        self.assertNotEqual(Comment.all_objects.get(id=cmt.id).visibility, Visibility.UNPUBLISHED)

        result = self.api_post('/api/comment/delete', {'comment_id': cmt.id}, user=cmt.author)
        self.assertEqual(result, {'success': True})
        self.assertEqual(Comment.all_objects.get(id=cmt.id).visibility, Visibility.UNPUBLISHED)
        self.assertEqual(cmt.flags.count(), 0)

    def test_deleting_others_post_fails(self):
        cmt = self.post_comment(reply_content=create_content().id)
        result = self.api_post('/api/comment/delete', {'comment_id': cmt.id})
        self.assertEqual(result, {'success': False, 'reason': 'Not comment author'})
        self.assertEqual(Comment.all_objects.get(id=cmt.id).visibility, Visibility.PUBLIC)

    def test_replying_doesnt_resurrect_post(self):
        cmt = self.post_comment(reply_content=create_content().id)
        result = self.api_post('/api/comment/delete', {'comment_id': cmt.id}, user=cmt.author)
        self.assertEqual(result, {'success': True})
        self.assertEqual(Comment.all_objects.get(id=cmt.id).visibility, Visibility.UNPUBLISHED)

        reply = self.post_comment(parent_comment=cmt.id, reply_text="back from the dead")
        self.assertEqual(Comment.all_objects.get(id=cmt.id).visibility, Visibility.UNPUBLISHED)


class TestScriptShare(CanvasTestCase):
    def test_invalidmd5(self):
        result = self.api_post('/api/script/share', {'s3sum': 'http://myurl.com'})
        self.assertEqual(result, {'success': False, 'reason': 'sums must be alphanumeric'})

    def test_validmd5(self):
        result = self.api_post('/api/script/share', {'s3sum': 'b1946ac92492d2347c6235b4d2611184'})
        self.assertEqual(result, {'success': True, 'plugin_url': '/script/1j'})


class TestGroupNew(CanvasTestCase):
    def test_with_valid_input(self):
        self.assertEqual(0, Category.objects.filter(name='foo').count())
        result = self.api_post('/api/group/new',
                               {'group_name': 'foo', 'group_description': 'baaaaaaaaaaaaaaaaaar'}, user=create_user())
        self.assertAPISuccess(result)
        self.assertEqual(1, Category.objects.filter(name='foo').count())


class TestGroupEdit(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.group = create_group()
        self.data = {'group_name': self.group.name, 'group_description': 'lolhacked1'}

    def test_user_cannot_edit(self):
        user = create_user()
        result = self.api_post('/api/group/edit', self.data, user=user)
        self.assertEqual(result, {'success': False, 'reason': 'Insufficient privileges.'})

    def test_moderator_cannot_edit(self):
        user = create_user()
        self.group.moderators.add(user)
        result = self.api_post('/api/group/edit', self.data, user=user)
        self.assertEqual(result, {'success': False, 'reason': 'Insufficient privileges.'})

    def test_founder_can_edit(self):
        user = create_user()
        self.group.founder = user
        self.group.save()
        self.assertNotEqual(Category.objects.get(name=self.group.name).description, self.data['group_description'])

        result = self.api_post('/api/group/edit', self.data, user=user)
        self.assertEqual(result, {'success': True})
        self.assertEqual(Category.objects.get(name=self.group.name).description, self.data['group_description'])


class TestCommentFlag(CanvasTestCase):
    def setUp(self):
        super(TestCommentFlag, self).setUp()
        self._old_limits = knobs.FLAG_RATE_LIMITS
        knobs.FLAG_RATE_LIMITS = {
            'm': (2, 2*60,), # Lower frequency so that the runs faster.
            'h': (50, 60*60,),
        }

    def _test_rate_limit(self, user, allowed):
        with override_service('time', FakeTimeProvider, kwargs={'t': 1333333333.}):
            client = self.get_client(user=user)
            flag_count = min(freq for freq,timespan in knobs.FLAG_RATE_LIMITS.itervalues()) + 1
            cmts = [self.post_comment(reply_content=create_content().id) for _ in xrange(flag_count)]
            msg = None
            for cmt in cmts:
                resp = self.api_post('/api/comment/flag', {'comment_id': cmt.id}, client=client)
                if not resp['success']:
                    msg = resp['reason']
                    break
            getattr(self, {True: 'assertEqual', False: 'assertNotEqual'}[allowed])(msg, None)
            if not allowed:
                self.assertTrue('limit' in msg)

    def test_rate_limit_exceeded(self):
        self._test_rate_limit(create_user(), False)

    def test_staff_exemption(self):
        self._test_rate_limit(create_staff(), True)

    def tearDown(self):
        knobs.FLAG_RATE_LIMITS = self._old_limits
        super(TestCommentFlag, self).tearDown()


class TestStoreBuy(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        # Grab a limited availability sticker
        self.sticker = stickers.Sticker(1234, "test", cost=10, maximum=100)

        # Call stickers.add_sticker so that we can use the sticker by id in api calls.
        stickers.add_sticker(self.sticker)

    def tearDown(self):
        stickers.remove_sticker(self.sticker)
        CanvasTestCase.tearDown(self)

    def test_purchase_invalidtype(self):
        result = self.api_post('/api/store/buy', {'item_type': 'badge', 'item_id': 1})
        self.assertEqual(result, {'success': False, 'reason': 'Sticker is unpurchasable for you.'})

    def test_purchase_invaliditem(self):
        result = self.api_post('/api/store/buy', {'item_type': 'sticker', 'item_id': 1})
        self.assertEqual(result, {'success': False, 'reason': 'Sticker is unpurchasable for you.'})

    def test_purchase_insufficientbalance(self):
        nyan = stickers.details_for(STORE_ITEM)
        result = self.api_post('/api/store/buy', {'item_type': 'sticker', 'item_id': nyan.type_id})
        self.assertEqual(result, {'success': False, 'reason': 'Insufficient balance.'})

    def test_purchase_sufficientbalance(self):
        nyan = stickers.details_for(STORE_ITEM)
        user = create_user()
        user.redis.user_kv.hset('sticker:7:count', 100)
        result = self.api_post('/api/store/buy', {'item_type': 'sticker', 'item_id': nyan.type_id}, user=user)
        self.assertEqual(result, {'success': True, 'new_balance': 100 - nyan.cost })

    def test_purchase_multiple_insufficient(self):
        nyan = stickers.details_for(STORE_ITEM)
        user = create_user()
        user.redis.user_kv.hset('sticker:7:count', 100)
        result = self.api_post('/api/store/buy',
                               {'item_type': 'sticker', 'item_id': nyan.type_id, 'quantity': '1000'},
                               user=user)
        self.assertEqual(result, {'success': False, 'reason': 'Insufficient balance.'})

    def test_purchase_hipster_fails_without_achievement(self):
        user = create_user()
        user.redis.user_kv.hset('sticker:7:count', 100)
        result = self.api_post('/api/store/buy', {'item_type': 'sticker', 'item_id': 305, 'quantity': '1'},
                               user=user)
        self.assertEqual(result, {'success': False, 'reason': 'Sticker is unpurchasable for you.'})

    def test_purchase_hipster_succeeds_with_achievement(self):
        user = create_user()
        user.kv.achievements.by_id(0).set(1)
        user.redis.user_kv.hset('sticker:7:count', 100)
        result = self.api_post('/api/store/buy', {'item_type': 'sticker', 'item_id': 305, 'quantity': '1'}, user=user)
        self.assertEqual(result['success'], True, repr(result))

    def test_purchase_multiple_sufficient(self):
        nyan = stickers.details_for(STORE_ITEM)
        user = create_user()
        user.redis.user_kv.hset('sticker:7:count', 1000)
        result = self.api_post('/api/store/buy', {'item_type': 'sticker', 'item_id': nyan.type_id, 'quantity': '2'},
                               user=user)
        self.assertEqual(result, {'success': True, 'new_balance': 1000-(2*nyan.cost) })

    def test_purchase_inventory_empty(self):
        nyan = stickers.details_for(STORE_ITEM)
        user = create_user()
        self.assertEqual(stickers.get_inventory(user), [])

        user.kv.stickers[7].set(100)
        result = self.api_post('/api/store/buy', {'item_type': 'sticker', 'item_id': nyan.type_id}, user=user)

        user.kv.update()
        user_inventory = stickers.get_inventory(user)
        self.assertEqual(user_inventory, [nyan])

    def test_purchase_limited_availability(self):
        user = tests_helpers.create_rich_user()
        previous_wealth = user.kv.stickers.currency.get()

        sticker = self.sticker
        # Give the user this sticker.
        # Give them zero for now.
        user.kv.stickers.add_limited_sticker(sticker)

        # Try to purchase. Should allow them
        result = self.api_post('/api/store/buy', {'item_type': 'sticker', 'item_id': sticker.type_id}, user=user)
        assert result
        print result
        new_wealth = result.get("new_balance")
        assert new_wealth == previous_wealth - sticker.cost

    def test_cant_purchase_limited_availability_multiple_times(self):
        # Grab a limited availability sticker
        sticker = self.sticker
        previous_inventory = sticker.remaining

        # Call stickers.add_sticker so that we can use the sticker by id in api calls.
        stickers.add_sticker(sticker)

        user = tests_helpers.create_rich_user()
        previous_wealth = user.kv.stickers.currency.get()

        # Give the user this sticker.
        # Give them zero for now.
        user.kv.stickers.add_limited_sticker(sticker)

        # Try to purchase. Should allow them
        result = self.api_post('/api/store/buy', {'item_type': 'sticker', 'item_id': sticker.type_id}, user=user)
        # Should not be able to buy it a second time.
        result = self.api_post('/api/store/buy', {'item_type': 'sticker', 'item_id': sticker.type_id}, user=user)
        assert result.get("success") == False

        assert sticker.remaining == previous_inventory - 1


class TestCommentPost(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.group = create_group()
        self.original = create_content()
        self.op = self.post_comment(reply_content=self.original.id, category=self.group.name)
        self.remix = create_content()
        self.remix.remix_of = self.original
        self.remix.save()

    def test_comment_reply(self):
        comment = self.post_comment(reply_text="nice one", parent_comment=self.op.id)
        self.assertTrue(self.op.id > 0)
        self.assertEqual(comment.parent_comment.id, self.op.id)

    def test_textonly_op_notallowed(self):
        result = self.post_comment(reply_text="text only can you believe it?", fetch_comment=False)
        self.assertEqual(result['success'], False)

    def test_remix_works_when_allowed(self):
        result = self.post_comment(parent_comment=self.op.id,
                                   reply_content=self.remix.id,
                                   category=self.group.name,
                                   fetch_comment=False)
        self.assertEqual(result['success'], True)


class TestCommentValidation(CanvasTestCase):
    def test_valid_post(self):
        kwargs = {
            'reply_content': create_content().id,
            'parent_comment': create_content().id,
            'external_content': dict(type="yt", start_time=100.0, end_time=200.0, source_url="1234567890"),
        }
        response = self.api_post('/api/comment/validate_post', kwargs)
        self.assertAPISuccess(response)

    def test_invalid_post(self):
        kwargs = {
            'category': "this group doesn't exist",
        }
        response = self.api_post('/api/comment/validate_post', kwargs)
        self.assertAPIFailure(response)


class TestPostComment(CanvasTestCase):
    def mock_call_count(self, *args, **kwargs):
        self.call_count += 1

    def after_setUp(self):
        self.old_func = Actions.replied
        Actions.replied = self.mock_call_count

    def before_tearDown(self):
        Actions.replied = self.old_func

    def test_posting_comment_creates_notification(self):
        self.call_count = 0

        self.post_comment(reply_text="Testing", reply_content=create_content().id)
        assert self.call_count == 1


class TestPinning(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.user = create_user()
        self.comment = self.post_comment(reply_content=create_content().id)

    def test_pin(self):
        result = self.api_post('/api/comment/pin', {'comment_id': self.comment.id}, user=self.user)

        self.assertEqual(result['success'], True)
        pin = CommentPin.objects.get_or_none(user=self.user, comment=self.comment)
        self.assertTrue(bool(pin))
        self.assertEqual(self.user.redis.pinned_bump_buffer[:], [self.comment.id])

    def test_unpin(self):
        self.api_post('/api/comment/pin', {'comment_id': self.comment.id}, user=self.user)
        result = self.api_post('/api/comment/unpin', {'comment_id': self.comment.id}, user=self.user)

        self.assertEqual(result['success'], True)
        pin = CommentPin.objects.get_or_none(user=self.user, comment=self.comment)
        self.assertFalse(bool(pin))
        self.assertEqual(self.user.redis.pinned_bump_buffer[:], [])

    def test_pin_reply_pins_parent_not_reply(self):
        reply = self.post_comment(reply_text="reply", parent_comment=self.comment.id)
        self.api_post('/api/comment/pin', {'comment_id': reply.id}, user=self.user)

        # The parent OP should be pinned, not the reply.
        self.assertTrue(CommentPin.objects.get_or_none(user=self.user, comment=self.comment))
        self.assertTrue(self.user.id in self.comment.pins())
        self.assertFalse(CommentPin.objects.get_or_none(user=self.user, comment=reply))
        self.assertFalse(self.user.id in reply.pins())
        self.assertEqual(self.user.redis.pinned_bump_buffer[:], [self.comment.id])

    def test_unpin_reply_unpins_parent(self):
        reply = self.post_comment(reply_text="reply", parent_comment=self.comment.id)
        self.api_post('/api/comment/pin', {'comment_id': reply.id}, user=self.user)
        self.assertTrue(CommentPin.objects.get_or_none(user=self.user, comment=self.comment))
        self.assertTrue(self.user.id in self.comment.pins())

        result = self.api_post('/api/comment/unpin', {'comment_id': reply.id}, user=self.user)
        self.assertEqual(result['success'], True)
        # The parent OP should be pinned, not the reply.
        self.assertFalse(CommentPin.objects.get_or_none(user=self.user, comment=self.comment))
        self.assertFalse(self.user.id in self.comment.pins())
        self.assertEqual(self.user.redis.pinned_bump_buffer[:], [])


class TestFollow(CanvasTestCase):
    def test_follow(self):
        user = create_user()
        group = create_group()
        result = self.api_post('/api/group/follow', {'category_id': group.id}, user=user)

        self.assertEqual(result['success'], True)
        fc = FollowCategory.objects.get_or_none(category=group, user=user)
        self.assertTrue(bool(fc))

    def test_unfollow(self):
        user = create_user()
        group = create_group()
        result = self.api_post('/api/group/follow', {'category_id': group.id}, user=user)
        result = self.api_post('/api/group/unfollow', {'category_id': group.id}, user=user)

        self.assertEqual(result['success'], True)
        fc = FollowCategory.objects.get_or_none(category=group, user=user)
        self.assertFalse(bool(fc))


class TestEconomyAPI(CanvasTestCase):
    def test_no_points_means_no_level_up(self):
        user = create_user()
        result = self.api_post('/api/user/level_up', {}, user=user)
        self.assertEqual(result['stats']['level_progress'], 0)
        self.assertEqual(result['stats']['level'], 0)
        self.assertEqual(result['reward_stickers'], 0)

    def test_five_points_gives_one_level_up(self):
        user = create_user()
        user.redis.user_kv.hincrby('sticker_inbox', 5)

        result = self.api_post('/api/user/level_up', {}, user=user)
        self.assertEqual(result['stats']['level_progress'], 0, result)
        self.assertEqual(result['stats']['level'], 1)
        self.assertEqual(result['reward_stickers'], 3)

    def test_five_thousand_points_gives_only_one_level_up(self):
        user = create_user()
        user.redis.user_kv.hincrby('sticker_inbox', 5000)

        result = self.api_post('/api/user/level_up', {}, user=user)
        self.assertEqual(result['stats']['level_progress'], 4995)
        self.assertEqual(result['stats']['level'], 1)
        self.assertEqual(result['reward_stickers'], 3)


class TestUserAPI(CanvasTestCase):
    def test_logged_out_user_more(self):
        user = create_user()
        result = self.api_post('/api/user/more', {'offset': 30, 'nav_data': {'user': user.username, 'userpage_type': "top", 'include_anonymous': ""}}, user=user)
        self.assertEqual(result.strip(), '')

    def test_parameterless_user_more(self):
        try:
            resp = self.api_post('/api/user/more')
        except NotOkay, e:
            self.assertEqual(e.status, 404)
        else:
            raise Exception("Didn't return 404")

    def test_user_doesnt_exist(self):
        resp = self.api_post('/api/user/exists', {'username': 'foo_no_exist'})
        self.assertAPISuccess(resp)

    def test_user_exists(self):
        user = create_user()
        resp = self.api_post('/api/user/exists', {'username': user.username})
        self.assertAPIFailure(resp)


class TestMuteThread(CanvasTestCase):
    def test_mute_thread_via_api(self):
        comment = create_comment()
        user = create_user()
        assert comment.id not in user.redis.muted_threads
        self.api_post('/api/comment/mute', {'comment_id': comment.id}, user=user)
        assert comment.id in user.redis.muted_threads

    def test_mute_thread_via_unsubscribe_page(self):
        comment = create_comment()
        user = create_user()
        assert comment.id not in user.redis.muted_threads
        self.assertStatus(200, '/unsubscribe?post=' + str(comment.id), user=user)
        assert comment.id in user.redis.muted_threads


#DISABLED: Having issues on OS X, test passes but feature fails when run under gunicorn
#DISABLED because this test strategy no longer works with subprocess calling a manage.py command to generate off of test data.
#class TestFooter(CanvasTestCase):
#    def after_setUp(self):
#        self.author = create_staff()
#        self.comment = self.post_comment(reply_content=create_content().id, user=self.author)
#        self.base_dir = "/var/canvas/website/ugc"

#    def _get_path(self):
#        return os.path.join(self.base_dir, self.comment.footer.get_path())

#    def _assert_exists(self, exists=True):
#        getattr(self, 'assert' +  str(exists))(os.path.exists(self._get_path()))

#    def test_generate_footer_on_post(self):
#        self._assert_exists()

#    def test_generate_footer_on_sticker(self):
#        # Delete the file to see if it's re-created upon stickering.
#        os.remove(self._get_path())
#        self._assert_exists(exists=False)
#        self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': self.comment.id}, user=create_user())
#        self._assert_exists()


class TestServerSideRenderedInfiniteScrolling(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.user = create_user()

    def test_user_more_claim_new_page(self):
        group = create_group()
        cmt = create_comment(category=group, author=self.user, reply_text="party_hard")
        # User looking at his own "top" page. There is no claim there
        result = self.api_post('/api/user/more', {
            'nav_data': {
               'user': self.user.username,
               'userpage_type': 'new',
            }
        }, user=self.user)

        print result
        self.assertTrue(cmt.reply_text in result)

        self.assertTrue("Delete" in result)
        self.assertTrue("Claim" not in result)

    def test_user_more_claim_anonymous_page(self):
        group = create_group()
        cmt = create_comment(category=group, author=self.user, anonymous=True, reply_text="party hard")
        # User looking at his own "top" page. There is no claim there
        result = self.api_post('/api/user/more', {
            'nav_data': {'user': self.user.username, "userpage_type": "new_anonymous"}
        }, user=self.user)
        print cmt.reply_text
        assert cmt.reply_text in result
        assert "Claim" in result


class TestStaffHelperAPIs(CanvasTestCase):
    def test_send_notification(self):
        with override_service('metrics', FakeMetrics):
            user = create_staff()
            pn = self.api_post('/api/staff/send_notification_email', {
                'action': 'digest',
                'username': user.username,
            }, user=create_staff())
            self.assertAPISuccess(pn)

            self.assertEqual(1, len(Services.metrics.email_sent.records))

