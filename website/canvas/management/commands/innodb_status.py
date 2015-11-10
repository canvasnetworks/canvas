from time import time
from datetime import datetime, timedelta

from django.db import connection

class Command(BaseCommand):
    args = ''
    help = 'Update comment scores for the front pages.'

    def handle(self, *args, **options):
        cur = connection.cursor();
        cur.execute("SHOW ENGINE INNODB STATUS"); 
        print cur.fetchall()[0][2]

