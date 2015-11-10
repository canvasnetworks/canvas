from functools import wraps

from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from canvas import util, knobs, browse
from canvas.api_decorators import json_service
from canvas.exceptions import ServiceError
from canvas.metrics import Metrics
from canvas.redis_models import RateLimit


def short_id(id):
    return util.base36encode(id)

def long_id(short_id):
    return util.base36decode(short_id)

def check_rate_limit(request):
    return RateLimit('apicall:' + request.META['REMOTE_ADDR'], knobs.PUBLIC_API_RATE_LIMIT).allowed()

def public_api_method(f):
    @csrf_exempt
    @json_service
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            request = kwargs.get('request') or args[0]

            if not check_rate_limit(request):
                Metrics.api_rate_limited.record(request)
                raise ServiceError("Slow down there, cowboy!")

            payload = request.JSON
            ids = payload.get('ids')

            if ids and len(ids) > knobs.PUBLIC_API_MAX_ITEMS:
                Metrics.api_items_limited.record(request)
                raise ServiceError("Max items per query limited to {0}".format(knobs.PUBLIC_API_MAX_ITEMS))

            kwargs['payload'] = payload

            ret = f(*args, **kwargs)
            Metrics.api_successful_request.record(request)

            if not ret:
                Metrics.api_documentation.record(request)
                return {'documentation': f.__doc__}
            else:
                return ret

        except ServiceError as se:
            Metrics.api_failed_request.record(request)
            raise se

    return wrapper
