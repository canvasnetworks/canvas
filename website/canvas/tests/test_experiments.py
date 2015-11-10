from canvas.tests.tests_helpers import create_user, FakeRequest, CanvasTestCase, AnonymousUser
from canvas.experiments import (migrate_from_request_to_user, force_into_branch, Experiments, RequestExperiments,
                                UserExperimentsBackend, Experiment, ForceExperimentMiddleware)
from canvas.models import Metrics, UserInfo
from canvas.redis_models import redis

class TestExperiments(CanvasTestCase):
    def test_migrate_experiments_from_request_to_user(self):
        request = FakeRequest(AnonymousUser())
        user = create_user()
        request.experiments.get(Experiments.forced_into_control)

        migrate_from_request_to_user(request, user)

        branches = list(user.redis.experiments.get_all_current_branches())
        self.assertEqual([(Experiments.forced_into_control, Experiments.forced_into_control.branches["control"])], branches)

class BaseRedisExperiments(object):
    def test_experiment_placement(self):
        request = self.request()
        branch = request.experiments.get(Experiments.forced_into_control)
        self.assertEqual(branch.name, "control")

    def test_get_all_branches_return_nothing_if_not_in_branch(self):
        request = self.request()
        branches = list(request.experiments.get_all_current_branches())
        self.assertEqual(branches, [])

    def test_get_all_branches_returns_placed_experiment(self):
        request = self.request()
        branch = request.experiments.get(Experiments.forced_into_control)
        branches = list(request.experiments.get_all_current_branches())
        self.assertEqual([(Experiments.forced_into_control, Experiments.forced_into_control.branches["control"])], branches)

class TestUserRedisExperiments(CanvasTestCase, BaseRedisExperiments):
    def request(self):
        return FakeRequest(create_user())

class TestSessionExperiments(CanvasTestCase, BaseRedisExperiments):
    def request(self):
        return FakeRequest(AnonymousUser())

class TestSimplifiedExperimentAPI(CanvasTestCase):
    def test_is_in_control(self):
        self.assertTrue(FakeRequest().experiments.is_in("forced_into_control", "control"))

    def test_is_in_experimental(self):
        self.assertTrue(FakeRequest().experiments.is_in("forced_into_experimental"))

    def test_bad_experiment_name_raises(self):
        with self.assertRaises(ValueError):
            FakeRequest().experiments.is_in("nope")

    def test_bad_branch_name_raises(self):
        with self.assertRaises(ValueError):
            FakeRequest().experiments.is_in("forced_into_control", "NOPE")

    def test_get_allows_strings(self):
        self.assertEqual(FakeRequest().experiments.get("forced_into_control"), "control")

    def test_get_rejects_bad_experiment_name(self):
        with self.assertRaises(ValueError):
            FakeRequest().experiments.get("nope")

    def test_logged_out_only(self):
        self.assertTrue(FakeRequest(AnonymousUser()).experiments.is_in('logged_out_only', 'experimental'))
        self.assertTrue(FakeRequest(create_user()).experiments.is_in('logged_out_only', 'control'))

    def test_logged_in_only(self):
        self.assertTrue(FakeRequest(AnonymousUser()).experiments.is_in('logged_in_only', 'control'))
        self.assertTrue(FakeRequest(create_user()).experiments.is_in('logged_in_only', 'experimental'))

    def test_staff_gets_staff_branch(self):
        staff_request = FakeRequest(create_user(staff=True))
        self.assertTrue(staff_request.experiments.is_in('forced_into_control', 'experimental'))

    def test_forced_into_experiment(self):
        request = FakeRequest()
        force_into_branch(request, "forced_into_control", "experimental")

        self.assertTrue(request.experiments.is_in("forced_into_control", "experimental"))

    def test_staff_can_be_forced_into_experiment(self):
        request = FakeRequest(create_user(staff=True))
        force_into_branch(request, "forced_into_experimental", "control")

        self.assertTrue(request.experiments.is_in("forced_into_experimental", "control"))

    def test_logged_in_only_experiments_return_control_even_if_forced_when_logged_out(self):
        request = FakeRequest(AnonymousUser())
        force_into_branch(request, "logged_in_only", "experimental")

        self.assertTrue(request.experiments.is_in("logged_in_only", "control"))

    def test_force_into_experiment_middleware(self):
        request = FakeRequest(GET="force_experiment=forced_into_control:experimental")
        fem = ForceExperimentMiddleware()
        fem.process_request(request)

        self.assertTrue(request.experiments.is_in('forced_into_control', 'experimental'))

class TestExperimentObject(CanvasTestCase):
    def test_reject_experiment_without_control(self):
        with self.assertRaises(ValueError):
            Experiment("foo", branches=[("foo", 1), ("bar", 1)], staff_branch="foo")

    def test_reject_experiment_without_default_branch(self):
        with self.assertRaises(ValueError):
            Experiment("foo", default_branch="nope")

    def test_reject_bad_staff_branch(self):
        with self.assertRaises(ValueError):
            Experiment("foo", staff_branch="foobar")

    def test_ignore_staff_branch_for_logged_out_only(self):
        experiment = Experiment("foo", logged_out_only=True, staff_branch="foobar")
        self.assertEqual(experiment.staff_branch, None)

    def test_reject_both_logged_out_and_logged_in_only(self):
        with self.assertRaises(ValueError):
            Experiment("bar", logged_in_only=True, logged_out_only=True)

    def test_reject_floating_point_rollout_values(self):
        with self.assertRaises(ValueError):
            Experiment("x", rollout=0.5)

    def test_reject_integer_rollout_values_outside_of_0_to_100(self):
        with self.assertRaises(ValueError):
            Experiment("x", rollout=101)
