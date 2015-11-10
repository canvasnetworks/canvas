from django.core.management.base import BaseCommand

from django.conf import settings

import fact_query
import stats
import datetime

# e - elapsed
# u - user
# s - system

# 21:17:54

def print_page_timings():
    if settings.PROJECT == 'canvas':
        SLOW_PAGE_THRESHOLD = 9000
    elif settings.PROJECT == 'drawquest':
        SLOW_PAGE_THRESHOLD = 275

    elapsed_times = []
    elapsed_api_times = []
    slow_pages = []
    slow_apis = []
    redis = []
    sql = []
    for row in fact_query.trailing_days(1):
        if row.get('metric') not in ('view', 'logged_out_view', 'api_call'):
            continue


        if 'sql' in row:
            sql.append(row['sql'])
        if 'redis' in row:
            redis.append(row['redis'])

        elapsed = row.get('e')
        if elapsed:
            if row.get('metric') == 'api_call':
                elapsed_api_times.append(elapsed)
            else:
                elapsed_times.append(elapsed)
            if elapsed > SLOW_PAGE_THRESHOLD:
                entry = (elapsed, row.get('path'))
                if row.get('metric') == 'api_call':
                    if (settings.PROJECT == 'drawquest'
                        and 'upload' in row.get('path')
                        or 'activity_stream' in row.get('path')):
                        continue
                    slow_apis.append(entry)
                else:
                    slow_pages.append(entry)

    slow_count = len(slow_pages)
    slow_api_count = len(slow_apis)

    if settings.PROJECT == 'canvas':
        print "SLOW PAGES"
        print "Slow count (>%s): %s" % (SLOW_PAGE_THRESHOLD, slow_count)
        if slow_count:
            print "Slow pages:"
            for elapsed, path in sorted(slow_pages, key=lambda x: int(x[0])):
                print "Slow page (%sms) %s" % (int(elapsed), path)

        print "Slow pages per hour", slow_count / 24.0
        print

        print "Overall (pages)"
        stats.pp_percentiles(elapsed_times)
        print

    print "SLOW API CALLS"
    print "Slow count (>%s): %s" % (SLOW_PAGE_THRESHOLD, slow_api_count)
    if slow_api_count:
        print "Slow pages:"
        for elapsed, path in sorted(slow_apis, key=lambda x: int(x[0])):
            print "Slow page (%sms) %s" % (int(elapsed), path)

    print "Slow API calls per hour", slow_api_count / 24.0
    print

    print "Overall (API calls)"
    stats.pp_percentiles(elapsed_api_times)
    print

    print "MySQL"
    print "Total Query Count:", sum(c[0] for c in sql)
    print "Total Query Time:", sum(c[1] for c in sql) // 1000, 's'
    print

    print "Redis"
    print "Total Command Count:", sum(c[0] for c in redis)
    print "Total Command Time:", sum(c[1] for c in redis) // 1000, 's'
    print

# via https://docs.djangoproject.com/en/dev/topics/db/sql/
def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def print_slow_queries():
    from django.db import connection
    from django.db.utils import DatabaseError
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM mysql.slow_log WHERE start_time > NOW() - INTERVAL 1 DAY")
    except DatabaseError:
        print "UNABLE TO QUERY SLOW LOG"
        return
    rows = dictfetchall(cursor)
    print "SLOW QUERIES"
    if rows:
        for row in rows:
            print "-" * 80
            _print_slow_query(row)
    else:
        print "No slow queries"
    print

def _print_slow_query(row):
    print "start time:", row['start_time'].isoformat()
    print "query time:", row['query_time'].isoformat()
    print "lock time:", row['lock_time'].isoformat()
    print "rows examined:", row['rows_examined']
    print "rows sent:", row['rows_sent']
    print "user/host:", row['user_host']
    print "sql:", row['sql_text']

class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        print "Daily performance digest -", datetime.datetime.now().isoformat()
        print_page_timings()
        print_slow_queries()

