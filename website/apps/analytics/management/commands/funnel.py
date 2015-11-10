import sys
import time

from apps.analytics.bots import is_bot
from apps.analytics.models import User, aggregate_facts_by_tokens, gather_results
from apps.analytics import webbrowser_util
from apps.analytics.management.commands.base import BaseAnalyticsCommand
from canvas.funnels import Funnels
from canvas.templatetags.jinja_base import render_jinja_to_string


class Command(BaseAnalyticsCommand):
    def handle_analytics(self, fact_query, *args, **kwargs):
        funnel_name = args[0]

        try:
            funnel = Funnels.by_name[funnel_name]
        except KeyError:
            print "Error, invalid experiment name %r." % funnel_name
            sys.exit(1)

        aggr = aggregate_facts_by_tokens(fact_query.fact_iter)

        logged_out_tests = [
            ('total', lambda user: True),
        ]

        logged_in_tests = [
            ('total', lambda user: True),
        ]

        for metric in funnel.steps:
            test_func = lambda user, metric=metric: user.facts[metric.name]
            test = ('%s' % metric, test_func)
            logged_out_tests.append(test)

            test = ('%s ever' % metric, test_func)
            logged_in_tests.append(test)

        def get_tables(new_users):
            return [
                ('By Unique Browser Session', gather_results(aggr, logged_out_tests, aggr.browser_sessions, new_users)),
                ('By Unique User', gather_results(aggr, logged_in_tests, aggr.logged_in_users, new_users)),
            ]

        sections = [
            ('Excluding Old Users', get_tables(True)),
            ('All Users', get_tables(False)),
        ]

        context = {
            'start': self.start,
            'stop': self.stop,
            'funnel': funnel,
            'sections': sections,
        }

        output_filename = "/var/canvas/analytics/reports/funnel_results_%s_%s.html" % (funnel_name, int(time.time()))

        with file(output_filename, 'w') as output:
            output.write(render_jinja_to_string('analytics/funnel_results.html', context))

        webbrowser_util.open_if_able(output_filename)

