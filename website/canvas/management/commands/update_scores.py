from datetime import datetime, timedelta
from time import time

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from canvas.browse import frontpage_algorithms
from canvas.models import Content, Comment, Category


class Command(BaseCommand):
    args = ''
    help = 'Update comment scores for the front pages.'

    def handle(self, generations, *args, **options):
        start = time()
        updates = 0
        epsilon = 0.01
        generations = int(generations)

        print "Generations: %s" % generations

        def flatten(list_of_lists):
            return set([int(item) for sublist in list_of_lists for item in sublist])

        comment_ids = flatten([Category.ALL.popular[0:100]])
        print "Gen 1", len(comment_ids)

        if generations > 1:
            comment_ids |= flatten([Category.ALL.popular[:]])
            print "Gen 2", len(comment_ids)

        if generations > 2:
            comment_ids |= flatten([category.popular[:] for category in Category.all_objects.all()])
            print "Gen 3", len(comment_ids)

        for comment in Comment.all_objects.in_bulk_list(comment_ids):
            updates += 1
            comment.update_score()
            for child_comment in Comment.all_objects.in_bulk_list(comment.popular_replies[0:3]):
                updates += 1
                child_comment.update_score()

        print "Scores updated. Rows updated: %s Total elapsed time: %0.2fs" % (updates, (time() - start))

        if generations == 2:
            print "Running hypothesis-testing scoring functions."
            frontpage_algorithms.update_scores()

