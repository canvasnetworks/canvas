from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotAllowed, HttpResponseRedirect

from canvas.api_decorators import is_api
from django.conf import settings

def view_guard(guard):
    """
    It will check if the view has already been decorated with `@api` - if it has, this throws an exception, 
    since it means @api is not the outermost decorator.
    """
    def decorator(view):
        if is_api(view):
            raise TypeError("Cannot decorate a function that has already been decorated with @api.")

        @wraps(view)
        def view_wrapper(request, *args, **kwargs):
            maybe_response = guard(request)
            if maybe_response:
                return maybe_response
            return view(request, *args, **kwargs)            

        # For ArgSpec's sake.
        if not hasattr(view_wrapper, '_original_function'):
            view_wrapper._original_function = view

        return view_wrapper
    return decorator

@view_guard
def require_secure(request):
    if not settings.HTTPS_ENABLED:
        return

    if request.META.get('HTTP_X_FORWARDED_PROTO') != 'https':
        return HttpResponseRedirect('https://' + settings.DOMAIN + request.get_full_path())

@view_guard
def require_POST(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(['POST'])

@view_guard
def require_user(request):
    if not request.user.is_authenticated():
        raise PermissionDenied()

@view_guard
def require_staff(request):
    if not request.user.is_authenticated() or not request.user.is_staff:
        raise PermissionDenied()

