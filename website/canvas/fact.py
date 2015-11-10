import time
import urllib2

from django.conf import settings

from canvas import bgwork, util
from canvas.experiments import create_experiments_for_request
import logging

def debug_fact_channel():
    from canvas.redis_models import RealtimeChannel
    return RealtimeChannel('debug_fact', 30)

def record(fact_type, request_or_user, info):
    return

    extra_info = { 'type': fact_type, 'ts': time.time()}

    if hasattr(request_or_user, 'user'):
        request = request_or_user
        user = request.user
    else:
        request = None
        user = request_or_user

    if request:
        extra_info['session_key'] = request.session.session_key
        extra_info['ip'] = request.META.get('REMOTE_ADDR')
        extra_info['utma'] = request.COOKIES.get('__utma')

        if not hasattr(request, "experiments"):
            request.experiments = create_experiments_for_request(request)
            logging.debug("Request did not have experiments ... recreating ...")

        experiments = request.experiments
    elif user:
        experiments = user.redis.experiments
    else:
        raise Exception("request_or_user is required.")

    if user.is_authenticated():
        extra_info['user'] = user.id

    if experiments:
        experiments_mapping = dict((experiment.name, branch.name) for experiment, branch in experiments.get_all_current_branches())
        if experiments_mapping:
            extra_info["experiments"] = experiments_mapping

    info = dict(info, **extra_info)

    if settings.DEBUG:
        debug_fact_channel().publish(info)

    @bgwork.defer
    def make_request():
        try:
            req = urllib2.Request("http://%s/" % settings.FACT_HOST, headers={'X-Fact-Log': util.backend_dumps(info)})
            urllib2.urlopen(req, timeout=3)
        except IOError:
            from canvas.models import Metrics
            Metrics.fact_record_fail.record(request, record_fact=False)

