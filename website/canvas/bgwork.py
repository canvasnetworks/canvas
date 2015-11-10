import collections

from django.db import transaction

from canvas import util

class WorkQueue(object):
    def __init__(self):
        self.deferred_jobs = collections.deque()

    def defer(self, func):
        self.deferred_jobs.append(func)

    def clear(self):
        self.deferred_jobs.clear()

    @transaction.autocommit
    def perform(self):
        # Perform each work item.
        while self.deferred_jobs:
            job = self.deferred_jobs.popleft()

            try:
                job()
            except Exception, e:
                util.logger.exception('post_request error in bgwork.perform:' + e.message)

_global_work_queue = WorkQueue()

defer = _global_work_queue.defer
perform = _global_work_queue.perform
clear = _global_work_queue.clear

__all__ = ['WorkQueue', 'defer', 'perform', 'clear']

