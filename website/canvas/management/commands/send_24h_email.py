import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.canvas_auth.models import User
from canvas.models import WelcomeEmailRecipient
from canvas.notifications import expander
from canvas.notifications.actions import Actions
from services import Services


def recipients():
    # We use a cutoff of 48 hours ago, so that we don't retroactively send this to all existing users,
    # and so that there's a window large enought to ensure we don't miss a bunch of users if this ever breaks and
    # doesn't run for a day for whatever reason.
    cutoff = Services.time.today() - datetime.timedelta(days=2)
    return User.users_over_one_day_old(cutoff=cutoff).exclude(pk__in=WelcomeEmailRecipient.objects.all().values_list('recipient_id', flat=True))

def send_welcome_email(user):
    """
    This doesn't protect against sending twice to the same user. You should call `recipients` and use its return
    value to get a fresh record of which users haven't received the email yet. This does save a record of which
    users were sent the email, but it doesn't check those records before sending - it's your responsibility to
    call `recipients` before calling this.
    """
    digest = Actions.digest
    do_not_deliver = getattr(digest, 'do_not_deliver', False)
    # Don't push it into bgwork.
    # See: http://stackoverflow.com/questions/7034063/adding-attributes-to-instancemethods-in-python
    digest.__func__.do_not_deliver = True

    pn = digest(user)

    # So that we don't send it twice to the same user.
    WelcomeEmailRecipient.objects.create(recipient=user)

    expander.expand_and_deliver(pn)

    digest.__func__.do_not_deliver = do_not_deliver


class Command(BaseCommand):
    args = ''
    help = """Schedules sending 24h digest email to anyone who signed up in the last 24h."""

    def handle(self, *args, **options):
        for user in recipients():
            print "id: {0} username: {1} email: {2}".format(user.id, user.username, repr(user.email))
            send_welcome_email(user)

