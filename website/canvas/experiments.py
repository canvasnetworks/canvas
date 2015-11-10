from canvas.redis_models import RedisHash, RedisSet
from canvas.funnels import Funnels
from services import Services
from django.conf import settings

class ExperimentBranch(object):
    def __init__(self, experiment, name, weight):
        self.experiment = experiment
        self.name = name
        self.weight = weight

    def __eq__(self, other):
        return self.name == other.name and self.experiment == other.experiment

    users = property(lambda self: RedisSet('experiment:%s:%s' % (self.experiment.name, self.name)))

class Experiment(object):
    def __init__(self,
                 name,
                 branches = [('control', 1), ('experimental', 1)],
                 rollout = 100,
                 logged_in_only = False,
                 logged_out_only = False,
                 default_branch = "control",
                 staff_branch = 'experimental',
                 metrics = []):

        assert not name.startswith("_"), "Reserved namespace _*"
        assert name not in ('all', 'add', 'names')

        self.name = name
        self.branches = dict([(name, ExperimentBranch(self, name, weight)) for (name, weight) in branches])
        self.__dict__.update(self.branches)

        if default_branch not in self.branches:
            raise ValueError("Experiments must have a control branch %r" % branches)
        self.default_branch = self.branches[default_branch]

        # Use the get arg to force yourself into the experiment if you want to test a logged_out_only experiment
        # while logged-in as staff.
        if not logged_out_only:
            if staff_branch not in self.branches:
                raise ValueError("Staff branch not in branches (%s)" % staff_branch)
            self.staff_branch = self.branches[staff_branch]
        else:
            self.staff_branch = None

        if logged_in_only and logged_out_only:
            raise ValueError("Pass only one of logged_in_only or logged_out_only.")
        self.logged_in_only = logged_in_only
        self.logged_out_only = logged_out_only

        if rollout not in range(101):
            raise ValueError("Rollout must be an integer in the range [0,100]")
        self.rollout = rollout

        self.metrics = metrics

class ExperimentPlacer(object):
    @staticmethod
    def roll(experiment):
        """ Roll the experiment dice. """
        slots = []
        for branch in experiment.branches.values():
            # Each branch gets as many slot entries as its weight.
            slots += [branch] * branch.weight

        random = Services.random
        random.seed()
        # Choose a branch according to weight.
        return random.choice(slots)

class ExperimentSet(object):
    def __init__(self, *experiments):
        self.all = []
        self.by_name = {}

        for experiment in experiments:
            self.add(experiment)

    def add(self, experiment):
        setattr(self, experiment.name, experiment)
        self.by_name[experiment.name] = experiment
        self.all.append(experiment)

class DEPRECATED_Experiments(object):
    """
    USAGE:
        For session backed (logged out) and redis backed (logged in) experiments, this picks the right one:

        request.experiments.get(Experiments.simplified_design).name == "control"

        If you only have a logged in user:

        user.redis.experiments.get(Experiments.simplified_design).name == "control"
    """
    names = (
        # Don't delete things, just comment them out. We don't want to accidentally reuse an experiment name (would collide with existing redis data)
        # Third parameter is current timestamp when you push the experiment live (so we know who are new users and who are old users)
        #('welcome_mat', [('control', 1), ('experimental', 1)]),
        #('header_v2', [('control', 1), ('experimental', 1)]),
        #('header_v3', [('control', 1), ('experimental', 1)]),
        #('landing_content', [('control', 1), ('best', 1), ('top', 1)]),
        #('landing_directory', [('control', 1), ('experimental', 1)]),
        #('simplified_design', [('control', 1), ('experimental', 1)]),
        #('second_click_teasers', [('control', 1), ('experimental', 1)]),
        #('sticker_attract_mode', [('control', 1), ('experimental', 1)]),
        #('new_signup_prompt', [('control', 1), ('experimental', 1)]),
        #('new_sticker_widget', [('control', 1), ('experimental', 1)]),
        #('seasonal_stickers', [('control', 1), ('experimental', 1)]),
        #('server_side_rendering', [('control', 1), ('experimental', 1)]),
        #('server_side_rendering_with_threads', [('control', 1), ('experimental', 1)]),
        #('logged_out_stickering', [('control', 1), ('experimental', 1)]),
        #('logged_out_stickering_taketwo', [('control', 1), ('experimental', 1)]),
        # As a sanity check of our A/B system to ensure that if we don't change anything, both branches yield similar results.
        #('null_hypothesis', [('control', 1), ('experimental', 1)]),
        #('server_side_threads', [('control', 1), ('experimental', 1)]),
        #('logged_out_replies_with_attract', [('control', 1), ('experimental', 1)]),
        #('logged_out_content', [('control', 1), ('order_by_reply_count', 1), ('order_by_time_plus_log_stickers', 1), ('deweight_bad_thumbnails', 1)]),
        #('email_notifications', [('control', 1), ('experimental', 1)]),
        #('logged_out_more_sharing', [('control', 1), ('experimental', 1)]),
        #('facebook_not_required2', [('control', 1), ('experimental', 1)]),
        #('welcome_window', [('control', 1), ('experimental', 1)]),
        #('twentyfour_hour_email', [('control', 1), ('experimental', 1)]),
        #('landing_page_clickthrough', [('control', 1), ('blog_content_simple_nav', 1), ('blog_content_control_nav', 1), ('control_content_no_nav', 1), ('remix_splash', 1)]),
        # DEPRECATED
    )

remix_share_metrics = [
    'flow_start',
    'flow_page_ready',
    'flow_click_remix',
    'flow_remix_tool_used',
    'flow_submitted_remix',
    'flow_signup',
    'flow_share',
    'flow_finished',
]

DeadExperiments = ExperimentSet(
    Experiment(
        'logged_out_content',
        branches = [
            ('control', 1),
            ('order_by_reply_count', 1),
            ('order_by_time_plus_log_stickers', 1),
            ('deweight_bad_thumbnails', 1),
        ],
        logged_out_only = True,
    ),
    Experiment('twentyfour_hour_email'),
    Experiment(
        'post_thread_button_copy2',
        branches = [('control', 0), ('a', 1), ('b', 1)],
        staff_branch = 'a',
        metrics = [
            'attempted_remix',
            'posted_thread',
            'start_remix_from_disk',
            'start_remix_from_draw',
            'start_remix_from_url',
            'post_thread_page_view',
        ],
    ),
    Experiment(
        'landing_page_clickthrough_2',
        metrics=[
            'dummy_page_view',
            'dummy_page_scroll',
            'dummy_page_click',
        ],
        logged_out_only = True,
    ),
    Experiment(
        'signup_copy',
        logged_out_only = True,
    ),
    Experiment(
        'remix_inline',
        rollout = 0,
    ),
    Experiment(
        'remix_share_stumbleupon',
        rollout = 100,
        branches = [('control', 0), ('experimental', 1)],
        logged_out_only = True,
        metrics = remix_share_metrics,
    ),
    Experiment(
        'remix_share_google',
        rollout = 100,
        branches = [('control', 0), ('experimental', 1)],
        logged_out_only = True,
        metrics = remix_share_metrics,
    ),
    Experiment(
        'remix_share_canvas',
        rollout = 100,
        branches = [('control', 0), ('experimental', 1)],
        logged_out_only = True,
        metrics = remix_share_metrics,
    ),
    Experiment(
        'new_nav',
        rollout = 100,
        logged_out_only = True,
        default_branch = 'experimental',
    ),
    Experiment(
        'new_thread_pages',
        rollout = 100,
        logged_out_only = True,
        metrics = remix_share_metrics + ['logged_out_thread_reply_input_clicked'],
    ),
    Experiment(
        'new_logged_out_header',
        rollout = 100,
        logged_out_only = True,
    ),
    Experiment(
        'new_thread_pages_v2',
        rollout = 100,
        logged_out_only = True,
        metrics = remix_share_metrics,
    ),
)

if settings.PROJECT == 'canvas':
    Experiments = ExperimentSet(
        # Permanent experiments, used for testing the experiment system
        Experiment('null_hypothesis', metrics=remix_share_metrics),
        Experiment('forced_into_control',
            branches = [('control', 1), ('experimental', 0)]
        ),
        Experiment('forced_into_experimental',
            branches = [('control', 0), ('experimental', 1)]
        ),
        Experiment('logged_in_only',
            logged_in_only = True,
            branches = [('control', 0), ('experimental', 1)]
        ),
        Experiment('logged_out_only',
            logged_out_only = True,
            branches = [('control', 0), ('experimental', 1)]
        ),

        # Currently running experiments
        Experiment(
            'new_onboarding',
            logged_in_only = True,
            rollout = 0,
        ),
        Experiment(
            'invite_remixers_v2',
            rollout = 0,
            staff_branch = 'experimental',
        ),
        Experiment(
            'onboarding_funnel',
            rollout = 100,
            branches = [('control', 0), ('experimental', 1)],
            metrics = Funnels.by_name['onboarding'].step_names(),
        ),
    )
elif settings.PROJECT == 'drawquest':
    Experiments = ExperimentSet(
        Experiment('null_hypothesis', metrics=[]),
    )

def get_experiment_and_branch_by_name(experiment_name, branch_name):
    experiment = Experiments.by_name.get(experiment_name)
    if not experiment:
        raise ValueError("Invalid experiment name (%s)" % experiment_name)

    branch = experiment.branches.get(branch_name)
    if not branch:
        raise ValueError("Invalid branch name (%s for experiment %s)" % (branch_name, experiment_name))

    return experiment, branch

class ForceExperimentMiddleware(object):
    def process_request(self, request):
        forced_experiments = request.GET.getlist('force_experiment')
        for pair in forced_experiments:
            try:
                experiment, branch = pair.split(':', 1)
                force_into_branch(request, experiment, branch)
            except ValueError:
                continue

def force_into_branch(request, experiment_name, branch_name):
    # Validate input
    get_experiment_and_branch_by_name(experiment_name, branch_name)

    request.session.modified = True
    request.session['force'] = request.session.get('force', {})
    request.session['force'][experiment_name] = branch_name

class RequestExperiments(object):
    def __init__(self, backend, request=None, user_id=None):
        """ Supply `request` or `logged_in_user_id` in order to record a fact. """
        self._backend = backend
        self._experiments = None
        self._request = request
        self._user_id = user_id

    def _fetch(self):
        if self._experiments is None:
            self.update()

    def update(self):
        self._experiments = self._backend.get_experiments()

    def is_in(self, experiment_name, branch_name="experimental"):
        experiment, branch = get_experiment_and_branch_by_name(experiment_name, branch_name)
        return self.get(experiment) == branch

    def get(self, experiment, *args, **kwargs):
        if isinstance(experiment, str):
            exp_obj = Experiments.by_name.get(experiment)
            if not exp_obj:
                raise ValueError("Invalid experiment name (%s)" % experiment)
            return self._get(exp_obj, *args, **kwargs).name
        else:
            return self._get(experiment, *args, **kwargs)

    def _get(self, experiment, no_roll=False):
        self._fetch()

        default = False if no_roll else experiment.default_branch

        if (experiment.logged_in_only and not self._backend.logged_in or
            experiment.logged_out_only and self._backend.logged_in):
            return default

        if self._request:
            force = self._request.session.get('force', {})
            branch_name = force.get(experiment.name)
            if branch_name:
                return experiment.branches[branch_name]

        if self._backend.staff:
            return False if no_roll else experiment.staff_branch

        if (self._backend.key % 100) + 1 > experiment.rollout:
            return default

        if experiment.name not in self._experiments:
            if no_roll:
                return False
            else:
                branch = Services.experiment_placer.roll(experiment)
                self.add(experiment, branch)

        return experiment.branches[self._experiments[experiment.name]]

    def add(self, experiment, branch):
        self._backend.add(experiment, branch)
        self.update()
        self._record_add(experiment, branch)

    def _record_add(self, experiment, branch):
        identifier = self._request
        if not identifier and self._user_id:
            from apps.canvas_auth.models import User
            identifier = User.objects.get(id=self._user_id)

        if identifier:
            from canvas import fact
            fact.record('experiment_add', identifier, {
                'experiment': experiment.name,
                'branch': branch.name,
            })

    def get_all_current_branches(self):
        for experiment in Experiments.all:
            branch = self._get(experiment, no_roll=True)
            if branch:
                yield experiment, branch

class SessionExperimentsBackend(object):
    """ An A/B experiments wrapper that uses the request session to store experiments membership info. """
    logged_in = False
    staff = False

    def __init__(self, session):
        self.session = session
        self.key = hash(session.session_key)

    def get_experiments(self):
        return self.session.get('experiments', {})

    def add(self, experiment, branch):
        self.session.setdefault('experiments', {})
        self.session['experiments'][experiment.name] = branch.name
        self.session.modified = True

class UserExperimentsBackend(object):
    """ A wrapper around a Redis hash to store experiments for an existing user. """
    logged_in = True

    def __init__(self, user_id, staff):
        self._user_id = user_id
        self.staff = staff
        self.key = user_id

    def get_experiments(self):
        return self.user_experiments.hgetall()

    def add(self, experiment, branch):
        self.user_experiments.hset(experiment.name, branch.name)
        branch.users.sadd(self._user_id)

    user_experiments = property(lambda self: RedisHash('user:%s:experiments' % self._user_id))

def migrate_from_request_to_user(request, user):
    for experiment, branch in request.experiments.get_all_current_branches():
        user.redis.experiments.add(experiment, branch)

def create_experiments_for_request(request):
    # Choose a backend based on whether this user is logged in or out.
    if request.user.is_authenticated():
        backend = UserExperimentsBackend(request.user.id, request.user.is_staff)
    else:
        backend = SessionExperimentsBackend(request.session)
    return RequestExperiments(backend, request=request)

def sees_experiment(request, experiment):
    # Allows you to force a request into an experiment
    holder = getattr(request, 'JSON', request.REQUEST)

    if experiment.name in holder:
        return bool(holder.get(experiment.name))
    return request.experiments.get(experiment).name == "experimental"

