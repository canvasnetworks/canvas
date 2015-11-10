'''
It is very important that this module gets imported the same way every time, to avoid duplicate entries in
sys.modules, which would execute this code multiple times and break the service overrides.
'''
from contextlib import contextmanager
import datetime
from functools import wraps
import random
import time

class TimeProvider(object):
    "Mostly the time module, but an explicitly narrowed API so we know what FakeTimeProvider needs."
    def time(self):
        return time.time()

    def today(self):
        return datetime.datetime.today()
        
    def strftime(self, *args):
        return time.strftime(*args)

    def sql_now(self, executable_name):
        if 'sqlite' in executable_name:
            return "strftime('%%' || 's', 'now')"
        elif 'mysql' in executable_name: 
            return "UNIX_TIMESTAMP(NOW())"
        else:
            raise Exception("Unsupported backend. conn.client.executable_name = %s"
                            % executable_name)

class FakeTimeProvider(object):
    def __init__(self, t=1333333333.123456):
        self.t = t

    def step(self, delta=100.0):
        self.t += delta
        
    def strftime(self, format, t=None):
        if t is None:
            t = time.localtime(self.time())
        return time.strftime(format, t)

    def time(self):
        return self.t

    def today(self):
        """ Returns the date + current time, as a datetime instance. """
        return datetime.datetime.fromtimestamp(self.t)

    def sql_now(self, executable_name):
        if 'sqlite' in executable_name or 'mysql' in executable_name:
            return str(self.t)
        else:
            raise Exception("Unsupported backend. conn.client.executable_name = %s"
                            % executable_name)

class RandomProvider(object):
    def seed(self, *args):
        random.seed(*args)

    def choice(self, lst):
        return random.choice(lst)

class FakeRandomProvider(object):
    def __init__(self, value):
        self.value = value

    def seed(self, *args):
        pass

    def choice(self, lst):
        return lst[self.value]

class FakeMetric(object):
    def __init__(self, name, alarm, category, threshold=None, ignore_from_api=False):
        self.records = []
        
    def record(self, request, **metadata):
        self.records.append((request, metadata))

class FakeMetrics(object):
    def __init__(self):
        from canvas.metrics import create_metrics, Metrics
        create_metrics(self, Metrics.names, FakeMetric)

class FakeExperimentPlacer(object):
    def __init__(self, **placements):
        self.placements = placements

    def roll(self, experiment):
        if experiment.name in self.placements:
            return experiment.branches[self.placements[experiment.name]]
        else:
            return experiment.branches['control']

def lazy_load(fun):
    """
    Use me to break circular dependencies.
    """

    prop_name = "_" + fun.__name__
    
    @property
    def lazy(self):
        try:
            return getattr(self, prop_name)
        except AttributeError:
            value = fun()
            setattr(self, prop_name, value)
            return value
    
    @lazy.setter
    def lazy(self, value):
        setattr(self, prop_name, value)
    
    return lazy

class ServicesMeta(object):
    '''
    This class is defined with the default service providers.

    When accessed, they may have been overridden via `override_service`.
    '''
    time = TimeProvider()
    random = RandomProvider()

    @lazy_load
    def metrics():
        from canvas.metrics import Metrics
        return Metrics
        
    @lazy_load
    def experiment_placer():
        from canvas.experiments import ExperimentPlacer
        return ExperimentPlacer()

Services = ServicesMeta()

@contextmanager
def override_service(name, provider, args=[], kwargs={}):
    old_instance = getattr(Services, name)
    override_instance = provider(*args, **kwargs)
    setattr(Services, name, override_instance)
    try:
        yield
    finally: 
        setattr(Services, name, old_instance)

def with_override_service(*args, **kwargs):
    '''
    Decorator version of `override_service`.
    '''
    def wrapper(func):
        @wraps(func)
        def decorator(*f_args, **f_kwargs):
            with override_service(*args, **kwargs):
                return func(*f_args, **f_kwargs)
        return decorator
    return wrapper


