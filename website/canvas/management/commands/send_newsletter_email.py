import time

from django.core.management.base import BaseCommand

from apps.canvas_auth.models import User
from canvas.models import send_email
from canvas.notifications import expander
from canvas.notifications.actions import Actions
from django.conf import settings

BUCKET_BURSTS = 20
PAUSE = 0.1

class Command(BaseCommand):
    args = ''
    help = """Schedules sending email newsletters to all users."""

    def handle(self, id_start=0, id_end=1000000000000, *args, **options):
        id_start, id_end = int(id_start), int(id_end)
        last = time.time()
        n = 0

        err_count = 0
        for user in User.objects.filter(id__gte=id_start).exclude(id__gt=id_end).exclude(email='').order_by('id'):
            n += 1
            if n == BUCKET_BURSTS:
                n = 0
                while time.time() - last <= 1:
                    time.sleep(PAUSE)
                last = time.time()

            print "id: %s username: %r email: %r" % (user.id, user.username, user.email)
            try:
                fxn = Actions.newsletter
                # Bypass pushing it into bgwork
                fxn.__func__.do_not_deliver = True
                # Make a PendingNotification. Since we bypassed, it won't be expanded nor delivered.
                pn = fxn(user)
                expander.expand_and_deliver(pn)
            #TODO no catch-all exceptions!
            except Exception, e:
                import traceback; traceback.print_exc()
                err_count += 1
                if err_count >= 20:
                    raise

