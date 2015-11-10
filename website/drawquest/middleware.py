from django.contrib.auth import logout
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404, HttpResponse

from canvas import util, bgwork
from canvas.exceptions import DeactivatedUserError
from drawquest.apps.drawquest_auth.inactive import inactive_user_http_response


class PingMiddleware(object):
    """ Special handling for the ping call. This skips the rest of the middleware. """
    def process_request(self, request):
        # If this is not a ping call, then continue through the rest of the middleware.
        if "/ping" != request.path_info:
            return

        return HttpResponse("pong")


class DrawquestShimMiddleware(object):
    """ Shim for integrating into the Canvas codebase. """
    def process_request(self, request):
        request.is_mobile = False


class StaffOnlyMiddleware(object):
    def process_request(self, request):
        if (request.META['PATH_INFO'].startswith('/admin')
                and not (request.user.is_authenticated()
                         and request.user.is_staff)):
            return HttpResponseRedirect('/login')


class InactiveUserMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated() and not request.user.is_active:
            if request.META['PATH_INFO'].startswith('/api'):
                #TODO this is duplicating _handle_json_response work
                return inactive_user_http_response()
            else:
                logout(request)
                return HttpResponseRedirect('/')

class Log403(object):
    def process_response(self, request, response):
        if response.status_code == 403 and request.META.get('HTTP_X_SESSIONID'):
            import traceback
            import sys
            stack = str(request.path_info) + '\n'

            stack += request.raw_post_data + '\n'

            if request.user.is_authenticated():
                stack += request.user.username + '\n'

            import time
            stack += str(time.time()) + '\n'

            import re
            regex_http_          = re.compile(r'^HTTP_.+$')
            regex_content_type   = re.compile(r'^CONTENT_TYPE$')
            regex_content_length = re.compile(r'^CONTENT_LENGTH$')

            request_headers = {}
            for header in request.META:
                if regex_http_.match(header) or regex_content_type.match(header) or regex_content_length.match(header):
                    request_headers[header] = request.META[header]

            stack += '\n'.join('{}: {}'.format(k,v) for k,v in request_headers.items()) + '\n'

            import traceback
            tb = traceback.format_exc()
            stack += unicode(tb)
            stack += '\n'.join('{}: {}'.format(k,v) for k,v in request.COOKIES.items()) + '\n'
            stack += '\n' + unicode(response.content)

            stack += '\n'.join(traceback.format_exception(*sys.exc_info()))
            from django.core.mail import send_mail
            send_mail('403 stack trace', stack, 'passwordreset@example.com',
                      ['alex@example.com'], fail_silently=False)
        return response

