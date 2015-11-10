import collections
import fact_query
import platform
import stats
import sys
import time
import webbrowser
import datetime

from django.core.management.base import BaseCommand

from canvas.experiments import Experiments
from canvas.templatetags.jinja_base import render_jinja_to_string

class User(object):
    def __init__(self):
        self.first_view_ts = self.signup_ts = 0
        self.first_view_dt = self.signup_dt = None
        self.view_ts = 0
        self.came_back = collections.Counter()
        self.retained_visits = collections.Counter()

def cached_host_by_addr(addr, cache={}):
    import socket
    if not addr in cache:
        try:
            host = socket.gethostbyaddr(addr)[0]
        except IOError:
            host = None
        cache[addr] = host

    return cache[addr]

def parse_ip(ip):
    return tuple(int(octet) for octet in ip.split('.'))

# via http://chceme.info/ips/

bot_ranges = [
    ((64,233,160,0), (64,233,191,255)),
    ((66,102,0,0), (66,102,15,255)),
    ((66,249,64,0), (66,249,95,255)),
    ((72,14,192,0), (72,14,255,255)),
    ((74,125,0,0), (74,125,255,255)),
    ((209,85,128,0), (209,85,255,255)),
    ((216,239,32,0), (216,239,63,255)),
    ((64,4,0,0), (64,4,63,255)),
    ((65,52,0,0), (65,55,255,255)),
    ((157,54,0,0), (157,60,255,255)),
    ((207,46,0,0), (207,46,255,255)),
    ((207,68,128,0), (207,68,207,255)),
    ((8,12,144,0), (8,12,144,255)),
    ((66,196,64,0), (66,196,127,255)),
    ((66,228,160,0), (66,228,191,255)),
    ((67,195,0,0), (67,195,255,255)),
    ((68,142,192,0), (68,142,255,255)),
    ((72,30,0,0), (72,30,255,255)),
    ((74,6,0,0), (74,6,255,255)),
    ((202,160,176,0), (202,160,191,255)),
    ((209,191,64,0), (209,191,127,255))
]

def is_bot(ip):
    try:
        parsed_ip = parse_ip(ip)
    except ValueError:
        return False

    for bot_lower, bot_upper in bot_ranges:
        if bot_lower <= parsed_ip <= bot_upper:
            return True
    return False

"""
Ideal logged out:
ip, until we see a utma for that ip then *move* that ips info into the utma and delete the ip.
"""

class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        SIGNUP_WINDOW = int(args[0]) if len(args) > 0 else 1
        RETENTION_WINDOW = int(args[1]) if len(args) > 1 else 1
        NEW_USER_WINDOW = int(args[2]) if len(args) > 2 else 1

        print "Signup window:", SIGNUP_WINDOW, "days"
        print "Retention window:", RETENTION_WINDOW, "days"
        print "New user window:", NEW_USER_WINDOW, "days"

        stop = datetime.datetime.utcnow()        
        retention_start = stop - datetime.timedelta(days=RETENTION_WINDOW)
        signup_start = retention_start - datetime.timedelta(days=SIGNUP_WINDOW)
        new_user_start = signup_start - datetime.timedelta(days=NEW_USER_WINDOW)

        fact_iter = lambda: fact_query.iterator(start=new_user_start, stop=stop)

        users = collections.defaultdict(User)
        
        all_shares = 0
        old_user_max = float("inf")
        retained_first_ts = None

        signups = []
        for row in fact_iter():
            if not retained_first_ts and row['dt'] >= signup_start:
                retained_first_ts = row['ts']

            key = row.get('type') if row.get('type') != 'metric' else row.get('metric')
            
            user = users[row['user']] if 'user' in row else None
            
            if user and key == 'signup':
                old_user_max = min(old_user_max, row['user'])
                user.signup_ts = row['ts']
                user.signup_dt = row['dt']
            
            if user and key == 'view':
                if not user.first_view_ts:
                    user.first_view_ts = row['ts']
                    user.first_view_dt = row['dt']

                user.came_back[(row['ts'] - user.signup_ts) // (24 * 60 * 60)] = 1
                
                if row['dt'] >= signup_start and row['user'] <= old_user_max:
                    user.retained_visits[(row['ts'] - retained_first_ts) // (24 * 60 * 60)] = 1
            

        user_retention = collections.Counter()
        
        new_users = set()
        for user in users.values():
            if user.signup_dt and signup_start <= user.signup_dt <= retention_start:
                new_users.add(user)
                user_retention += user.came_back

        retained_visits = sum((user.retained_visits for user in users.values()), collections.Counter())

        print
        print
        print "Signup window:", SIGNUP_WINDOW, "days"
        print "Retention window:", RETENTION_WINDOW, "days"
        print "New user window:", NEW_USER_WINDOW, "days"
        print

        print "New user retention curve"
        for key, value in sorted(user_retention.items(), key = lambda (k,v): k):
            if key < NEW_USER_WINDOW:
                print key, ':', value
        print

        print "Old user retention curve"
        retained_visits_list = [retained_visits[day] for day in range(RETENTION_WINDOW + SIGNUP_WINDOW)]
        for day, value in enumerate(retained_visits_list):
                print day, ':', value
        print
        print
        
        print "Old user retention curve averaged over signup window days"
        retained_average = [sum(retained_visits_list[day:day+SIGNUP_WINDOW]) / float(SIGNUP_WINDOW) for day in range(RETENTION_WINDOW)]
        for day, value in enumerate(retained_average):
            print day, ':', value
            
        print
        print "=" * 100
        print
        
        n = user_retention[NEW_USER_WINDOW-1]
        d = user_retention[0]
        print "New user activation %% over new user window: %s / %s = %s" % (n,d, float(n)/d)
        
        d = retained_average[0]
        n = retained_average[-1]
        print "Retained %% over retained window: %s / %s = %s" % (n,d, float(n)/d)
        
        
