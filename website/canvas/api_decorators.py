from functools import wraps

from django.http import HttpResponse
from django.core.exceptions import ValidationError
import django.views.decorators.csrf
import yaml
from django.conf import settings

from canvas import url_util
from canvas.util import ArgSpec, simple_decorator, loads, client_dumps, JSONDecodeError
from canvas.exceptions import ServiceError, DeactivatedUserError

api_functions = set()

def ServiceResponse(request, response, **kwargs):
    """
    Serializes the response to primarily JSON, but you can force it to produce YAML by sending a format=yaml request
    variable.
    """
    formatted_response = client_dumps(response)
    if request.POST.get("format") == "yaml":
        formatted_response = yaml.safe_dump(loads(formatted_response), default_flow_style=False)
    # Allows us to force a mimetype in a request arg.
    mimetype = request.POST.get("force_mimetype", 'application/json')
    return HttpResponse(formatted_response, mimetype, **kwargs)

def JSONPResponse(request, response, **kwargs):
    callback = request.GET.get('callback', "callback")
    if not callback.replace('_', '').isalnum():
        raise ServiceError()
    return HttpResponse('%s(%s);' % (callback, client_dumps(response)), mimetype="application/javascript", **kwargs)

def json_response(view):
    @wraps(view)
    def view_wrapper(request, *args, **kwargs):
        return _handle_json_response(view, ServiceResponse, request, *args, **kwargs)
    return view_wrapper

def _handle_json_response(view, json_response_processor, request, *args, **kwargs):
    status_code = None
    try:
        response = view(request, *args, **kwargs)
    except (ServiceError, ValidationError, DeactivatedUserError,), se:
        response = se.to_json()
        status_code = getattr(se, 'status_code', None)
    else:
        if response is None:
            response = {}
        if isinstance(response, dict):
            response['success'] = True
    # If the response is not a dict, we're not going to serialize it as JSON since our JSON
    # services expect a "success" key.
    #
    # This is primarily so that we can handle returning an HTTP response from the view, for
    # redirects and the like.
    if isinstance(response, dict):
        response_kwargs = {}
        if status_code:
            response_kwargs['status_code'] = status_code
        return json_response_processor(request, response, **response_kwargs)
    return response

def _bad_json_view(*args, **kwargs):
    raise ServiceError("malformed json")

def _json_service_wrapper(json_response_processor, view):
    def view_wrapper(request, *args, **kwargs):
        try:
            request.JSON = loads(request.raw_post_data) if request.raw_post_data else {}
        except JSONDecodeError:
            temp_view = _bad_json_view
        else:
            temp_view = view

        return _handle_json_response(temp_view, json_response_processor, request, *args, **kwargs)
    return view_wrapper

#TODO use functools.wraps instead of simple_decorator
@simple_decorator        
def json_service(view):
    return _json_service_wrapper(ServiceResponse, view)

#TODO use functools.wraps
def public_jsonp_service(view):
    """
    More explicitly named to call attention to the extra little p
    """
    return _json_service_wrapper(JSONPResponse, view)

def is_api(view):
    return getattr(view, 'is_api', False)

def api_response_wrapper(public_jsonp=False, csrf_exempt=False):
    serializer = public_jsonp_service if public_jsonp else json_service
    csrf_wrapper = django.views.decorators.csrf.csrf_exempt if (csrf_exempt or settings.API_CSRF_EXEMPT) else lambda f: f
    return csrf_wrapper(serializer)

def inner_api(url_decorator, force_csrf_exempt=False):
    def api(url, public_jsonp=False, skip_javascript=False, async=True, csrf_exempt=False):
        """
        `url` is a static URL endpoint, not a regex pattern.

        Requires JSON payloads in the request's raw POST data (which doesn't need to be used by the view, but the
        POST headers can't be used for anything else.) `request.GET` is still usable (for when it makes XSS easier),
        but this decorator doesn't help with that by generating anything in canvas_api.js for it, as it does for the
        JSON parameters.

        This also doesn't support *args or **kwargs inside the API view's arguments yet (i.e. it won't generate
        anything in the JS API for these.) It does support explicitly named args and kwargs though. The kwargs are
        used to provide default values to optional params (or simply to make them optional without a default).

        The order of args in an API view's arg list doesn't actually matter (besides `request` being first), since
        the JS API sends everything as a JSON dictionary of arg name, value pairs (which is unordered.)

        If `public_jsonp` is True, this will return a JSONP response, and will work with GET. This is False by
        default -- the response is serialized into JSON, not JSONP, and POST is required.

        NOTE:
            This *must* be the first (outermost) decorator on the view.
        """
        response_wrapper = api_response_wrapper(public_jsonp=public_jsonp, csrf_exempt=(csrf_exempt or force_csrf_exempt))

        def decorator(func):
            try:
                func.url_name = u'api-{0}-{1}'.format(func.__module__, func.__name__)
            except AttributeError:
                func.url_name = None

            # We assume the function's arg specs don't change at runtime. Seems to be a reasonable assumption. If we
            # couldn't assume that, then our JS API could diverge from the actual function signatures. We can't have
            # that happening. So we just precompute it here.
            if not getattr(func, 'arg_spec', None):
                func.arg_spec = ArgSpec(func)

            if not public_jsonp:
                from canvas.view_guards import require_POST
                func = require_POST(func)

            # Mark it as an API.
            func.is_api = True

            func.async = async

            if not skip_javascript:
                api_functions.add((func.__name__, func))

            @url_decorator(r'^' + url + r'$', name=func.url_name)
            @response_wrapper
            @wraps(func)
            def wrapped_view(request):
                # JSON or REQUEST. The latter is to support the API console.
                payload = request.JSON
                if not payload:
                    try:
                        payload = request.REQUEST
                    except AttributeError:
                        pass
                args, kwargs = [], {}

                # Skip the `request` arg.
                for arg_name in func.arg_spec.args[1:]:
                    try:
                        args.append(payload[arg_name])
                    except KeyError:
                        raise ServiceError("Request payload is missing a required parameter: " + arg_name)

                for kwarg_name in func.arg_spec.kwargs.iterkeys():
                    if kwarg_name in payload:
                        kwargs[kwarg_name] = payload[kwarg_name]

                return func(request, *args, **kwargs)
            return wrapped_view
        return decorator
    return api

def api_decorator(urls):
    """ Returns an API decorator for the given URL space. """
    url_decorator = url_util.url_decorator(urls)
    return inner_api(url_decorator)

