import base64
import cProfile
import cStringIO
import collections
import gzip
import hmac
import inspect
import itertools
import logging
import math
import os
import socket
import struct
import time
from urlparse import urljoin

from django.conf import settings
from django.db.models import Model, FloatField
from django.db.models.query import QuerySet
from django.db.models.sql.compiler import SQLInsertCompiler
from django.http import Http404
from django.template import Context, Template
from django.utils.encoding import force_unicode
from django.utils.functional import Promise
from django.utils.html import escape, strip_tags
from django.utils.safestring import mark_safe
import facebook
from jinja2 import Markup

from canvas.exceptions import NotLoggedIntoFacebookError
from canvas.json import loads, dumps, client_dumps, backend_dumps, JSONDecodeError
from configuration import Config
from services import Services

logger = logging.getLogger()

unique = lambda iterable: list(set(iterable))

clamp = lambda lower, value, upper: min(upper, max(lower, value))

#TODO this is deprecated because of functools.wraps, unless someone knows an advantage to this method. --alex
def simple_decorator(decorator):
    """
    This decorator can be used to turn simple functions
    into well-behaved decorators, so long as the decorators
    are fairly simple. If a decorator expects a function and
    returns a function (no descriptors), and if it doesn't
    modify function attributes or docstring, then it is
    eligible to use this. Simply apply @simple_decorator to
    your decorator and it will automatically preserve the
    docstring and function attributes of functions to which
    it is applied.
    """
    def new_decorator(f):
        g = decorator(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g
    # Now a few lines needed to make simple_decorator itself
    # be a well-behaved decorator.
    new_decorator.__name__ = decorator.__name__
    new_decorator.__doc__ = decorator.__doc__
    new_decorator.__dict__.update(decorator.__dict__)
    return new_decorator

def iterlist(fun):
    def wrapper(*args, **kwargs):
        return list(fun(*args, **kwargs))
    return wrapper

def ip_to_int(ip):
    try:
        return struct.unpack('I', socket.inet_aton(ip))[0]
    except (socket.error, struct.error, TypeError):
        return 0

def int_to_ip(integer):
    return socket.inet_ntoa(struct.pack('I', integer))

def flatten(list_of_lists):
    """ Flatten one level of nesting. """
    return itertools.chain.from_iterable(list_of_lists)

def js_safety(thing, django=True, escape_html=False):
    thing = thing.replace('<', '\\u003c').replace('>', '\\u003e')

    if django:
        return mark_safe(thing)
    else:
        if escape_html:
            return thing
        return Markup(thing)

def get_or_create(cls, **kwargs):
    inst = cls.objects.get_or_none(**kwargs)
    if inst is None:
        inst = cls(**kwargs)
        inst.save()
    return inst

class GetSlice(object):
    def __getitem__(self, item):
        return item

get_slice = GetSlice()

# Modified, originally from http://en.wikipedia.org/wiki/Base_36
def _raw_base36encode(number):
    """
    Convert positive integer to a base36 string.
    JS: canvas.base36encode
    """
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer')
    if number <= 0:
        raise ValueError('number must be a positive integer')

    alphabet='0123456789abcdefghijklmnopqrstuvwxyz'
    checksum = 0

    base36 = ''
    while number != 0:
        number, i = divmod(number, 36)
        checksum += i * 19
        base36 = alphabet[i] + base36

    return base36, alphabet[checksum % 36]


def base36encode(number):
    base36, check = _raw_base36encode(number)
    return base36 + check

class Base36DecodeException(Exception): pass

def base36decode(string):
    if not string:
        raise Base36DecodeException("Empty string")

    base36, check = string[:-1], string[-1]

    try:
        number = int(base36, 36)
    except ValueError:
        raise Base36DecodeException("Invalid base36 characters.")

    try:
        _, expected_check = _raw_base36encode(number)
    except ValueError:
        raise Base36DecodeException("Invalid base36 number.")

    if expected_check != check:
        raise Base36DecodeException("base36 check character does not match.")

    return number

def base36decode_or_404(string):
    try:
        return base36decode(string)
    except Base36DecodeException:
        raise Http404

def random_token(length=40):
    assert length % 2 == 0
    return base64.b16encode(os.urandom(length//2))

def placeholder(self, conn, field, value):
    if isinstance(value, Now):
        return value.as_sql(None, conn)[0]
    else:
        return SQLInsertCompiler.placeholder(self, field, value)

# EVIL HAX
def as_sql(self):
    # We don't need quote_name_unless_alias() here, since these are all
    # going to be column names (so we can avoid the extra overhead).
    qn = self.connection.ops.quote_name
    opts = self.query.model._meta
    result = ['INSERT INTO %s' % qn(opts.db_table)]
    result.append('(%s)' % ', '.join([qn(c) for c in self.query.columns]))
    values = [placeholder(self, self.connection, *v) for v in self.query.values]
    result.append('VALUES (%s)' % ', '.join(values))
    params = [param for param in self.query.params if not isinstance(param, Now)]
    if self.return_id and self.connection.features.can_return_id_from_insert:
        col = "%s.%s" % (qn(opts.db_table), qn(opts.pk.column))
        r_fmt, r_params = self.connection.ops.return_insert_id()
        result.append(r_fmt % col)
        params = params + r_params
    return ' '.join(result), params

SQLInsertCompiler.as_sql = as_sql

class UnixTimestampField(FloatField):
    def get_prep_value(self, value):
        if isinstance(value, Now):
            return value
        return FloatField.get_prep_value(self, value)

class Now(object):
    def prepare_database_save(self, field):
        return self

    def _sql(self, executable_name):
        return Services.time.sql_now(executable_name)

    def as_sql(self, qn, conn):
        return self._sql(conn.client.executable_name), []


def get_fb_api(request):
    fb_user = facebook.get_user_from_cookie(request.COOKIES,
                                            Config['facebook']['app_id'],
                                            Config['facebook']['secret'])
    access_token = fb_user and fb_user.get('access_token')
    if not access_token:
        raise NotLoggedIntoFacebookError()

    return fb_user, facebook.GraphAPI(access_token)

class ArgSpec(object):
    """
    Convenience wrapper around `inspect.ArgSpec`.

    Properties:
        `args`:
            The list of arg names. Not the same as `inspect.ArgSpec#args`, however - this excludes the kwarg names.

        `kwargs`:
            A dictionary of kwarg names mapped to their default values.

    Note that if the given function contains a member annotation named `_original_function`, it will use that
    instead of the function.
    """
    def __init__(self, func):
        func = getattr(func, '_original_function', func)
        spec = inspect.getargspec(func)
        defaults = spec.defaults or []

        self.args = spec.args[:len(spec.args) - len(defaults)]
        self.kwargs = dict(zip(spec.args[-len(defaults):], defaults))

def page_divide(x, y):
    return max(1, int(math.ceil(1.0 * x / y)))

def paginate(iterable, page=1, per_page=50):
    count = len(iterable)
    page_last = page_divide(count, per_page)

    # Handle 'current'.
    if page == 'current':
        start, stop = max(0, count-per_page), count
        page = page_last
    else:
        # Handle p=9999
        page = min(int(page), page_last)
        start, stop = per_page * (page-1), per_page * (page)

    # page_next is None when there aren't any more pages.
    page_next = page+1 if page < page_last else None

    return iterable[start:stop], page, page_next, page_last


def profile(fun):
    if settings.PROFILE:
        def wrap(request, *args, **kwargs):
            profiler = cProfile.Profile()
            result = profiler.runcall(fun, request, *args, **kwargs)
            profiler.dump_stats('/var/canvas/website/run/profile-%s-%s.pstats'
                                % (request.path.replace('/', '_'), int(time.time() * 1000)))
            return result
        return wrap
    else:
        return fun

def generate_email_links():
    """
    Feel free to rewrite me, I'm just an example of the last use. Just change 'visitor' and 'data'.
    """
    def visitor(item):
        from canvas.models import User
        username, groups = [x.strip() for x in item.split(':')]
        user = User.objects.get(username=username)
        subject = '%s, Canvas needs you!' % username
        body = """Hey %s!\n\nWe've noticed you're one of the top posters in our Canvas-owned groups (%s), and would love to have you as a referee if you are interested. Referees are able to mark posts in appointed groups as off-topic, collapsing them and helping to keep discussion and posts relevant to the group."""
        body += """\n\nIf you would be interested in helping us out, let us know, we'd greatly appreciate it!"""
        body += """\n\nThanks for being awesome,\n- The Canvas Team"""
        body %= (username, groups)
        body = body.replace('\n', '%0A')
        return {'to': user.email, 'subject': subject, 'body': body}
    data = """blblnk: cute, pop_culture, canvas
        nicepunk: cute, the_horror, stamps
        powerfuldragon: cute, stamps, girls
        cybertaco: games
        tobacco: games
        straitjacketfun: photography
        slack_jack: photography
        oliveoodle: pop_culture
        ryoshi: pop_culture
        oliveiralmeida: nerdy
        AquilesBaeza: nerdy, the_horror
        nebetsu: nerdy
        Laban: food
        ROPED: food
        MuttonChops: canvas
        Degu: stamps
        sparknineone: girls"""
    for item in data.split('\n'):
        print """<a href="mailto:%(to)s?subject=%(subject)s&body=%(body)s">%(to)s</a><br/>""" % visitor(item)


def has_flagged_words(text):
    """
    Returns True if @text has flagged words.
    """
    return any((flag_word in text) for flag_word in Config.get('autoflag_words', []))

def make_absolute_url(relative_url, protocol=None):
    """
    Takes a relative url and makes it absolute by prepending the Canvas absolute domain.

    This refers not to relative as in "foo" resolving to "/bar/foo" when you're already on "/bar", but to an
    absolute path sans the host portion of the URL.

    `protocol` should be the name without the "://", e.g. "http" or "https"
    """
    # Is it already absolute?
    if relative_url.split('//')[-1].startswith(settings.DOMAIN) and relative_url.startswith(protocol or '//'):
        return relative_url

    if protocol:
        protocol = protocol + '://'
    else:
        protocol = '//'

    base = protocol + settings.DOMAIN
    return urljoin(base, relative_url)


_template_tag_cache = {}

def render_template_tag(tag_name, args=None, module=None, context_instance=None):
    """
    `args` may be either an list of tuples, or any other iterable. If it contains tuples,
    it will create a context object out of it with the car as the key and the cdr as the value,
    and the keys will be passed to the template tag. (This is to simulate an ordered dict.)

    Otherwise, the items in `args` are given as strings to the template tag.

    It caches templates, but only if `args` has tuples.

    This renders to a string. To use it as a view response, wrap it in HttpResponse.
    """
    def make_cache_key(module, tag_name, arg_cars):
        return u'-'.join(e for e in [module, tag_name, arg_cars] if e is not None)

    prefix, _args = '', ''
    context = {}
    cache_key = None # Doesn't cache if this doesn't get set.

    if module:
        prefix = u'{{% load {0} %}}'.format(module)

    if args:
        args = list(args)
        if isinstance(args[0], tuple):
            context.update(dict((arg[0], arg[1]) for arg in args))
            _args = u' '.join(arg[0] for arg in args)
            cache_key = make_cache_key(module, tag_name, _args)
        else:
            _args = u' '.join(u'"{0}"'.format(arg) for arg in args)

    if cache_key and cache_key in _template_tag_cache:
        template = _template_tag_cache[cache_key]
        _template_tag_cache[cache_key] = template
    else:
        template = Template(u'{0}{{% {1} {2} %}}'.format(prefix, tag_name, _args))
        if cache_key:
            _template_tag_cache[cache_key] = template

    if context_instance is None:
        context_instance = Context(context)
    else:
        for key, val in context.iteritems():
            context_instance[key] = val

    return template.render(context_instance)

def get_arg_names(func):
    """ Returns a list with function argument names. """
    return inspect.getargspec(func)[0]

def token(msg):
    """ Returns a Canvas "signed" hash of a token. This is used in unsubscribe links. """
    return hmac.new(settings.SECRET_KEY, msg=str(msg)).hexdigest()

class paramaterized_defaultdict(collections.defaultdict):
    """ Defaultdict where the default_factory takes key as an argument. """
    def __missing__(self, key):
        return self.default_factory(key)

def gzip_string(data):
    str_file = cStringIO.StringIO()

    gzip_file = gzip.GzipFile(fileobj=str_file, mode='wb')
    gzip_file.write(data)
    gzip_file.close()

    return str_file.getvalue()

def strip_template_chars(text):
    text = text.replace('{{', '&#123;' * 2)
    text = text.replace('}}', '&#125;' * 2)
    text = text.replace('{%', '&#123;%')
    text = text.replace('%}', '%&#125;')
    text = text.replace('{#', '&#123;#')
    text = text.replace('#}', '#&#125;')
    return text

