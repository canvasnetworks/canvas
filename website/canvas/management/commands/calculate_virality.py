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

class Session(object):
    def __init__(self):
        self.referrer = None
        self.share_views = 0
        self.sharers = set()
        self.users = set()

class User(object):
    def __init__(self):
        self.signup_dt = None
        self.shares = 0
        self.in_signup_window = False

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
        SIGNUP_WINDOW = float(args[0]) if len(args) > 0 else 0.1
        VIRALITY_WINDOW = float(args[1]) if len(args) > 1 else 0.1
        
        print "Signup window:", SIGNUP_WINDOW, "days"
        print "Virality window:", VIRALITY_WINDOW, "days"

        stop = datetime.datetime.utcnow()
        virality_start = stop - datetime.timedelta(days=VIRALITY_WINDOW)
        signup_start = virality_start - datetime.timedelta(days=SIGNUP_WINDOW)


        fact_iter = lambda: fact_query.iterator(start=signup_start, stop=stop)

        sessions = collections.defaultdict(Session)
        users = collections.defaultdict(User)
        
        all_shares = 0

        signups = []
        for row in fact_iter():
            if 'ip' in row:
                if is_bot(row['ip']):
                    continue

            session = None
            if 'ip' in row:
                if 'utma' in row:
                    if row['utma'] not in sessions:
                        # First time we've seen this google session
                        # Let's tie any previous requests from this IP to this utma session
                        sessions[row['utma']] = sessions[row['ip']]
                        del sessions[row['ip']]

                    session = sessions[row['utma']]
                else:
                    # We don't have any google session, use the ip instead
                    session = sessions[row['ip']]

            
            user = users[row['user']] if 'user' in row else None
                
            key = row.get('type') if row.get('type') != 'metric' else row.get('metric')

            if key == 'signup':
                user.id = row['user']
                user.signup_dt = row['dt']
                user.in_signup_window = signup_start <= user.signup_dt < virality_start
                session.users.add(user.id)
            
            if key == 'create_share_url':
                all_shares += 1
                
            if user and user.signup_dt and row['dt'] < user.signup_dt + datetime.timedelta(VIRALITY_WINDOW):
                # Within our window of consideration for user-attributable shares
                if key == 'create_share_url':
                    user.shares += 1
            
            if session and key == 'share_redirect':
                session.share_views += 1
                session.sharers.add(row['sharer'])

        signups_initial = set()
        for user in users.values():
            if user.in_signup_window:
                signups_initial.add(user)
        
        viral_sessions = set()
        outside_viral_sessions = set()
        for session in sessions.values():
            if len(session.sharers & signups_initial):
                viral_sessions.add(session)
            elif len(session.sharers):
                print session.sharers
                outside_viral_sessions.add(session)
        
        viral_signups = set()
        for session in viral_sessions:
            viral_signups |= session.users
        
        outside_signups = set()
        for session in outside_viral_sessions: outside_signups |= session.users
        
        print
        print
        print "CORE STATS:"
        print "Initial Signups (IS):", len(signups_initial)
        print "Shares from IS:", sum(user.shares for user in signups_initial)
        print "Sessions from shares:", len(viral_sessions)
        print "Signups from share sessions:", len(viral_signups)
        print
        print
        print "JUST FOR REFERENCE:"
        print "All shares (new and old users):", all_shares
        print "Outside sessions from shares:", len(outside_viral_sessions)
        print "Outside signups from shares:", len(outside_signups)
