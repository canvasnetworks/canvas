import copy
import logging
import random
import urllib

from django.contrib.sessions.backends.cache import SessionStore
from django.contrib.sessions.models import Session
from django.core.urlresolvers import reverse
from django.http import Http404
import facebook

from apps.canvas_auth.models import User, AnonymousUser
from apps.signup.views import signup, get_signup_context
from canvas import bgwork, stickers, views, util, knobs
from canvas.models import (Visibility, get_system_user, Config, Category, FacebookUser,
                           EmailUnsubscribe, APIApp, APIAuthToken, CommentSticker, Comment)
from canvas.notifications.email_channel import EmailChannel
from canvas.notifications.notification_models import UserNotificationsSubscription
from canvas.templatetags import canvas_tags
from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_group, create_user, create_staff,
                                        create_comment, create_gif_content, FakeRequest, pretty_print_etree)
from canvas.util import get_or_create, dumps
import configuration
from services import Services, override_service, FakeTimeProvider, FakeRandomProvider, FakeExperimentPlacer


class TestCommentViews(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.group = create_group(founder=create_user())
        self.content = create_content()
        self.text = 'foo bar baz lol what'
        self.op = self.post_comment(reply_content=self.content.id, category=self.group.name, reply_text=self.text)
        self.user = create_user()

        # It would be great to at some point make some kind of "with configOverride(foo=new_value):"
        self.previousConfig = copy.deepcopy(configuration.Config)
        Config['minimum_top_replies'] = 1
        Config['maximum_top_replies'] = 2
        Config['posts_per_top_reply'] = 2

        self._per_page = knobs.COMMENTS_PER_PAGE
        knobs.COMMENTS_PER_PAGE = 2

    def tearDown(self):
        configuration.Config = self.previousConfig
        knobs.COMMENTS_PER_PAGE = self._per_page
        CanvasTestCase.tearDown(self)

    def test_posted_comment_is200(self):
        self.assertStatus(200, self.op.details().url)

    def test_deleted_comment_is404(self):
        self.api_post('/api/comment/delete', {'comment_id': self.op.id}, user=self.op.author)
        self.assertStatus(404, self.op.details().url)

    def test_invalid_base36_is_404(self):
        self.assertStatus(404, '/p/q2s.txt') # Invalid characters
        self.assertStatus(404, '/p/q2x') # Check digit wrong

    def test_disabled_comment_is200(self):
        self.op.moderate_and_save(Visibility.DISABLED, get_system_user())
        self.assertEqual(Visibility.DISABLED, self.op.visibility)
        self.assertStatus(200, self.op.details().url)

    def test_bad_reply_url_is_still_200(self):
        print self.op.details().url
        self.assertStatus(200, self.op.details().url + '/reply/99999999')

    def test_logged_out_view_of_comment(self):
        self.assertStatus(200, self.op.details().url, user=AnonymousUser())

    def test_logged_out_staff_view(self):
        self.assertStatus(403, '/staff', user=AnonymousUser())

    def test_404ed_comment_urls(self):
        self.assertStatus(404, '/p/%#@$&^')
        self.assertStatus(404, '/p/00')
        self.assertStatus(404, '/p/0')
        self.assertStatus(404, '/p/01')

    def test_replies_box_shown_when_replies(self):
        reply = self.post_comment(parent_comment=self.op.id, reply_text="hello")
        resp = self.get(self.op.get_absolute_url(), user=self.user)
        self.assertNumCssMatches(0, resp, "#comments.hidden")

    def test_visiting_pending_post_unsets_pending_post(self):
        op_url = self.op.details().url
        self.user.kv.post_pending_signup_url.set(op_url)
        self.assertTrue(self.user.kv.post_pending_signup_url.get())

        resp = self.get(op_url, user=self.user)
        self.assertFalse(self.user.kv.post_pending_signup_url.get(nocache=True))

    def test_facebook_metadata(self):
        reply = self.post_comment(parent_comment=self.op.id, reply_text="tldr")
        resp = self.get(reply.get_absolute_url())
        (desc,) = self.css_select(resp, 'meta[property="og:description"]')
        self.assertEqual(desc.attrib['content'], 'tldr')


class TestUserViews(CanvasTestCase):
    def test_stickered_deleted_post(self):
        '''
        Checks that a deleted post is not visible in the "stickered by" view if it had been stickered before it was
        deleted.
        '''
        op = self.post_comment(reply_content=create_content().id)
        text = 'lol what'
        cmt = self.post_comment(parent_comment=op.id, reply_text=text)

        # Now another user sticks it.
        user = create_user()
        result = self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': cmt.id}, user=user)

        # Then the author deletes it.
        self.api_post('/api/comment/delete', {'comment_id': cmt.id}, user=cmt.author)

        # Check the user page.
        viewer = create_user()
        resp = self.get('/user/{0}/stickered'.format(user.username), user=viewer)
        self.assertFalse(self.css_select(resp, '.image_tile.post_{0}'.format(cmt.id)))
        self.assertFalse(text in resp.content)

    def test_noindex(self):
        user = create_user()

        def get_meta():
            resp = self.get('/user/{0}'.format(user.username))
            return self.css_select(resp, 'meta[name="robots"]')

        self.assertFalse(get_meta())

        user.join_lab('hide_userpage_from_google')
        meta = get_meta()
        self.assertTrue(meta)
        self.assertEqual(meta[0].attrib['content'], 'noindex')


class TestSignupViews(CanvasTestCase):
    def test_signup_creates_user(self):
        signup_name = 'ilovetotest'
        self.assertEqual(0, User.objects.filter(username=signup_name).count())
        self.signup('ilovetotest')
        self.assertEqual(1, User.objects.filter(username=signup_name).count())

    def test_signup_without_facebook(self):
        self.restore_facebook()
        try:
            user = self.signup('nofacebook', email="nofacebook@example.com")
        finally:
            self.mock_facebook()

        self.assertEqual(user.email, "nofacebook@example.com")
        self.assertRaises(FacebookUser.DoesNotExist, lambda: user.facebookuser)

    def test_signup_creates_user_even_with_extra_info_from_logged_out_posting(self):
        signup_name = 'ilovetotest'
        self.assertEqual(0, User.objects.filter(username=signup_name).count())
        self.signup('ilovetotest', extra_info='{}')
        self.assertEqual(1, User.objects.filter(username=signup_name).count())

    def test_signup_prompt_standard(self):
        resp = self.get('/signup_prompt', https=True)
        self.assertNumCssMatches(1, resp, '.login_prompt h1.signup')
        self.assertNumCssMatches(0, resp, '.login_prompt p.sticker_limit')
        self.assertNumCssMatches(0, resp, '.login_prompt p.post_pending')
        self.assertNumCssMatches(0, resp, '.login_prompt input.post_pending')

    def test_signup_prompt_from_reply(self):
        resp = self.get('/signup_prompt?post_pending', https=True)
        self.assertNumCssMatches(1, resp, '.login_prompt h1.post_pending')
        self.assertNumCssMatches(0, resp, '.login_prompt p.sticker_limit')
        self.assertNumCssMatches(1, resp, '.login_prompt p.post_pending')
        self.assertNumCssMatches(1, resp, '.login_prompt input.post_pending')

    def test_signup_prompt_from_sticker(self):
        resp = self.get('/signup_prompt?sticker_limit', https=True)
        self.assertNumCssMatches(1, resp, '.login_prompt h1.signup')
        self.assertNumCssMatches(1, resp, '.login_prompt p.sticker_limit')
        self.assertNumCssMatches(0, resp, '.login_prompt p.post_pending')
        self.assertNumCssMatches(0, resp, '.login_prompt input.post_pending')


class TestLoggedOutReplies(CanvasTestCase):
    def test_signup_with_reply(self):
        op = self.post_comment(reply_content=create_content().id)
        info = {
            u'url': u'https://savnac.com/p/66',
            u'post': {
                u'category': None,
                u'parent_comment': op.id,
                u'replied_comment': None,
                u'anonymous': False,
                u'reply_text': u'ooooooo',
                u'reply_content': None
            },
            u'reason': u'reply',
        }
        def get_op():
            return Comment.objects.get(pk=op.pk)
        self.assertEqual(0, get_op().replies.count())
        self.signup('ilovetotest', extra_info=dumps(info))
        self.assertEqual(1, get_op().replies.count())

"""
class TestLoginViews(CanvasTestCase):
    def test_empty_login(self):
        response = self.post('/login', {}, https=True)
        self.assertTemplateUsed(response, 'user/login.html')
"""


class TestEmailViews(CanvasTestCase):
    def test_user_id_token_allows_unsubscribe(self):
        user = create_user()
        url = "/unsubscribe?" + urllib.urlencode({
            'action': 'remixed',
            'token': util.token(user.id),
            'user_id': user.id,
        })

        self.assertTrue(user.kv.subscriptions.can_receive('remixed'))
        self.assertStatus(200, url, user=AnonymousUser())
        self.assertFalse(user.kv.subscriptions.can_receive('remixed'))

    def test_email_token_that_corresponds_to_user_allows_from_channel(self):
        user = create_user()
        url = "/unsubscribe?" + urllib.urlencode({
            'action': 'remixed',
            'token': util.token(user.email),
            'email': user.email,
        })

        self.assertTrue(user.kv.subscriptions.can_receive('remixed'))
        self.assertStatus(200, url, user=AnonymousUser())
        self.assertFalse(user.kv.subscriptions.can_receive('remixed'))

    def test_email_token_allows_unsubscribe_from_all(self):
        email = "foo@example.com"
        url = "/unsubscribe?" + urllib.urlencode({
            'token': util.token(email),
            'email': email,
        })

        self.assertFalse(EmailUnsubscribe.objects.get_or_none(email=email))
        self.assertStatus(200, url, user=AnonymousUser())
        self.assertTrue(EmailUnsubscribe.objects.get_or_none(email=email))

    def test_broken_token_ignored_for_logged_in_user(self):
        user = create_user()
        url = "/unsubscribe?" + urllib.urlencode({
            'action': 'remixed',
            'token': "GARBAGE DAY",
            'email': user.email,
        })

        self.assertTrue(user.kv.subscriptions.can_receive('remixed'))
        self.assertStatus(200, url, user=user)
        self.assertFalse(user.kv.subscriptions.can_receive('remixed'))

    def test_unsubscribe_page_without_user_id(self):
        user = create_user()
        resp = self.get('/unsubscribe?' + urllib.urlencode({
            'token': util.token(user.email),
            'email': user.email,
        }))
        self.assertNumCssMatches(0, resp, 'input[name="user_id"]')

    def test_unsubscribe_page_with_user_id(self):
        user = create_user()
        resp = self.get('/unsubscribe?' + urllib.urlencode({
            'token': util.token(user.email),
            'email': user.email,
            'user_id': user.id,
        }))
        selector = 'input[name="user_id"]'
        self.assertNumCssMatches(1, resp, 'input[name="user_id"]')

    def test_granular_unsubscribe(self):
        all_actions = EmailChannel.all_handled_actions()

        for action in all_actions:
            if action == 'newsletter':
                continue
            u = create_user()
            assert u.kv.subscriptions.can_receive(action)
            actions_dict = {}
            actions_dict = {action: "on"}
            self.validate_unsubscript(actions_dict, u)
            assert u.kv.subscriptions.can_receive(action)

    def test_unsubscribe_headers(self):
        action = 'remixed'
        user = create_user()
        self.assertTrue(user.kv.subscriptions.can_receive(action, EmailChannel))
        self.assertStatus(200, "/unsubscribe?action="+action, user=user)
        self.assertFalse(user.kv.subscriptions.can_receive(action, EmailChannel))

    def test_granualr_unsubscribe_blanket_ban(self):
        all_actions = EmailChannel.all_handled_actions()
        # ALL has inverted semantics ... make sure it works.
        all_actions.append("ALL")
        # Reuse the same user
        canvas_user = create_user()
        action = "ALL"
        actions_dict = {action: "on"}
        unsubscriptions = self.validate_unsubscript(actions_dict, canvas_user, all_actions)
        for action in all_actions:
            # Ensure that we unsubscribed from all of them!
            assert unsubscriptions.get(action)

        action = "ALL"
        # Remove blanket subscription
        actions_dict = {}
        request = FakeRequest()
        views.handle_unsubscribe_post(canvas_user, actions_dict, request)
        unsubscriptions = views.get_unsubscriptions(canvas_user, all_actions)
        for action in all_actions:
            # Ensure that the user is now subscribed for everything, which is the default without the blanket ban.
            assert not unsubscriptions.get(action)

    def validate_unsubscript(self, actions_dict, canvas_user=None, all_actions=None):
        if not canvas_user:
            canvas_user = create_user()
        if not all_actions:
            all_actions = EmailChannel.all_handled_actions()

        request = FakeRequest()
        views.handle_unsubscribe_post(canvas_user, actions_dict, request)
        unsubscriptions = views.get_unsubscriptions(canvas_user, all_actions)
        for action in all_actions:
            if action == 'newsletter':
                continue
            value = action
            if action == "ALL":
                value = not action
            if actions_dict.get(action) == "on":
                assert not unsubscriptions.get(value)
            else:
                assert unsubscriptions.get(value)
        return unsubscriptions

class TestGroupNewViews(CanvasTestCase):
    def setUp(self):
        super(TestGroupNewViews, self).setUp()
        self._old_limit = Category.FOUND_LIMIT
        Category.FOUND_LIMIT = 2

    def tearDown(self):
        Category.FOUND_LIMIT = self._old_limit
        super(TestGroupNewViews, self).tearDown()

    def test_found_limit(self):
        user = create_user()
        for _ in xrange(Category.FOUND_LIMIT):
            resp = self.get('/group/new', user=user)
            self.assertContains(resp, 'id="group_new"')
            self.assertNotContains(resp, 'max_founded_notice')
            group = create_group(founder=user)

        resp = self.get('/group/new', user=user)
        self.assertContains(resp, 'max_founded_notice')
        self.assertNotContains(resp, 'id="group_new"')

