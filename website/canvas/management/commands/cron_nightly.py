from django.core.management.base import BaseCommand, CommandError

from canvas.models import User, Count, Visibility, redis

class Command(BaseCommand):
    args = ''
    help = "Run our nightly cron tasks"

    def handle(self, *args, **options):
        self.annotate_accurate_flaggers()
        
    def annotate_accurate_flaggers(self):
        curators = []
        ignored = []
        
        # Figure out who are good and bad flaggers are.
        for user in User.objects.annotate(fc=Count('flags')).filter(fc__gt=0).order_by('-fc'):
            flagged = user.fc
            unmoderated = user.flags.filter(comment__visibility=Visibility.PUBLIC).count()
            accuracy = 1 - (1.0 * unmoderated / flagged)
            if accuracy <= 0.2 and flagged >= 5:
                ignored.append(user)
            elif accuracy > 0.8 and flagged >= 20:
                curators.append(user)
             
        # Update the redis sets.
        for userlist, key in zip([ignored, curators], ["user:flags_ignored", "user:flags_curate"]):
            redis.delete(key)
            for user in userlist:
                redis.sadd(key, user.id)
                
        print "Successfully annotated flaggers: %s curators and %s ignored." % (len(curators), len(ignored))

