import errno
import facebook
from os import path
import random
from subprocess import Popen, PIPE
import time
from urlparse import urlunsplit, urlsplit

from django.contrib.auth import authenticate
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpRequest, QueryDict
import django.test
from django.test.client import Client
from lxml import html, etree
from lxml.cssselect import CSSSelector

from apps.canvas_auth.models import User, AnonymousUser
from canvas import api, bgwork, util
from canvas.cache_patterns import CachedCall, cache
from canvas.experiments import create_experiments_for_request
from canvas.models import UserInfo, Category, Comment, Content, ContentUrlMapping, Visibility, InviteCode
from canvas.notifications import expander
from canvas.notifications.actions import Actions
from canvas.redis_models import redis
from services import Services


PASSWORD = 'gocanvasgo'


class Autoincr(object):
    last = 0
    @classmethod
    def get(cls):
        cls.last += 1
        return cls.last


class FakeRequest(HttpRequest):
    def __init__(self, user=None, path=None, GET={}, extra_META={}):
        HttpRequest.__init__(self)
        self.user = user or AnonymousUser()
        self.user_kv = {}
        if hasattr(self.user, 'redis'):
            self.user_kv = self.user.redis.user_kv.hgetall()
        self.session = SessionStore(session_key='skey')
        self.experiments = create_experiments_for_request(self)
        self.META = {"REMOTE_ADDR": "127.0.0.1", "PATH_INFO": path}
        self.META.update(extra_META)
        if path is not None:
            self.path = path

        if GET is not None:
            self.GET = QueryDict(GET)

    @property
    def REQUEST(self):
        return self.GET or self.POST

    @property
    def raw_post_data(self):
        return getattr(self, '_raw_post_data', getattr(super(FakeRequest, self), 'raw_post_data', None))

    @raw_post_data.setter
    def raw_post_data(self, value):
        self._raw_post_data = value


def fake_api_request(api_path, data={}):
    path = ('/api/' + api_path)
    req = FakeRequest(path=path, GET=None, extra_META={'CONTENT_TYPE': 'application/json'})
    req.raw_post_data = util.dumps(data)
    req.method = 'POST'
    return req


class CB(object):
    def __init__(self, retvalue = None):
        self.called = 0
        self.retvalue = "retvalue" if retvalue is None else retvalue

    def __call__(self):
        self.called += 1
        return self.retvalue

class NotOkay(Exception):
    def __init__(self, response):
        Exception.__init__(self, "%r: %r" % (response.status_code, response))
        self.response = response
        self.status = response.status_code

def pretty_print_etree(root):
    print etree.tostring(root, pretty_print=True)

class CanvasTestCase(django.test.TestCase):
    def setUp(self):
        # django.test.TestCase flushes the database so we have to clear the redis side as well to be consistent.
        redis.flushdb()
        cache.flush_all()
        CachedCall.inprocess_cache.flush()
        django.test.TestCase.setUp(self)
        self.restore_facebook = self.mock_facebook()
        self.after_setUp()

    def tearDown(self):
        self.before_tearDown()
        bgwork.perform()
        self.restore_facebook()
    
    def after_setUp(self):
        """ Override this to do extra setup. """
    
    def before_tearDown(self):
        """ Override this to do extra tear-down. """
        
    def assertStatus(self, status, path, **kwargs):
        try:
            response = self.get(path, **kwargs)
        except NotOkay, no:
            response = no.response
            
        self.assertEqual(status, response.status_code)
        
    def _api_response_content(self, response):
        if isinstance(response, dict):
            return response
        try:
            return util.loads(response.content[response.content.index('(') + 1:-2])
        except ValueError:
            return util.loads(response.content)

    def assertAPISuccess(self, response):
        content = self._api_response_content(response)
        self.assertTrue(content.get('success'),
                        'API response failed (returned success:false). Reason: ' + content.get('reason', ''))

    def assertAPIFailure(self, response, reason=None):
        content = self._api_response_content(response)
        self.assertEqual(content.get('success'), False, 'API response succeeded (returned success:true).')
        if reason is not None:
            self.assertEqual(content.get('reason'), reason)

    def assertRedirectsNoFollow(self, response, expected_url, host='testserver'):
        '''
        Django's assertRedirects will also attempt to GET the redirect URL and verify that it returns a 200.
        This one skips that step, basically.
        '''
        scheme, netloc, path, query, fragment = urlsplit(expected_url)
        if not (scheme or netloc):
            expected_url = urlunsplit(('http', netloc or host, path, query, fragment,))
        self.assertEqual(response._headers['location'], ('Location', expected_url))
        self.assertIn(response.status_code, [301, 302])

    
    def override_fb_get_object(self, cls):
        cls.get_object = lambda self, *args: {
            'email': 'tests@example.com',
            'first_name': 'Testy',
            'last_name': 'Testerston',
        }
    
    def mock_facebook(self):
        from facebook import GraphAPI
        from canvas.middleware import FacebookMiddleware

        def get_fb_api(request):
            fb_user = {'id': 1, 'access_token': 1}
            return fb_user, GraphAPI(1)

        def get_object(self, *args):
            return self.fb_get_object_response()

        previous_get_fb_api = util.get_fb_api
        previous_get_object = GraphAPI.get_object

        util.get_fb_api = get_fb_api
        self.override_fb_get_object(GraphAPI)

        def restore():
            util.get_fb_api = previous_get_fb_api
            GraphAPI.get_object = previous_get_object

        return restore

    def signup(self, username=None, extra_info=None, email=None, **kwargs):
        if not username:
            username = "username%s" % Autoincr.get()
        if email is None:
            email = generate_email(username)
        data = {
            'username': username,
            'password': 'buttsallthetime',
            'email': email,
            'code': InviteCode.generate().code,
        }
        data.update(kwargs)
        if extra_info is not None:
            data['info'] = extra_info
        response = self.post('/signup', data, user=AnonymousUser(), https=True)
        bgwork.perform()
        self.assertEqual(response.status_code, 302, "The signup POST didn't redirect, which probably means that "
                                                    "there was an error inside get_signup_context.")
        return User.objects.get(username=username)

    @classmethod
    def get_client(cls, user=None, password=None):
        if password is None:
            password = PASSWORD
        if not user:
            user = create_user(password=password)
        # Django 1.3 has a RequestFactory to make this much simpler.
        client = Client()
        client.login(username=user.username, password=password)
        return client

    @classmethod
    def _http_verb(cls, verb, path, client=None, data=None, user=None, password=None, https=False, **kwargs):
        data = data or {}
        client = client or cls.get_client(user=user, password=password)
        kwargs['HTTP_X_FORWARDED_PROTO'] = 'https' if https else 'http' # Simulates ELB
        response = getattr(client, verb.lower())(path, data=data, **kwargs)
        if response.status_code not in [200, 302, 301]:
            raise NotOkay(response)
        bgwork.perform()
        return response

    @classmethod
    def get(cls, path, data=None, client=None, user=None, **kwargs):
        data = data or {}
        return cls._http_verb('get', path, client=client, user=user, **kwargs)

    @classmethod
    def post(cls, path, data=None, client=None, user=None, **kwargs):
        data = data or {}
        return cls._http_verb('post', path, data=data, client=client, user=user, **kwargs)

    @classmethod
    def _api_call(cls, path, data=None, client=None, user=None, password=None, method="post"):
        data = data or {}
        response = getattr(cls, method)(path,
                                        data=util.dumps(data),
                                        client=client,
                                        user=user,
                                        password=password,
                                        content_type="application/json")
        try:
            content = util.loads(response.content)
        except ValueError:
            # Probably not a JSON response, so just return a string.
            content = response.content
        return content

    @classmethod
    def api_post(cls, *args, **kwargs):
        return cls._api_call(*args, **kwargs)

    @classmethod
    def post_comment(cls, fetch_comment=True, user=None, **kwargs):
        kwargs['anonymous'] = kwargs.get('anonymous', False)
        kwargs['replied_comment'] = kwargs.get('replied_comment')
        kwargs['parent_comment'] = kwargs.get('parent_comment')
        kwargs['reply_content'] = kwargs.get('reply_content')

        if kwargs.get('parent_comment') is None:
            kwargs['title'] = kwargs.get('title', 'Sample title.')

        # kwargs become data to post
        response = cls.api_post('/api/comment/post', kwargs, user=user)
        if fetch_comment:
            try:
                response = Comment.all_objects.get(id=response['comment']['id'])
            except KeyError:
                raise Exception(response)
        return response

    def post_offtopic_comment(self, **kwargs):
        group = create_group(founder=create_user())
        op = self.post_comment(reply_content=create_content().id, category=group.name, **kwargs)
        op.mark_offtopic(group.founder)
        return op

    def add_pin(self, user, comment):
        """
        `comment` can be an ID or a Comment instance.
        """
        id_ = getattr(comment, 'id', comment)
        return self.api_post('/api/comment/pin', {'comment_id': id_}, user=user)

    def parse_response(self, response):
        if isinstance(response, basestring):
            return html.fromstring(response)
        return html.fromstring(response.content)

    def css_select(self, response, css_selector):
        sel = css_selector if isinstance(css_selector, CSSSelector) else CSSSelector(css_selector)
        return [e for e in sel(self.parse_response(response))]

    def assertNumCssMatches(self, num, response, css_selector, message=''):
        found = len(self.css_select(response, css_selector))
        if message:
            message = '\n\n' + message
        message = "Expected {0} but found {1}.".format(num, found) + message
        self.assertEqual(num, found, message)

    def assertNoGrepMatches(self, pattern, root_path, ignored_paths=[], extensions=[r'.*']):
        def check_gnu():
            """
            Checks if this system has GNU find or not.
            """
            find = Popen(['find', '-E'], stdout=PIPE, stderr=PIPE)
            _, err = find.communicate()
            return 'unknown predicate' in err

        # Find all matching files and grep them.
        if check_gnu():
            find_cmd = ['find', root_path, '-regextype', 'posix-egrep']
        else:
            find_cmd = ['find', '-E', root_path]
        for path_ in ignored_paths:
            find_cmd.extend(['-path', path_, '-prune', '-o'])
        file_pattern = r'.*\.(' + '|'.join(extensions) + ')'
        find_cmd.extend(['-regex', file_pattern, '-print0'])

        find = Popen(find_cmd, stdout=PIPE)
        grep = Popen(['xargs', '-0', 'grep', '-P', pattern, '--files-with-matches'], stdin=find.stdout, stdout=PIPE)

        # See: http://docs.python.org/library/subprocess.html#replacing-shell-pipeline
        find.stdout.close() # Allow find to receive SIGPIPE if grep exits.

        for x in range(5):
            try:
                result, err = grep.communicate()
            except IOError, e:
                if e.errno == errno.EINTR:
                    print e
                    print "EINTR :("
                    continue
                raise
            else:
                break
        else:
            self.assertTrue(False, "Repeatedly got EINTR :( :(")


        self.assertTrue(err is None)
        self.assertFalse(result, u"The following files match for '{0}':\n\n".format(pattern) + result)

def generate_email(username=None):
    if username is None:
        username = str(random.random())
    return "{0}@example.com".format(username)

def create_user(staff=False, is_qa=True, email=None, user_cls=User, password=PASSWORD):
    unique = str(random.random())

    if email is None:
        email = generate_email(unique)

    u = user_cls.objects.create_user(unique, email, password)
    u.date_joined = Services.time.today()
    u.is_staff = staff
    UserInfo(user=u, is_qa=is_qa).save()
    u.save()
    return u

def create_rich_user(*args, **kwargs):
    # Currency is limited but has unlimited inventory
    user = create_user(*args, **kwargs)
    # Make em' rich.
    user.kv.stickers.currency.increment(100)
    return user
    
def create_staff(user_cls=User):
    user = create_user(user_cls=user_cls)
    user.is_staff = True
    user.save()
    return user
    
def create_group(**kwargs):
    name = kwargs.pop('name', str(random.random()).replace('.', '_'))
    description = kwargs.pop('description', str(random.random()))

    x = Category(name=name, description=description, **kwargs)
    x.save()
    return x

def create_content(**kwargs):
    url_mapping = ContentUrlMapping()
    url_mapping.save()
    
    content = Content(
        id=str(Autoincr.get()),
        url_mapping=url_mapping,
        timestamp=Services.time.time(),
        **kwargs
    )
    content.save()

    # Throw in some fake details. We never test this anywhere, but remixes depend on being able to hit some details of their original.
    fake_details = "{\"activity\": {\"width\": 60, \"kb\": 1, \"name\": \"processed/d763f53f918b20b562a26e9b3e3688109297ce68.png\", \"height\": 25}, \"small_square\": {\"width\": 50, \"kb\": 1, \"name\": \"processed/d763f53f918b20b562a26e9b3e3688109297ce68.png\", \"height\": 25}, \"giant\": {\"width\": 64, \"height\": 32, \"name\": \"processed/c72db1199d63872f87e59687f2bb71cef543cd62.png\", \"kb\": 1}, \"stream\": {\"width\": 64, \"height\": 32, \"name\": \"processed/c72db1199d63872f87e59687f2bb71cef543cd62.png\", \"kb\": 1}, \"column\": {\"width\": 64, \"height\": 32, \"name\": \"processed/c72db1199d63872f87e59687f2bb71cef543cd62.png\", \"kb\": 1}, \"original\": {\"width\": 64, \"height\": 32, \"name\": \"original/a023129be8f5c3fe3e7f500bc5b21a4f6df6bf89.png\", \"kb\": 1}, \"id\": \"a023129be8f5c3fe3e7f500bc5b21a4f6df6bf89\", \"alpha\": true, \"small_column\": {\"width\": 64, \"height\": 32, \"name\": \"processed/c72db1199d63872f87e59687f2bb71cef543cd62.png\", \"kb\": 1}, \"thumbnail\": {\"width\": 64, \"height\": 32, \"name\": \"processed/c72db1199d63872f87e59687f2bb71cef543cd62.png\", \"kb\": 1}}"
    redis.set('content:%s:details' % content.id, fake_details)

    return content

def create_gif_content(**kwargs):
    content = create_content(animated=True, **kwargs)
    key = 'content:%s:details' % content.id
    details = util.loads(redis.get(key))
    details['original']['animated'] = True
    redis.set(key, util.dumps(details))
    return content

def create_comment(**kwargs):
    kwargs['author'] = kwargs.get('author', create_user())
    kwargs['timestamp'] = kwargs.get('timestamp', Services.time.time())
    kwargs['anonymous'] = kwargs.get('anonymous', False)
    if kwargs.get('parent_comment') is None:
        kwargs['title'] = kwargs.get('title', 'Sample title.')
    comment = Comment(**kwargs)
    comment.save()
    return comment

def action_recipients(action_name, *args, **kwargs):
    pn = getattr(Actions, action_name)(*args)
    new_expander = expander.get_expander(pn)()
    notifications = new_expander.expand(pn)
    channel = kwargs.get('channel')
    if channel:
        notifications = [n for n in notifications if n.channel == channel]
    return [n.recipient for n in notifications if n.action == action_name]

