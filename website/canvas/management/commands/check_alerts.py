import sys
import time
import urllib2

from django.core.management.base import BaseCommand, CommandError

from canvas.models import Metrics

def ping_puppetmaster():
    headers = {'Accept': 'yaml'}
    request = urllib2.Request('https://puppetmaster.internal.example.com:8140/production/certificate/ca', headers=headers)
    try:
        urllib2.urlopen(request, timeout=2).read()
    except urllib2.URLError:
        print "Puppetmaster not responding."
        return False
    else:
        print "Puppetmaster healthy."
        return True

class Command(BaseCommand):
    args = '[all | high | low]'
    help = "Check all metric's last updated times against their alert thresholds"

    def handle(self, priority='all', *args, **options):
        ok = True
        now = time.time()
        # Our slow hours are approximately 1AM - 11AM EDT which is GMT-4. Double alarm minutes during this period.
        slow_hours = 5 <= time.gmtime()[3] < 15
        alarm_scalar = 2 if slow_hours else 1

        assert priority in ('all', 'high', 'low')

        tested_metrics = 0

        for key, metric in sorted(Metrics.all.items()):
            if metric.alarm_minutes == None:
                continue

            high_priority = metric.alarm_minutes <= 60

            if (priority == 'high' and not high_priority) or (priority == 'low' and high_priority):
                continue

            tested_metrics += 1

            if metric.threshold:
                metric_ok = metric.check_threshold(not slow_hours)
            else:
                raw_ts = metric.timestamp_key.get()
                last = float(raw_ts) if raw_ts is not None else 0
                metric_ok = last >= now - (metric.alarm_minutes * 60 * alarm_scalar)

            ok = ok and metric_ok
            if not metric_ok:
                print key, u'({0} category)'.format(metric.category), 'ALARM',
                if metric.threshold:
                    mins = 2 * metric.alarm_minutes if slow_hours else metric.alarm_minutes
                    print 'below threshold of {0} per {1} minutes @ {2}'.format(metric.threshold, mins, metric.get_threshold_count())

                elif raw_ts is not None:
                    minutes, seconds = divmod(now-last, 60)
                    print '%sm %0.02fs seconds since last timestamp' % (minutes, seconds)

                else:
                    print 'no recorded last timestamp'


        RETRIES = 6
        for n in range(1, RETRIES+1):
            if ping_puppetmaster():
                break
            elif n != RETRIES:
                print "Retrying..."
                time.sleep(5)

        if not ok:
            sys.exit(1)
        else:
            print "All", tested_metrics, "checks OK"


