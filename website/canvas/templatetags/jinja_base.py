""" Functions used for creating and working with Jinja2 tags. """
from functools import partial, wraps
import os
import sys

from django import template
from django.conf import settings as django_settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.template import Context, RequestContext
from django.utils.importlib import import_module
from jinja2 import FileSystemLoader, Environment, MemcachedBytecodeCache, Markup, contextfunction

from apps.jinja_adapter.adapter import ExtendsDjangoExtension
from apps.jinja_adapter.csrf import CsrfTokenExtension
from canvas.util import logger
from compressor.contrib.jinja2ext import CompressorExtension
from django.conf import settings


default_mimetype = getattr(django_settings, 'DEFAULT_CONTENT_TYPE')
bytecode_cache = MemcachedBytecodeCache(cache)

################################################
#
# Template directories.
#
template_dirs = getattr(django_settings, 'TEMPLATE_DIRS')

# Look in apps for more template dirs.
# (Ported from django.template.loaders.app_dirctories)
#
# At compile time, cache the directories to search.
fs_encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()
app_template_dirs = []
for app in django_settings.INSTALLED_APPS:
    try:
        mod = import_module(app)
    except ImportError, e:
        raise ImproperlyConfigured('ImportError %s: %s' % (app, e.args[0]))
    template_dir = os.path.join(os.path.dirname(mod.__file__), 'templates')
    if os.path.isdir(template_dir):
        app_template_dirs.append(template_dir.decode(fs_encoding))

template_dirs = template_dirs + tuple(app_template_dirs)

# auto_reload=False so that we only invalidate cache when the Django worker gets failovered.
env = Environment(loader=FileSystemLoader(template_dirs), autoescape=True, bytecode_cache=bytecode_cache,
                  auto_reload=settings.DEBUG,
                  extensions=[ExtendsDjangoExtension, CsrfTokenExtension, CompressorExtension])


def filter_tag(fun):
    env.filters[fun.__name__] = fun
    return fun

def global_tag(fun):
    env.globals[fun.__name__] = fun
    return fun

def update_context(context, options):
    d = dict(context.iteritems())
    d.update(options)
    return d

def to_dict_context(context):
    """ If it's a Django Context instance, turn it into a regular dict. """
    if isinstance(context, Context):
        django_context = context
        context = {}
        # Django Context instances contain a list (a stack) of dicts.
        # If you iterate over the context object, it returns dicts in the order of inner to outer.
        # Apply the context stack in reverse order, so that the innermost frame is the last to override our context.
        context_stack = reversed([d for d in django_context])
        for d in context_stack:
            context.update(d)
    return context

def render_jinja_to_string(filename, context, request=None):
    """
    `context` may be either a dictionary or a Django Context instance (incl. RequestContext).
    """
    template = env.get_template(filename)
    if request:
        context = RequestContext(request, context)
    context = to_dict_context(context)
    return template.render(**context)

def jinja_context_tag(func):
    def jinja_func(func):
        @wraps(func)
        @contextfunction
        def wrapper(context, *args, **kwargs):
            return func(to_dict_context(context), *args, **kwargs)
        return wrapper
    env.globals[func.__name__] = jinja_func(func)
    return func

################################################
#
# Template tag modules.
#
def get_jinja_tags_modules():
    """
    Returns the list of all available "jinja_tags" modules.

    It will import each one found (just to test its existence), so this can be used to load all of our Jinja tags.
    """
    modules = []
    # Ported from django.template.get_templatetags_modules
    for app_module in ['django'] + list(django_settings.INSTALLED_APPS):
        for app_path_suffix in ['.templatetags.jinja_tags', '.jinja_tags']:
            try:
                jinja_tags_module = unicode(app_module) + app_path_suffix
                import_module(jinja_tags_module)
                modules.append(jinja_tags_module)
            except ImportError, ex:
                #logger.error("loading jinja_tags @ {}{}: {}".format(unicode(app_module), app_path_suffix, ex.message))
                continue

    return modules

def load_all_jinja_tags():
    # Just calling this will cause each available tags module to be imported (and thus loaded into `env`
    # via global_tag, filter_tag etc.).
    get_jinja_tags_modules()

load_all_jinja_tags()

