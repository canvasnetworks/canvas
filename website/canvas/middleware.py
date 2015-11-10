import datetime
import os
import time
import traceback
import random
import re

from django import template
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404, HttpResponse
import django.middleware.csrf
from django.shortcuts import redirect
from django.shortcuts import render_to_response, get_object_or_404
from django.utils.html import strip_spaces_between_tags
import facebook

from apps.canvas_auth.models import User
from canvas import util, bgwork, stickers
from canvas.cache_patterns import CachedCall
from canvas.exceptions import HttpRedirect
from canvas.experiments import Experiments, create_experiments_for_request
from canvas.models import UserInfo, Metrics
from canvas.redis_models import IP
from configuration import Config
from services import Services
from django.conf import settings


def safe_middleware(cls):
    """
    Use this middleware decorator if you want to assume that a request that doesn't make it to process_request will
    not get a corresponding process_response.
    """
    token = "smt_%s_%s" % (cls.__name__, id(cls))

    unsafe_process_request = cls.process_request
    def guarded_process_request(self, request):
        try:
            result = unsafe_process_request(self, request)
        except:
            raise
        else:
            setattr(request, token, True)
            return result
    cls.process_request = guarded_process_request

    unsafe_process_response = cls.process_response
    def guarded_process_response(self, request, response):
        if hasattr(request, token):
            return unsafe_process_response(self, request, response)
        else:
            return response
    cls.process_response = guarded_process_response

    return cls


class ExceptionLogger(object):
    def process_exception(self, request, exception):
        if not isinstance(exception, Http404) and not isinstance(exception, PermissionDenied):
            util.logger.info(traceback.format_exc())
            Metrics.exception.record(request)


class ResponseGuard(object):
    """ Ensures that all views and apis return an instance of HttpResponse. """
    def process_response(self, request, response):
        if not isinstance(response, HttpResponse):
            raise TypeError("Response should be an HttpResponse. Got %s" % type(response))
        return response


class PingMiddleware(object):
    """ Special handling for the ping call. This skips the rest of the middleware. """
    def process_request(self, request):
        # If this is not a ping call, then continue through the rest of the middleware.
        if "/ping" != request.path_info:
            return

        # Handle the ping.
        import urllib
        result = urllib.urlopen('http://' + settings.SELF + '/twisted_ping').read()
        if result.lower().strip() != "twisted pong":
            raise Exception("Bad twisted response: " + result)
        return HttpResponse("pong")


class TimeDilationMiddleware(object):
    def process_request(self, request):
        time_dilation = request.user.kv.time_dilation.get()
        if time_dilation:
            sleep_amt = random.uniform(0, time_dilation)
            time_dilation_start = request.user.kv.time_dilation_start.get()
            time_dilation_end = request.user.kv.time_dilation_end.get()
            if time_dilation_start and time_dilation_end:
                progress = min(1.0, ((time.time() - time_dilation_start) / (time_dilation_end - time_dilation_start)))
                sleep_amt = random.uniform(0, (progress * time_dilation))

            time.sleep(sleep_amt)


@safe_middleware
class DeferredWorkMiddleware(object):
    def process_request(self, request):
        request.on_success = bgwork.WorkQueue()

    def process_response(self, request, response):
        if response.status_code == 200 and hasattr(request, 'on_success'):
            bgwork.defer(request.on_success.perform)
        return response


class HandleLoadBalancerHeaders(object):
    def get_x_forwarded_for_ip(self, request):
        ips = [ip.strip() for ip in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')]
        for ip in ips:
            if not ip.startswith('10.'):
                return ip
        return request.META['REMOTE_ADDR']

    def process_request(self, request):
        request.META['REMOTE_ADDR'] = self.get_x_forwarded_for_ip(request)
        if 'HTTP_X_FORWARDED_PROTO' in request.META:
            request.environ['wsgi.url_scheme'] = request.META['HTTP_X_FORWARDED_PROTO']


class FacebookMiddleware(object):
    def process_request(self, request):
        request.fb_app_id = settings.FACEBOOK_APP_ID


class ImpersonateMiddleware(object):
    def process_request(self, request):
        if "__impersonate" in request.GET and request.user.is_staff:
            request.session['impersonate_name'] = request.GET["__impersonate"]
        elif "__unimpersonate" in request.GET:
            del request.session['impersonate_name']
        if 'impersonate_name' in request.session and request.user.is_staff:
            request.user = get_object_or_404(User, username=request.session['impersonate_name'])


class UploadifyIsALittleBitchMiddleware(object):
    def process_request(self, request):
        if (request.method == 'POST'):
            if request.POST.has_key('csrfmiddlewaretoken'):
                request.COOKIES["csrftoken"] = request.POST['csrfmiddlewaretoken']
                # 'good_referer' from django csrf middleware
                request.META['HTTP_REFERER'] = 'https://%s/' % request.get_host()
            if request.POST.has_key('sessionid'):
                request.COOKIES['sessionid'] = request.POST['sessionid']


class Django403Middleware(object):
    """ Renders to 403.html unless it's an AJAX request. """
    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            if not request.is_ajax():
                try:
                    t = template.loader.get_template('403.html')
                    context = {'request': request}
                    return HttpResponseForbidden(t.render(template.RequestContext(request, context)))
                except template.TemplateDoesNotExist, e:
                    return HttpResponseForbidden('403 Forbidden')


# https://github.com/aehlke/django-catnap/blob/master/catnap/middleware.py
class HttpExceptionMiddleware(object):
    '''
    Catches `HttpException` exceptions, which contain a `response` property, which should be a subclass instance
    of HttpResponse.

    This middleware simply returns the `response` member.
    '''
    def process_exception(self, request, exception):
        if (hasattr(exception, 'response') and isinstance(exception.response, HttpResponse)):
            return exception.response


class HttpRedirectExceptionMiddleware(object):
    """ Catches HttpRedirect exceptions and redirects to their target. """
    def process_exception(self, request, exception):
        if isinstance(exception, HttpRedirect):
            return HttpResponseRedirect(exception.redirect_to)


def times():
    raw = os.times()
    return [raw[0], raw[1], raw[4]] # We don't care about child utime/stime


@safe_middleware
class RedirectToHttpsMiddleware(object):
    def process_request(self, request):
        def redirect_https():
            return HttpResponseRedirect('https://' + settings.DOMAIN + request.get_full_path())

        if not request.is_secure():
            # Check for a secure_only cookie
            secure_only_cookie = request.COOKIES.get('secure_only', 'false').strip().lower() == 'true'
            # Check the user KV for the Force HTTPS setting.
            secure_only_kv = request.user.is_authenticated() and request.user.kv.secure_only.get()

            if secure_only_cookie or secure_only_kv:
                return redirect_https()

    def process_response(self, request, response):
        # Make sure the cookies are in sync with the secure_only setting.
        if request.user.is_authenticated():
            if request.user.kv.secure_only.get():
                response.set_cookie('secure_only', 'true')
            else:
                response.delete_cookie('secure_only')
        return response


class SandboxMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            if 'sandbox' in request.user_kv:
                if request.META['PATH_INFO'].startswith('/api'):
                    # Deactivated users cannot access anything outside of the sandbox. 403 Forbidden any other
                    # request.
                    if not request.user.is_active:
                        return HttpResponseForbidden(util.client_dumps({'reason': 'deactivated'}))
                    # Otherwise fall though and serve API requests, user is just warned.
                elif not request.META['PATH_INFO'].startswith(request.user_kv['sandbox']):
                    # Request for a page outside of the sandbox, redirect to the sandbox.
                    return HttpResponseRedirect(request.user_kv['sandbox'])
            elif not request.user.is_active:
                # Deactivated user with no sandbox, log them out, boot them to /
                logout(request)
                return HttpResponseRedirect('/')


class StaffOnlyMiddleware(object):
    def process_request(self, request):
        if (request.META['PATH_INFO'].startswith('/staff')
                and not (request.user.is_authenticated()
                         and request.user.is_staff)):
            return HttpResponseForbidden(util.client_dumps({'reason': 'staff_only'}))


class GlobalExperimentMiddleware(object):
    def process_request(self, request):
        # Place users into null_hypothesis, but don't actually branch on the result
        request.experiments.get(Experiments.null_hypothesis)


class IPHistoryMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            ip = request.META['REMOTE_ADDR']

            int_ip = util.ip_to_int(ip)
            request.user.redis.ip_history.bump(int_ip)
            IP(int_ip).user_history.bump(request.user.id)


@safe_middleware
class RequestSetupMiddleware(object):
    def process_request(self, request):
        request._start_times = times()
        CachedCall.inprocess_cache.flush()

        # Associate the correct experiments backend for this request
        request.experiments = create_experiments_for_request(request)

        request.user_kv = {} #TODO: probably use a FrozenDict when we can write to the authenticated user_kv.
        if request.user.is_authenticated():
            request.user_kv = request.user.redis.user_kv.hgetall()

        request.config = Config

        # As a side effect, sets the CSRF cookie
        django.middleware.csrf.get_token(request)

    def process_response(self, request, response):
        if hasattr(request, "user") and request.user.is_authenticated():
            if not 'username' in request.COOKIES:
                # For easy debugging via request vars, etc
                response.set_cookie('username', request.user.username)

        metric_info = {'path': request.path, 'referrer': request.META.get('HTTP_REFERER')}

        end_times = times()

        # True story: AttributeError: 'WSGIRequest' object has no attribute '_start_times'
        if hasattr(request, '_start_times'):
            data = [(label, (end - start) * 1000)
                    for (label, start, end)
                    in zip("use", request._start_times, end_times)]
            response['X-Timing'] = " ".join(["%s%0.2fms" % row for row in data])
            metric_info.update(data)

        if hasattr(request, '_sql_queries'):
            queries = request._sql_queries
            metric_info['sql'] = data = (len(queries), sum(queries), max(queries))
            response['X-SQL'] = "c:%s t:%0.2fms max:%0.2fms" % data

        if hasattr(request, '_redis_commands'):
            commands = request._redis_commands
            metric_info['redis'] = data = (len(commands), sum(commands), max(commands))
            response['X-Redis'] = "c:%s t:%0.2fms max:%0.2fms" % data

        # Record a metric for page views.
        # We need to figure out if this is a logged in or out view.
        # Api calls should not record a page view metric, but their own.
        metric_record = None
        if "/api/" not in request.path and "/ping" not in request.path:
            metric_record = (Services.metrics.view.record if request.user.is_authenticated()
                             else Services.metrics.logged_out_view.record)
        elif request.path.startswith('/api/'):
            metric_record = Services.metrics.api_call.record

        if metric_record is not None:
            @bgwork.defer
            def record_view():
                metric_record(request, **metric_info)

        if response.status_code == 404:
            Metrics.file_not_found.record(request, **metric_info)

        return response


class SeasonalStickerMiddleware(object):
    def process_request(self, request):
        # Just change these vars as needed now

        if not request.user.is_authenticated():
            return

        event = stickers.get_active_event()
        if not event:
            return

        if float(request.user_kv.get(event.name, 0)) == 0:
            for sticker in event.stickers:
                request.user.kv.stickers[sticker.type_id].set(event.sticker_counts[sticker])
            request.user.redis.user_kv.hset(event.name, time.time())
            request.user_kv = request.user.redis.user_kv.hgetall()


RE_MULTISPACE = re.compile(r" {2,}")
RE_MULTIBOTH = re.compile(r"\n+ +\n+")
RE_NEWLINE = re.compile(r"\n{2,} *")


class MinifyHTMLMiddleware(object):
    def process_response(self, request, response):
        if 'text/html' in response['Content-Type'] and settings.MINIFY_HTML:
            #response.content = strip_spaces_between_tags(response.content)
            response.content = RE_MULTISPACE.sub(" ", response.content)
            response.content = RE_MULTIBOTH.sub("\n", response.content)
            response.content = RE_NEWLINE.sub("\n", response.content)
        return response


# Forked from Django to allow me to HTTPS-only the staff session
class SessionMiddleware(object):
    def process_request(self, request):
        from django.conf import settings
        from django.utils.importlib import import_module
        engine = import_module(settings.SESSION_ENGINE)
        session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME, None)
        request.session = engine.SessionStore(session_key)

    def process_response(self, request, response):
        from django.conf import settings
        from django.utils.http import cookie_date
        from django.utils.cache import patch_vary_headers

        # If request.session was modified, or if the configuration is to save the session every time, save the
        # changes and set a session cookie.

        secure = settings.SESSION_COOKIE_SECURE or None

        try:
            accessed = request.session.accessed
            modified = request.session.modified
        except AttributeError:
            pass
        else:
            if accessed:
                patch_vary_headers(response, ('Cookie',))
            if modified or settings.SESSION_SAVE_EVERY_REQUEST:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires_time = time.time() + max_age
                    expires = cookie_date(expires_time)
                # Save the session data and refresh the client cookie.
                request.session.save()
                response.set_cookie(settings.SESSION_COOKIE_NAME,
                                    request.session.session_key, max_age=max_age,
                                    expires=expires, domain=settings.SESSION_COOKIE_DOMAIN,
                                    path=settings.SESSION_COOKIE_PATH,
                                    secure=secure)

                if secure:
                    response.set_cookie('secure_only', 'true', max_age=(20*365*24*60*60)) # 20 years :-O

        return response

