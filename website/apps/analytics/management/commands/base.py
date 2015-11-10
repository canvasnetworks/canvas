import datetime
from optparse import make_option

from django.core.management.base import BaseCommand

from fact_query_utils import FactQuery

DEFAULT_DAYS = 0.1


class BaseAnalyticsCommand(BaseCommand):
    args = ''
    help = ''

    option_list = BaseCommand.option_list + (
        make_option('--days',
            type='float',
            dest='days',
            default=DEFAULT_DAYS,
            help='Number of days to run this over'),
        )

    def handle(self, *args, **options):
        try:
            days = float(options.get('days'))
        except TypeError:
            days = DEFAULT_DAYS

        self.stop = datetime.datetime.utcnow()
        self.start = self.stop - datetime.timedelta(days=days)

        fact_query = FactQuery(start=self.start, stop=self.stop)

        self.handle_analytics(fact_query, *args, **options)

    def handle_analytics(self, fact_query, *args, **kwargs):
        raise NotImplementedError

