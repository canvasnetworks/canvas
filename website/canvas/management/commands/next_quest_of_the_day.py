from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from drawquest.apps.quests.models import ScheduledQuest


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        ScheduledQuest.rollover_next_quest()

