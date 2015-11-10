from django.core.management.base import BaseCommand, CommandError

from canvas.models import User, FacebookUser

class Command(BaseCommand):
    args = 'username'
    help = 'Deletes all FacebookUsers or the one associated with the provided username'

    def handle(self, username=None, *args, **kwargs):
        if username:
            print "Deleting the FacebookUser associated with '%s'..." % username
            User.objects.get(username=username).facebookuser.delete()
            print "Done!"
            return
        else:
            print "Deleting all FacebookUser objects..."
            total = FacebookUser.objects.count()
            if total > 10:
                print "Too many FacebookUser objects to feel good about this, bailing..."
                return
            FacebookUser.objects.all().delete()
            print "Deleted all %s FacebookUsers" % total
