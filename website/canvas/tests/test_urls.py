import datetime

from django.core.urlresolvers import reverse

from apps.canvas_auth.models import AnonymousUser
from canvas.models import FollowCategory
from canvas.tests.tests_helpers import CanvasTestCase, create_group, create_content, create_user, create_staff

class TestUrls(CanvasTestCase):
    def test_non_existent_tag_okay(self):
        self.assertStatus(200, '/x/dasdfasdfasdoesntexist')

    def test_200_best(self):
        self.assertStatus(200, '/best')

    def test_200_signup(self):
        self.assertStatus(200, '/signup', user=AnonymousUser(), https=True)

    def test_200_logged_out_frontpage(self):
        self.assertStatus(200, '/')

    def test_200_logged_in_frontpage(self):
        self.assertStatus(200, '/', user=create_user())

    def test_200_logged_in_frontpage_is_following_a_group(self):
        user = create_user()
        user.redis.user_kv.hset('labs:root_is_following', 1)

        group = create_group()
        FollowCategory(category=group, user=user).save()

        self.assertStatus(200, '/', user=user)

    def test_specified_top_url_doesnt_redirect(self):
        self.assertStatus(200, '/top/2011')

    def test_monthly_top(self):
        self.assertStatus(200, '/top/2011/1')

    def test_daily_top(self):
        self.assertStatus(200, '/top/2011/1/1')

    def test_url_stripping_group(self):
        group = create_group()
        response = self.get_client().get('/x/%s/' % group.name)
        self.assertRedirects(response, '/x/%s' % group.name)

    def test_url_stripping_comment(self):
        comment = self.post_comment(reply_content=create_content().id)
        url = comment.details().url
        response = self.get_client().get('%s/' % url)
        self.assertRedirects(response, url)

    def test_url_stripping_user(self):
        username = create_user().username
        response = self.get_client().get('/user/%s/' % username)
        self.assertRedirects(response, '/user/%s' % username)

    def test_undecodeable_post_id_404s(self):
        self.assertStatus(404, '/p/toolbar_icon.gif')

