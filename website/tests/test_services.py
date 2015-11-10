import datetime
import time

from canvas.tests.tests_helpers import CanvasTestCase, create_user
from canvas.experiments import Experiments
from services import Services, override_service, with_override_service, FakeTimeProvider, FakeMetrics, FakeExperimentPlacer

class TestTimeService(CanvasTestCase):
    def test_context_overrides(self):
        self.assertFalse(isinstance(Services.time, FakeTimeProvider))
        with override_service('time', FakeTimeProvider):
            self.assertTrue(isinstance(Services.time, FakeTimeProvider))
            
    def test_with_context_override_decorator(self):
        self.assertFalse(isinstance(Services.time, FakeTimeProvider))
        
        @with_override_service('time', FakeTimeProvider)
        def get_time():
            return Services.time
                
        time = get_time()            
        self.assertTrue(isinstance(time, FakeTimeProvider))

    def test_today(self):
        with override_service('time', FakeTimeProvider):
            today = datetime.datetime.today()
            today = datetime.datetime(*today.timetuple()[:6])
            now = time.mktime(today.timetuple())
            Services.time.t = now
            self.assertEqual(Services.time.today(), today)

            
class TestFakeTime(CanvasTestCase):
    def test_step(self):
        ft = FakeTimeProvider(t=100)
        self.assertEqual(ft.time(), 100)
        
        ft.step(1)
                
        self.assertEqual(ft.time(), 101)
        
    def test_strftime_uses_fake_time(self):
        ft = FakeTimeProvider(t=123456789)
        self.assertEqual(ft.strftime("%s"), "123456789")
        
    def test_faketime_default_value_is_strftime_valid(self):
        ft = FakeTimeProvider()
        
        # Calling this shouldn't raise: ValueError: timestamp out of range for platform time_t
        ft.strftime("%s") 

class TestFakeMetrics(CanvasTestCase):
    def test_two_overrides_dont_collide_with_eachother(self):
        with override_service('metrics', FakeMetrics):
            Services.metrics.view.record("1")
            self.assertEqual([("1", {})], Services.metrics.view.records)

        with override_service('metrics', FakeMetrics):
            Services.metrics.view.record("2")
            self.assertEqual([("2", {})], Services.metrics.view.records)

class TestFakeExperimentPlacer(CanvasTestCase):
    def test_can_force_user_into_experimental(self):
        user = create_user()

        with override_service('experiment_placer', FakeExperimentPlacer, kwargs={'null_hypothesis': 'experimental'}):
            self.assertEqual('experimental', user.redis.experiments.get(Experiments.null_hypothesis).name)

    def test_can_force_user_into_control(self):
        user = create_user()

        with override_service('experiment_placer', FakeExperimentPlacer, kwargs={'null_hypothesis': 'control'}):
            self.assertEqual('control', user.redis.experiments.get(Experiments.null_hypothesis).name)
