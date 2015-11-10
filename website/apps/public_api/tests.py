from apps.public_api.util import short_id, long_id
from apps.public_api.views import (root, posts, users, groups)
from canvas import util, knobs
from canvas.models import Visibility, Category
from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_user,
                                        create_group, create_comment, create_staff)
from services import Services, override_service, FakeTimeProvider
from django.conf import settings


class PublicAPITestCase(CanvasTestCase):
    @classmethod
    def get(self, *args, **kwargs):
        # TODO: get rid of this when the api doesnt require staff
        kwargs['user'] = create_staff()
        return CanvasTestCase.get(*args, **kwargs)

    @classmethod
    def post(cls, path, data=None):
        # TODO: get rid of this when the api doesnt require staff
        user = create_staff()
        data = util.dumps(data) if data else None
        return cls._http_verb('post', path, data=data, user=user, content_type='application/json')

    def before_tearDown(self):
        knobs.PUBLIC_API_RATE_LIMIT = self.old_rate_limit
        knobs.PUBLIC_API_MAX_ITEMS = self.old_max_items
        knobs.PUBLIC_API_PAGINATION_SIZE = self.old_pagination_size

    def after_setUp(self):
        self.old_rate_limit = knobs.PUBLIC_API_RATE_LIMIT
        self.old_max_items = knobs.PUBLIC_API_MAX_ITEMS
        self.old_pagination_size = knobs.PUBLIC_API_PAGINATION_SIZE

    def check_comment(self, expected, json):
        self.assertEqual(short_id(expected.id), json['id'])
        self.assertEqual(expected.title, json['title'])
        self.assertEqual(expected.category, json['category'])
        self.assertEqual(expected.reply_text, json['caption'])
        self.assertEqual(expected.author_name, json['author_name'])
        self.assertEqual(expected.parent_comment, json['parent_comment'])
        self.assertEqual(expected.parent_url, json['parent_url'])
        self.assertEqual(short_id(expected.thread_op_comment_id), json['thread_op_id'])
        self.assertEqual("https://{0}".format(settings.DOMAIN) + expected.share_page_url, json['share_page_url'])
        self.assertEqual(expected.replied_comment, json['reply_to'])
        self.assertEqual(expected.top_sticker(), json['top_sticker'])
        self.assertEqual(int(expected.timestamp), json['timestamp'])
        self.assertEqual("https://{0}".format(settings.DOMAIN) + expected.url, json['url'])

    def check_user(self, expected, json):
        self.assertEqual(expected.username, json['user'])


class TestPublicAPIGeneral(PublicAPITestCase):
    def test_no_trailing_slash_redirects(self):
        result = self.get('/public_api')
        self.assertRedirectsNoFollow(result, '/public_api/')

    def test_root(self):
        result = self.post('/public_api/')
        self.assertAPISuccess(result)
        result = self.get('/public_api/')
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertIn('documentation', json.keys())
        self.assertEqual(root.__doc__, json['documentation'])

    def test_trigger_rate_limit(self):
        knobs.PUBLIC_API_RATE_LIMIT = 2
        with override_service('time', FakeTimeProvider):
            def inner():
                for x in range(knobs.PUBLIC_API_RATE_LIMIT + 5):
                    result = self.get('/public_api/')
                    self.assertAPISuccess(result)
        self.assertRaises(AssertionError, inner)


class TestPublicAPIPosts(PublicAPITestCase):
    def test_post_documentation(self):
        result = self.post('/public_api/posts/')
        self.assertAPISuccess(result)
        result = self.get('/public_api/posts/')
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertIn('documentation', json.keys())
        self.assertEqual(posts.__doc__, json['documentation'])

    def test_get_post_by_short_id(self):
        comment = create_comment()
        result = self.get('/public_api/posts/{0}'.format(short_id(comment.id)))
        self.assertAPISuccess(result)
        result = self.post('/public_api/posts/{0}'.format(short_id(comment.id)))
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.check_comment(comment.details(), json)

    def test_handle_bad_post_id(self):
        comment = create_comment()
        result = self.get('/public_api/posts/{0}'.format(short_id(comment.id+10000)))
        self.assertAPIFailure(result)
        result = self.post('/public_api/posts/{0}'.format(short_id(comment.id+10000)))
        self.assertAPIFailure(result)

    def test_get_single_post_by_posted_id(self):
        comment = create_comment()
        id_list = [ short_id(comment.id) ]
        req = {'ids': id_list}
        result = self.post('/public_api/posts/', data=req)
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertEqual(1, len(json['posts']))
        self.check_comment(comment.details(), json['posts'][0])

    def test_get_single_distinct_post_by_posted_ids(self):
        comment = create_comment()
        id_list = [ short_id(comment.id), short_id(comment.id), short_id(comment.id) ]
        req = {'ids': id_list}
        result = self.post('/public_api/posts/', data=req)
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertEqual(1, len(json['posts']))
        self.check_comment(comment.details(), json['posts'][0])

    def test_get_multiple_posts_by_post(self):
        comment = create_comment()
        comment1 = create_comment()
        id_list = [short_id(x.id) for x in [comment, comment1]]
        req = {'ids': id_list}
        result = self.post('/public_api/posts/', data=req)
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertEqual(2, len(json['posts']))
        self.check_comment(comment.details(), json['posts'][0])

    def test_get_some_bad_some_good_posts_by_post(self):
        comment = create_comment()
        comment1 = create_comment()
        id_list = [short_id(x.id) for x in [comment, comment1]]
        id_list.append(short_id(comment.id + 10000))
        req = {'ids': id_list}
        result = self.post('/public_api/posts/', data=req)
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertEqual(2, len(json['posts']))
        self.check_comment(comment.details(), json['posts'][0])

    def test_trim_max_request(self):
        comments = [create_comment() for x in range(knobs.PUBLIC_API_MAX_ITEMS + 2)]
        id_list = [short_id(x.id) for x in comments]
        req = {'ids': id_list}
        result = self.post('/public_api/posts/', data=req)
        self.assertAPIFailure(result)

    def test_post_respects_anonymity(self):
        comment = create_comment(anonymous=True)
        id_list = [ short_id(comment.id) ]
        req = {'ids': id_list}
        result = self.post('/public_api/posts/', data=req)
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertEqual(1, len(json['posts']))
        self.assertEqual("Anonymous", json['posts'][0]['author_name'])

    def test_get_post_and_replies(self):
        comment = create_comment(anonymous=True)
        rep1 = create_comment(parent_comment=comment, replied_comment=comment)
        rep2 = create_comment(parent_comment=comment, replied_comment=rep1)
        rep3 = create_comment(parent_comment=comment, replied_comment=rep1)
        rep4 = create_comment(parent_comment=comment)
        reply_ids = [short_id(x.id) for x in [rep1, rep2, rep3, rep4]]
        req = {'ids': [short_id(comment.id)]}
        result = self.post('/public_api/posts/', data=req)
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertEqual(1, len(json['posts']))
        post = json['posts'][0]
        for id in reply_ids:
            self.assertIn(id, [x['id'] for x in post['replies']])


class TestPublicAPIUsers(PublicAPITestCase):
    def test_users_documentation(self):
        result = self.post('/public_api/users/')
        self.assertAPISuccess(result)
        result = self.get('/public_api/users/')
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertIn('documentation', json.keys())
        self.assertEqual(users.__doc__, json['documentation'])

    def test_get_user_by_username(self):
        user = create_user()
        comments = [create_comment(author=user) for x in range(3)]
        anon_comments = [create_comment(author=user, anonymous=True) for x in range(3)]
        username = user.username
        result = self.get('/public_api/users/{0}'.format(username))
        self.assertAPISuccess(result)
        result = self.post('/public_api/users/{0}'.format(username))
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.check_user(user, json)
        returned_posts = [x['id'] for x in json['posts']]
        for c in comments:
            self.assertIn(short_id(c.id), returned_posts)
        for c in anon_comments:
            self.assertNotIn(short_id(c.id), returned_posts)

    def test_handle_bad_username(self):
        user = create_user()
        username = user.username + "lolol"
        result = self.get('/public_api/users/{0}'.format(username))
        self.assertAPIFailure(result)
        result = self.post('/public_api/users/{0}'.format(username))
        self.assertAPIFailure(result)

    def test_get_users_by_post(self):
        user = create_user()
        user1 = create_user()
        user2 = create_user()
        users = [user, user1, user2]
        data = {'ids': [user.username, user1.username, user2.username, "trololo"]}
        result = self.post('/public_api/users/', data=data)
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertEqual(len(users), len(json['users']))
        returned_users = [x['user'] for x in json['users']]
        for u in users:
            self.assertIn(u.username, returned_users)

    def test_get_paged_user_posts(self):
        user = create_user()
        knobs.PUBLIC_API_PAGINATION_SIZE = 5
        first_five = [create_comment(author=user) for x in range(knobs.PUBLIC_API_PAGINATION_SIZE)]
        second_five = [create_comment(author=user) for x in range(knobs.PUBLIC_API_PAGINATION_SIZE)]
        data = {'ids': [user.username]}
        result = self.post('/public_api/users/', data=data)
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertEqual(1, len(json['users']))
        self.assertEqual(knobs.PUBLIC_API_PAGINATION_SIZE, len(json['users'][0]['posts']))
        returned_ids = [x['id'] for x in json['users'][0]['posts']]
        for x in second_five:
            self.assertIn(short_id(x.id), returned_ids)

        data = {'ids': [{'user':user.username, 'skip':knobs.PUBLIC_API_PAGINATION_SIZE}]}
        result = self.post('/public_api/users/', data=data)
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        self.assertEqual(1, len(json['users']))
        self.assertEqual(knobs.PUBLIC_API_PAGINATION_SIZE, len(json['users'][0]['posts']))
        returned_ids = [x['id'] for x in json['users'][0]['posts']]
        for x in first_five:
            self.assertIn(short_id(x.id), returned_ids)

    def test_respect_moderated_posts(self):
        user = create_user()
        comments = [create_comment(author=user) for x in range(4)]
        comments[0].moderate_and_save(Visibility.HIDDEN, user)
        comments[1].moderate_and_save(Visibility.DISABLED, user)
        comments[2].moderate_and_save(Visibility.UNPUBLISHED, user)
        comments[3].moderate_and_save(Visibility.CURATED, user)
        username = user.username
        result = self.get('/public_api/users/{0}'.format(username))
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        returned_posts = [x['id'] for x in json['posts']]
        self.assertIn(short_id(comments[0].id), returned_posts)
        self.assertNotIn(short_id(comments[1].id), returned_posts)
        self.assertNotIn(short_id(comments[2].id), returned_posts)
        self.assertIn(short_id(comments[3].id), returned_posts)

    def test_respect_anonymous_posts_via_get(self):
        user = create_user()
        comments = [create_comment(author=user, anonymous=True) for x in range(3)]
        username = user.username
        result = self.get('/public_api/users/{0}'.format(username))
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        returned_posts = [x['id'] for x in json['posts']]
        self.assertEqual(0, len(returned_posts))

    def test_respect_anonymous_posts_via_post(self):
        user = create_user()
        comments = [create_comment(author=user, anonymous=True) for x in range(3)]
        username = user.username
        result = self.post('/public_api/users/', data={'ids':[username]})
        self.assertAPISuccess(result)
        json = util.loads(result.content)
        returned_posts = [x['id'] for x in json['users'][0]['posts']]
        self.assertEqual(0, len(returned_posts))


# class TestPublicAPIGroups(PublicAPITestCase):
#     def test_groups_documentation(self):
#         result = self.post('/public_api/groups/')
#         self.assertAPISuccess(result)
#         result = self.get('/public_api/groups/')
#         self.assertAPISuccess(result)
#         json = util.loads(result.content)
#         self.assertIn('documentation', json.keys())
#         self.assertEqual(groups.__doc__, json['documentation'])

#     def test_get_group_by_name(self):
#         group = create_group()
#         groupname = group.name
#         comments = [create_comment(category=group) for x in range(3)]
#         anon_comments = [create_comment(category=group, anonymous=True) for x in range(3)]
#         result = self.get('/public_api/groups/{0}'.format(groupname))
#         self.assertAPISuccess(result)
#         result = self.post('/public_api/groups/{0}'.format(groupname))
#         self.assertAPISuccess(result)
#         json = util.loads(result.content)
#         self.assertEqual(group.name, json['group'])
#         returned_posts = [x['id'] for x in json['posts']]
#         print returned_posts
#         print comments
#         print anon_comments
#         for c in comments + anon_comments:
#             self.assertIn(short_id(c.id), returned_posts)
#         for c in anon_comments:
#             post = [x for x in json['posts'] if x['id'] == short_id(c.id)]
#             self.assertEqual(1, len(post))
#             print post[0]
#             self.assertEqual("Anonymous", post[0]['author_name'])

#     def test_handle_bad_groupname(self):
#         group = create_group()
#         groupname = group.name + "lololo"
#         result = self.get('/public_api/groups/{0}'.format(groupname))
#         print result.content
#         self.assertAPIFailure(result)
#         result = self.post('/public_api/groups/{0}'.format(groupname))
#         self.assertAPIFailure(result)

#     def test_get_groups_by_post(self):
#         group = create_group()
#         group1 = create_group()
#         groups = [group, group]
#         data = {'ids': [group.name, group1.name, "trololo"]}
#         result = self.post('/public_api/groups/', data=data)
#         self.assertAPISuccess(result)
#         json = util.loads(result.content)
#         self.assertEqual(len(groups), len(json['groups']))
#         returned_groups = [x['group'] for x in json['groups']]
#         for g in groups:
#             self.assertIn(g.name, returned_groups)

#     def test_get_paged_group_posts(self):
#         group = create_group()
#         knobs.PUBLIC_API_PAGINATION_SIZE = 5
#         first_five = [create_comment(category=group) for x in range(knobs.PUBLIC_API_PAGINATION_SIZE)]
#         second_five = [create_comment(category=group) for x in range(knobs.PUBLIC_API_PAGINATION_SIZE)]
#         data = {'ids': [group.name]}
#         result = self.post('/public_api/groups/', data=data)
#         self.assertAPISuccess(result)
#         json = util.loads(result.content)
#         self.assertEqual(1, len(json['groups']))
#         self.assertEqual(knobs.PUBLIC_API_PAGINATION_SIZE, len(json['groups'][0]['posts']))
#         returned_ids = [x['id'] for x in json['groups'][0]['posts']]
#         for x in second_five:
#             self.assertIn(short_id(x.id), returned_ids)

#         data = {'ids': [{'group':group.name, 'skip':knobs.PUBLIC_API_PAGINATION_SIZE}]}
#         result = self.post('/public_api/groups/', data=data)
#         self.assertAPISuccess(result)
#         json = util.loads(result.content)
#         self.assertEqual(1, len(json['groups']))
#         self.assertEqual(knobs.PUBLIC_API_PAGINATION_SIZE, len(json['groups'][0]['posts']))
#         returned_ids = [x['id'] for x in json['groups'][0]['posts']]
#         for x in first_five:
#             self.assertIn(short_id(x.id), returned_ids)

#     def test_respect_moderated_posts(self):
#         group = create_group()
#         user = create_user()
#         comments = [create_comment(category=group, author=user) for x in range(4)]
#         comments[0].moderate_and_save(Visibility.HIDDEN, user)
#         comments[1].moderate_and_save(Visibility.DISABLED, user)
#         comments[2].moderate_and_save(Visibility.UNPUBLISHED, user)
#         comments[3].moderate_and_save(Visibility.CURATED, user)
#         result = self.get('/public_api/groups/{0}'.format(group.name))
#         self.assertAPISuccess(result)
#         json = util.loads(result.content)
#         returned_posts = [x['id'] for x in json['posts']]
#         self.assertNotIn(short_id(comments[0].id), returned_posts)
#         self.assertNotIn(short_id(comments[1].id), returned_posts)
#         self.assertNotIn(short_id(comments[2].id), returned_posts)
#         self.assertIn(short_id(comments[3].id), returned_posts)

