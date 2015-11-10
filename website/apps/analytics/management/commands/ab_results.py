import stats
import sys
import time

from apps.analytics.bots import is_bot
from apps.analytics.models import User, aggregate_facts_by_tokens, gather_results
from apps.analytics import webbrowser_util
from apps.analytics.management.commands.base import BaseAnalyticsCommand
from canvas.experiments import Experiments
from canvas.templatetags.jinja_base import render_jinja_to_string


class Command(BaseAnalyticsCommand):
    def handle_analytics(self, fact_query, *args, **kwargs):
        EXPERIMENT = args[0]

        try:
            experiment = Experiments.by_name[EXPERIMENT]
        except KeyError:
            print "Error, invalid experiment name %r." % EXPERIMENT
            sys.exit(1)

        aggr = aggregate_facts_by_tokens(fact_query.fact_iter, experiment=experiment)

        def in_branch(experiment, branch):
            def test_user(user):
                return user.experiments.get(experiment) == branch
            return test_user

        basis = [(branch.name, in_branch(experiment.name, branch.name)) for branch in experiment.branches.values()]

        logged_out_tests = [
            ('total', lambda user: True),
            ('viewed 3+ pages', lambda user: user.facts['view'] >= 3),
            ('5+ infinite scrolls', lambda user: user.facts['infinite_scroll'] >= 5),
            ('2nd day view', lambda user: user.day_bins[1]['view']),
            ('signed up', lambda user: user.facts['signup']),
            ('stickered', lambda user: user.facts['sticker']),
            ('posted', lambda user: user.facts['post']),
        ]

        logged_in_tests = [
            ('total', lambda user: True),
            ('stickered ever', lambda user: user.facts['sticker']),
            ('posted ever', lambda user: user.facts['post']),
            ('2nd day after signup viewed', lambda user: user.post_signup_bins[1]['view']),
            ('2nd day after signup stickered', lambda user: user.post_signup_bins[1]['sticker']),
            ('2nd day after signup posted', lambda user: user.post_signup_bins[1]['post']),
        ]

        for metric in experiment.metrics:
            test = ('%s ever' % metric, lambda user, metric=metric: user.facts[metric])
            logged_out_tests.append(test)
            logged_in_tests.append(test)

        def get_tables(new_users):
            return [
                ('By Unique Browser Session', gather_results(aggr,
                                                             logged_out_tests, aggr.browser_sessions, new_users,
                                                             basis=basis)),
                ('By Unique User', gather_results(aggr,
                                                  logged_in_tests, aggr.logged_in_users, new_users,
                                                  basis=basis)),
            ]

        sections = []

        if not experiment.logged_in_only:
            sections.append(('Excluding Old Users', get_tables(True)))

        # Even if the experiment is logged_out_only, this shows us what users who saw the logged out experiment and then signed up did.
        sections.append(('All Users', get_tables(False)))

        context = {
            'start': self.start,
            'stop': self.stop,
            'experiment': EXPERIMENT,
            'sections': sections,
        }
        
        output_filename = "/var/canvas/analytics/reports/ab_results_%s_%s.html" % (EXPERIMENT, int(time.time()))

        with file(output_filename, 'w') as output:
            output.write(render_jinja_to_string('analytics/ab_results.html', context))

        webbrowser_util.open_if_able(output_filename)

