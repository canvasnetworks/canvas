import sys; sys.path += ['/var/canvas/common', '../../common']

from itertools import ifilter

import fact_query


class Row(dict):
    def key(self):
        return self.get('type') if self.get('type') != 'metric' else self.get('metric')


def _wrapped_iter(query_iter):
    for item in query_iter:
        yield Row(item)


class FactQuery(object):
    def __init__(self, **kwargs):
        self.fact_iter = lambda: _wrapped_iter(fact_query.iterator(**kwargs))
        self._phase = 1
        self.start = kwargs.get('start')
        self.stop = kwargs.get('stop')

    @classmethod
    def trailing_days(cls, *args, **kwargs):
        obj = cls()
        obj.fact_iter = lambda: _wrapped_iter(fact_query.trailing_days(*args, **kwargs))
        return obj

    def metric_iter(self, *metric_names):
        for row in self.fact_iter():
            if row.get('type') == 'metric' and row.get('metric') in metric_names:
                yield row

    def begin_phase(self):
        print >> sys.stderr, "Phase {0}\n".format(self._phase)
        self._phase += 1

    def signup_ips(self):
        self.begin_phase()

        unique_signup_ips = set(row.get('ip') for row in self.fact_iter() if row.get('metric') == 'signup')
        print >> sys.stderr, "Found", len(unique_signup_ips), "signups."
        return unique_signup_ips

    def unique_visitors(self, _filtered_ips=None):
        self.begin_phase()

        visitors = {}
        for row in self.fact_iter():
            ip = row.get('ip')
            if _filtered_ips is None or ip in _filtered_ips:
                visitors[ip] = visitors.get(ip) or Visitor(ip)
                visitors[ip].visit(row)
        return visitors

    def unique_signed_up_visitors(self):
        return self.unique_visitors(_filtered_ips=self.signup_ips())

    def key_count(self, key):
        self.begin_phase()
        return sum(1 for row in self.fact_iter() if row.key() == key)


class Visitor(object):
    def __init__(self, ip):
        self.ip = ip
        self.facts = []
        
    def visit(self, row):
        if row.get('user'):
            self.user = row.get('user')
        self.facts.append(row)

    def _logged_out_referrer(self, strict, is_reversed=False):
        facts = self.facts
        if is_reversed:
            facts = reversed(facts)
                
        for fact in facts:
            if fact.get('metric') == 'logged_out_view':
                if fact.get('referrer'):
                    return fact.get('referrer')
                elif strict:
                    return
            elif fact.get('metric') == 'view' and not is_reversed:
                # This visitor was somehow logged-in before ever being logged-out.
                return

    def first_logged_out_referrer(self, strict=True):
        """
        `strict` means that if the very first visit was direct, we don't check later visits for a referrer.

        Returns `None` if the first visit was direct.
        """
        return self._logged_out_referrer(strict)

    def signed_up(self):
        """ Whether this visitor ever signed up. """
        return any(fact.get('metric') == 'signup' for fact in self.facts)
    
    def signup_count(self):
        return sum(1 for fact in self.facts if fact.get('metric') == 'signup')

