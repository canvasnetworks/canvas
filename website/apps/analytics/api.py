from canvas import fact
from canvas.api_decorators import api_decorator
from canvas.exceptions import ServiceError
from canvas.metrics import Metrics

urlpatterns = []
api = api_decorator(urlpatterns)

@api('metric/record')
def metric_record(request, name, info={}):
    info = dict((str(key), value) for (key, value) in info.items())

    metric = Metrics.all.get(name)
    if not metric:
        raise ServiceError("Invalid metric name")

    if metric.ignore_from_api:
        return

    metric.record(request, **info)

@api('fact/record')
def record_fact(request, type, info={}):
    fact.record(type, request, info)

