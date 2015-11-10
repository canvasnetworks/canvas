import time

from django.core.management.base import BaseCommand

from canvas.models import User, send_email

class Command(BaseCommand):
    args = ''
    help = 'Send e-mail template'

    def handle(self, from_address, subject, template, id_start, id_end, *args, **options):
        id_start, id_end = int(id_start), int(id_end)
        last = time.time()
        n = 0
        rate = 20 # per second
        err_count = 0
        for user in User.objects.filter(id__gte=id_start).exclude(id__gt=id_end).exclude(email='').order_by('id'):
            n += 1
            if n == rate:
                n = 0
                while time.time() - last <= 1:
                    time.sleep(0.1)
                last = time.time()
            
            print "id: %s username: %s email: %s" % (user.id, user.username, user.email)
            try:
                send_email(user.email, from_address, subject, template, locals())
            except Exception, e:
                import traceback; traceback.print_exc()
                err_count += 1
                if err_count >= 20:
                    raise
