import copy
import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F, Q, Count

from canvas.models import *

dt = datetime.datetime.utcfromtimestamp

class Command(BaseCommand):
    args = 'username'
    help = "Print out a detailed history of a user's lifetime on the site."

    def handle(self, username, *args, **options):
        user = User.objects.get(username=username)

        stickers_types = {
            # Upvotes.
            1:      'smiley',
            2:      'frowny',
            3:      'monocle',
            4:      'lol',
            5:      'wtf',
            6:      'question',
            7:       'num1',
            8:      'cookie',
            9:      'heart',
            10:     'wow',
            # Seasonal
            100:    "note",
            101:    "texas",
            102:    "sxsw",
            # Downvotes.
            500:    'stale',
            501:    'stop',
            502:    'poop',
            503:    'downvote', # used by api.downvote_comment and scoring.
            # Administrative.
            8901:   'bieber', #disable
            8902:   'ellipsis', #curated
            8903:   'show', #show
            8910:   'selleck', #bestof
            8911:   'offtopic', #decategorize
            8912:   'zalgo', #ultrakill (comment and content)
        }

        start = user.date_joined
        events = (
            list(user.commentsticker_set.all()) + 
            list(user.comments.all())
        )

        events = sorted(events, key=lambda e: e.timestamp)

        print "Joined", start
        current = copy.copy(start)
        
        def print_event(event):
            d = dt(event.timestamp)
            print str(d - start).ljust(25),
            if isinstance(event, CommentSticker):
                print "Stickered Content"
            elif isinstance(event, Comment):
                if event.parent_comment:
                    print "Replied",
                else:
                    print "Posted",
                
                if event.reply_content:
                    if event.reply_content.remix_of:
                        print "remix",
                    elif event.reply_content.source_url:
                        print "upload from url",
                    else:
                        print "upload from file",                        
                else:
                    print "text",

                if event.anonymous:
                    print "anonymously",

                print "and got", event.stickers.filter(type_id__lt=500).count(), "stickers", event.stickers.filter(type_id__range=(500, 1000)).count(), "downvotes"
                
        while events:
            print "Day", (current - start).days,
            if Metrics.view.is_on_record(current, user):
                print "(visited)",
            if (Metrics.logged_out_infinite_scroll.is_on_record(current, user)
                    or Metrics.logged_in_infinite_scroll.is_on_record(current, user)):
                print "(scrolled)",
            if Metrics.get_new_replies.is_on_record(current, user):
                print "(got_new_replies)",    
            
            print
            
            print "=" * 20
            day_end = current + datetime.timedelta(days=1)
            while events and dt(events[0].timestamp) < day_end:
                print_event(events.pop(0))
            print    
                
            current = day_end
