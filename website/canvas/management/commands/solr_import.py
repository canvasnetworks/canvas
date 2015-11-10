from time import time

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from canvas.models import Comment, Category
from canvas import search
from django.conf import settings

class Command(BaseCommand):
    args = 'solr_core'
    help = 'WARNING: Deletes everything first! Bulk import all data into SOLR. solr_core is one of "comment" or "group"'

    def handle(self, solr_core, *args, **options):
        if solr_core == 'comment':
            qs = Comment.objects.exclude(reply_content__id=None).filter(category__name='stamps')
        elif solr_core == 'group':
            qs = Category.objects.all()
        else:
            raise Exception("Unknown solr_core %r" % solr_core)
            
        conn = search.get_local(solr_core).connection
            
        conn.delete_query('*:*')
        count = qs.count()
        for e, obj in enumerate(qs.only('id')):
            obj.update_solr()
            if e % 100 == 0:
                print "%0.02f%% complete" % (float(e)/count*100)
        print "Commit/Optimize"
        conn.commit()
        conn.optimize()    
        print "Done!"
