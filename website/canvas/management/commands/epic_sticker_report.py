from django.core.management.base import BaseCommand

from collections import defaultdict
import fact_query
from canvas import stickers
    
class Command(BaseCommand):
    args = ''
    help = "See which epic stickers users are buying and using."
    
    def handle(self, *args, **options):
        purchased = defaultdict(int)
        used = defaultdict(int)
        for row in fact_query.trailing_days(9):
            if row.get('metric') == 'shop_sticker_purchased':
                sticker = stickers.get(row.get('type_id'))
                if sticker.name not in purchased:
                    purchased[sticker.name] = defaultdict(int)
                purchased[sticker.name]["quantity"] += 1
                purchased[sticker.name]["total_spent"] += sticker.cost
            if row.get('metric') == 'shop_sticker_used':
                sticker = stickers.get(row.get('type_id'))
                if sticker.name not in used:
                    used[sticker.name] = defaultdict(int)
                used[sticker.name]["quantity"] += 1
                used[sticker.name]["total_spent"] += sticker.cost
        print "Purchased:", purchased
        print "Used:", used
