from time import time
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from django.db.models import Q, Count
import facebook

from canvas.models import *
from canvas.util import Now
from django.conf import settings


class Command(BaseCommand):
    args = ''
    help = 'Import users from fbid csv dump'

    def handle(self, *args, **options):
        users = [line.strip() for line in file('/var/canvas/data/canvas_installed_users.csv')]
        fb = facebook.GraphAPI(settings.FACEBOOK_APP_ACCESS_TOKEN)
        
        def fb_call(fun, retries=0):
            try:
                return fun()
            except (facebook.GraphAPIError, IOError):
                if retries < 5:
                    time.sleep(retries + 0.01)
                    return fb_call(fun, retries + 1)
                else:
                    raise
        
        missing = 0
        existing = 0
        added = 0
        try:
            for n in range(0, len(users), 100):
                fb_results = fb_call(lambda: fb.get_objects(users[n:n+100]))
                for fbid, info in fb_results.items():
                    if "email" not in info:
                        print "no email", fbid
                        missing += 1
                    else:
                        try:                        
                            FacebookUser(
                                 fb_uid=info['id'], 
                                 email=info['email'],
                                 first_name=info['first_name'],
                                 last_name=info['last_name'],
                                 user=None
                             ).save()
                        except IntegrityError:
                            existing += 1
                        else:
                            added += 1
        
                        
                        
                print "Processed", n, "of", len(users)
        finally:
            print "Total", len(users)
            print "Missing email", missing
            print "Added", added
            print "Existing", existing
            
                    
