import collections
import stats

from apps.analytics.bots import is_bot


class User(object):
    # ip -> signup ts
    all_signup_ts = {}

    def __init__(self):
        self.first_ts = 0
        self.day_bins = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
        self.post_signup_bins = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
        self.facts = collections.defaultdict(lambda: 0)
        self.ids = set()
        self.experiments = {}

    @property
    def id(self):
        try:
            return list(self.ids)[0]
        except IndexError:
            return None

    @property
    def signup_ts(self):
        return self.all_signup_ts.get(self.id, 0)


class FactAggregation(object):
    def __init__(self, cutoff_user_id, browser_sessions, logged_in_users, uniques):
        self.cutoff_user_id = cutoff_user_id
        self.browser_sessions = browser_sessions
        self.logged_in_users = logged_in_users
        self.uniques = uniques


def aggregate_facts_by_tokens(fact_iter, experiment=None):
    cutoff_user_id = float('inf')

    browser_sessions = collections.defaultdict(User)
    logged_in_users = collections.defaultdict(User)
    uniques = collections.defaultdict(set)

    for row in fact_iter():
        if 'ip' in row:
            if is_bot(row['ip']):
                continue

        for key in ('ip', 'session_key', 'utma','user'):
            if key in row: 
                uniques[key].add(row[key])

        users = []
        if row.get('ip') is not None:
            if row.get('utma') is not None:
                if row['utma'] not in browser_sessions:
                    # First time we've seen this google session
                    # Let's tie any previous requests from this IP to this utma session
                    browser_sessions[row['utma']] = browser_sessions[row['ip']]
                    del browser_sessions[row['ip']]

                users.append(browser_sessions[row['utma']])
            else:
                # We don't have any google session, use the ip instead
                users.append(browser_sessions[row['ip']])

        if 'user' in row:
            users.append(logged_in_users[row['user']])

        experiments = row.get('experiments', {})

        key = row.get('type') if row.get('type') != 'metric' else row.get('metric')

        if key == 'signup':
            User.all_signup_ts[row['user']] = row['ts']

        if key == 'logged_out_view':
            # We don't care about logged out / logged in
            key = 'view'

        if key == 'logged_out_infinite_scroll':
            key = 'infinite_scroll'

        for user in users:
            if experiment and not experiments.get(experiment.name) and not user.experiments.get(experiment.name):
                # Don't count facts prior to being placed in the experiment
                # Experiments don't (yet) carry over from logged out to logged in, need to fix this asap
                continue

            if not user.first_ts:
                user.first_ts = row.get('ts')

            user.experiments.update(experiments)

            if row.get('user'):
                user.ids.add(row['user'])

            if key == 'signup':
                cutoff_user_id = min(cutoff_user_id, row['user'])

            dayify = lambda ts, first_ts: int((ts - first_ts) // 86400)

            user.day_bins[dayify(row['ts'], user.first_ts)][key] += 1
            if user.signup_ts:
                user.post_signup_bins[dayify(row['ts'], user.signup_ts)][key] += 1

            user.facts[key] += 1

    return FactAggregation(cutoff_user_id, browser_sessions, logged_in_users, uniques)

def gather_results(aggr, tests, users, new_users, basis=None):
    """ See ab_results for a usage example. """
    basis_counts = {}

    def populate_counts(counts, base_fun=None):
        for ip, user in users.iteritems():
            # Skip users that did stuff like logging out then logging back in as a different user.
            if len(user.ids) > 1:
                continue

            if new_users and user.id is not None and user.id < aggr.cutoff_user_id:
                continue

            if base_fun and not base_fun(user):
                continue

            for test_name, test_fun in tests:
                if test_fun(user):
                    counts[test_name] += 1

    if basis:
        for base_name, base_fun in basis:
            basis_counts[base_name] = counts = collections.defaultdict(lambda: 0)
            populate_counts(counts, base_fun=base_fun)
    else:
            basis_counts = collections.defaultdict(lambda: 0)
            populate_counts(basis_counts)

    results = []

    def get_result(test_name, test_fun, basis=None):
        result = {
            'fact': test_name,
        }

        if not basis:
            result['count'] = basis_counts[test_name]
            return result

        result.update({
            'branch': basis_name,
            'control': basis_name == 'control',
            'count': basis_counts[basis_name][test_name],
        })

        if basis_name != "control":
            vexp = basis_counts[basis_name][test_name]
            exp_total = basis_counts[basis_name]['total']
            vcontrol = basis_counts['control'][test_name]
            control_total = basis_counts['control']['total']

            z = stats.z_test(vexp, exp_total, vcontrol, control_total)

            rate = lambda amount, total: float(amount) / total if total else 0

            exp_rate = rate(vexp, exp_total)
            control_rate = rate(vcontrol, control_total)

            perc_change = (exp_rate - control_rate) / float(control_rate) if control_rate else 0

            stats.z_to_ci(z) * 100, perc_change * 100, z

            result.update({
                'confidence': stats.z_to_ci(z) * 100,
                'change': perc_change * 100,
                'z': z,
            })

        return result

    for test_name, test_fun in tests:
        test_results = []

        if basis:
            for basis_name, bases_fun in basis:
                result = get_result(test_name, test_fun, basis=basis)
                test_results.append(result)
        else:
            result = get_result(test_name, test_fun)
            test_results.append(result)

        results.append(test_results)

    return results

