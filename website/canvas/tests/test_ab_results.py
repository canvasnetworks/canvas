import datetime

from apps.analytics.management.commands.ab_results import aggregate_facts_by_tokens
from canvas.experiments import Experiments
from canvas.tests.tests_helpers import CanvasTestCase

_time = 1234567890

def fact(**kwargs):
    global _time
    _time += 1
    defaults = {
        'ts': _time,
        'dt': datetime.datetime.fromtimestamp(_time),
        'type': 'metric',
        'metric': 'test',
        'experiments': {'null_hypothesis': 'control'},
    }
    return dict(defaults, **kwargs)


class TestUserAndSessionAggregation(CanvasTestCase):
    def test_all_facts_into_one_utma(self):
        simple_stream = [
            fact(ip='1.1.1.1', utma='def'),
            fact(ip='1.1.1.1', utma='def'),
            fact(ip='1.1.1.1', utma='def'),
        ]
        
        aggr = aggregate_facts_by_tokens(lambda: simple_stream, Experiments.null_hypothesis)
        
        self.assertEqual(1, len(aggr.browser_sessions))
        self.assertTrue("def" in aggr.browser_sessions)

    def test_ip_fact_follows_utma(self):
        ip_then_utma = [
            fact(ip='1.1.1.1', metric='first'),
            fact(ip='1.1.1.1', utma='foo'),
        ]
        
        aggr = aggregate_facts_by_tokens(lambda: ip_then_utma, Experiments.null_hypothesis)

        self.assertEqual(1, aggr.browser_sessions['foo'].facts['first'])

    def test_ips_and_utmas_living_in_harmony(self):
        ip_and_utma_unrelated = [
            fact(ip='1.1.1.1'),
            fact(ip='2.2.2.2', utma='bar')
        ]

        aggr = aggregate_facts_by_tokens(lambda: ip_and_utma_unrelated, Experiments.null_hypothesis)

        self.assertEqual(2, len(aggr.browser_sessions))

    def test_utma_of_None_is_like_no_utma_at_all(self):
        ips_unrelated = [
            fact(ip='1.1.1.1', utma=None),
            fact(ip='2.2.2.2', utma=None)
        ]

        aggr = aggregate_facts_by_tokens(lambda: ips_unrelated, Experiments.null_hypothesis)

        self.assertEqual(2, len(aggr.browser_sessions))

