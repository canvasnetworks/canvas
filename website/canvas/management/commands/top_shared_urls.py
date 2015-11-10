from django.core.management.base import BaseCommand

import time
from collections import defaultdict
from apps.share_tracking.models import ShareTrackingUrl
    
class Command(BaseCommand):
    args = ''
    help = "Top 30 shared links from the last 30 days."
    
    def handle(self, *args, **options):
        urls = defaultdict(int)
        number_of_days = 30
        n_days_ago = time.time() - (60*60*24*number_of_days)
        for share in ShareTrackingUrl.objects.filter(timestamp__gte=n_days_ago):
            urls[share.redirect_url] += 1

        print "Top shared replies by new users:"
        for url in sorted(urls.items(), key=lambda (key, value): -value)[:30]:
            print url
