from cachecow.decorators import cached_view
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from canvas.util import ArgSpec, client_dumps, loads


def _response_gatekeeper(response):
    if isinstance(response, dict):
        return response.get('success', True)
    return True

def cached_api(*args, **kwargs):
    """
    Only works on API endpoints with csrf_exempt=True and public_jsonp=False.
    """
    def decorator(func):
        kwargs['request_gatekeeper'] = lambda request: not getattr(cached_view, 'never_cache', False)
        kwargs['response_gatekeeper'] = _response_gatekeeper

        def response_wrapper(ret):
            ret = loads(ret)
            ret['success'] = True
            ret = client_dumps(ret)
            return HttpResponse(ret, 'application/json')

        cache_func = cached_view(*args,
                                 cached_response_wrapper=response_wrapper,
                                 serializer=client_dumps,
                                 **kwargs)(func)
        cache_func.arg_spec = ArgSpec(func)

        return cache_func
    return decorator

