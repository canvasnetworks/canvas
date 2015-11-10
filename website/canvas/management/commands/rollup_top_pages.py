import datetime

from django.core.management.base import BaseCommand

from apps.tags.models import all_tags, Tag
from canvas.models import Category

class Command(BaseCommand):
    args = ''
    help = 'Merge daily top scores into monthly and yearly top scores.'

    def handle(self, *args, **options):
        today = datetime.date.today()

        categories = [Category.ALL] + list(Category.objects.all())

        for category in categories:
            category.merge_top_scores(today)

        for tag in all_tags.smembers():
            Tag(tag).merge_top_scores(today)


