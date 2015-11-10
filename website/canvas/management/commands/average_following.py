import datetime
import functools
import math

from django.db.models import Count, StdDev, Avg
from django.db.utils import DatabaseError
from django.core.management.base import BaseCommand, CommandError

from apps.canvas_auth.models import User
from canvas.models import FollowCategory
from canvas.browse import frontpage_algorithms

def percentile(N, percent, key=lambda x:x):
    """
    Find the percentile of a list of values.

    @parameter N - is a list of values. Note N MUST BE already sorted.
    @parameter percent - a float value from 0.0 to 1.0.
    @parameter key - optional key function to compute value from each element of N.

    @return - the percentile of the values
    """
    if not N:
        return None
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (c-k)
    d1 = key(N[int(c)]) * (k-f)
    return d0+d1

MONTHS = 6

class Command(BaseCommand):
    args = ''

    def handle(self, *args, **options):
        cutoff_date = datetime.date.today() - datetime.timedelta(days=(30 * MONTHS))
        counts = User.objects.filter(date_joined__gt=cutoff_date)
        counts = counts.annotate(follow_count=Count('following')).order_by('follow_count')

        avg = counts.aggregate(Avg('follow_count'))['follow_count__avg']

        print
        print 'Following counts for users who signed up in the last {} months'.format(MONTHS)
        print '----------------'
        print 'Average: {:.3} per user'.format(avg)

        try:
            std_dev = counts.aggregate(StdDev('follow_count'))['follow_count__stddev']
            print 'StdDev:  {:.3}'.format(std_dev)
        except DatabaseError:
            print "(can't get standard deviation with SQLite)"
        counts = counts.values_list('follow_count', flat=True)
        print 'Median: {}'.format(percentile(counts, 0.5))
        print

