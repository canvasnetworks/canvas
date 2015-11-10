#!/usr/bin/env python
import sys; sys.path += ['/var/canvas/common', '../../common', '/var/canvas/boto']

import boto
from boto.s3.key import Key
import cStringIO
import collections
import contextlib
import copy
import datetime
import functools
import gzip
import json
import os.path
import time

from django.conf import settings

# Run ./maske.sh in common to build the C extensions for more perf
# Makes new_user_flows over 2x faster (9.415s before, 4.237s after for test=True)
from factlib import nginx_unescape
import ec2
try:
    try:
        # Benchmarked at 20x faster than built-in json o_O
        from cjson import decode as json_loads
    except ImportError:
        print >> sys.stderr, "WARNING: Could not import cjson. Falling back to 2x slower simplejson. Run pip install python-cjson."
        # Benchmarked at 10x-12x faster than built-in json
        from simplejson import loads as json_loads
except ImportError:
    print >> sys.stderr, "WARNING: Could not import simplejson. Falling back to 20x slower stdlib json."
    from json import loads as json_loads

# Shortcut for timedelta.
td = datetime.timedelta

import Queue
import threading
class ThreadExecModel(object):
    def run(self, fun):
        thread = threading.Thread(target=fun)
        thread.daemon = True
        thread.start()
        return thread

    def queue(self):
        return Queue.Queue()

    def event(self):
        return threading.Event()

import multiprocessing
class ProcessExecModel(object):
    def run(self, fun):
        process = multiprocessing.Process(target=fun)
        process.daemon = True
        process.start()
        return process

    def queue(self):
        return multiprocessing.Queue()

    def event(self):
        return multiprocessing.Event()

# Currently ProcessExecModel is the same or slower; doing a little too much slow copying between processes. Need to work on that.
# exec_model = ProcessExecModel()
exec_model = ThreadExecModel()

class FactRow(dict):
    """
    Simple dynamic dict for fact_query rows. 

    Allows us to do row.foo instead of row.get("foo", None)
    """
    def __getattr__(self, key):
        return self.get(key, None)

class Timing(object):
    def __init__(self):
        self.times = collections.defaultdict(lambda: 0)

    @contextlib.contextmanager
    def __getitem__(self, item):
        start = time.time()
        try:
            yield
        finally:
            stop = time.time()
            self.times[item] += stop - start

class Promise(object):
    promise_queue = exec_model.queue()
    promise_id = 1
    promise_map = {}

    def __init__(self):
        self.pid = Promise.promise_id
        self.waiting = True
        Promise.promise_id += 1
        Promise.promise_map[self.pid] = self

    def __call__(self):
        try:
            while self.waiting:
                pid, result = self.promise_queue.get(timeout=60)
                promise = Promise.promise_map[pid]
                promise.result = result
                promise.waiting = False
        except Queue.Empty:
            raise Exception("Waited 60 seconds and queued function was never completed.")

        result = self.result
        del self.result
        return result

class FunctionQueue(object):
    def __init__(self, fun, threads=12):
        self.queue = exec_model.queue()
        self.num_threads = threads
        self.fun = fun

    def start(self):
        self.threads = [exec_model.run(self.thread_loop) for n in range(self.num_threads)]

    def thread_loop(self):
        while True:
            (pid, args, kwargs) = self.queue.get()
            result = self.fun(*args, **kwargs)
            Promise.promise_queue.put_nowait((pid, result))

    def queue_work(self, *args, **kwargs):
        promise = Promise()
        self.queue.put_nowait((promise.pid, args, kwargs))
        return promise

def get_data_from_key(key_name):
    s3_conn = ec2.s3_connection()
    bucket = s3_conn.get_bucket(settings.FACT_BUCKET)
    key = Key(bucket)
    key.name = key_name

    cache_filename = os.path.join('/var/canvas/analytics/cache/', key.name)
    if os.path.exists(cache_filename):
        gzip_data = file(cache_filename, 'rb').read()
    else:
        try:
            os.makedirs(os.path.dirname(cache_filename))
        except OSError:
            pass
        gzip_data = key.get_contents_as_string()
        file(cache_filename, 'wb').write(gzip_data)

    try:
        return nginx_unescape(gzip.GzipFile(fileobj=cStringIO.StringIO(gzip_data)).read())
    except IOError:
        # Bad JSON / file
        return ""

t = Timing()
def sharded_iterator(start=None, stop=None, test=False, all=False):
    if not stop:
        stop = datetime.datetime.utcnow()
    # Support for timedelta stop time
    if isinstance(stop, td):
        stop = datetime.datetime.utcnow() - stop

    if not start:
        if all:
            assert not test
            start = datetime.datetime(year=2011, month=9, day=15)
        else:
            start = stop - (td(7) if not test else td(minutes=120))

    try:
        s3_conn = ec2.s3_connection()
    except boto.exception.NoAuthHandlerFound, e:
        print e
        exit("You need a ~/aws.json file. Ask Timothy for it.")

    bucket = s3_conn.get_bucket(settings.FACT_BUCKET)

    current = copy.copy(start)

    fq = FunctionQueue(get_data_from_key)

    iterators = []
    while current.date() <= stop.date():
        day = current.strftime("%Y.%m.%d")
        for key in bucket.list(prefix=day):
            filename = os.path.basename(key.name)
            name = filename.rstrip(".gz").rstrip(".log")
            timestamp, instance_id = name.split('-', 1)
            dt = datetime.datetime.strptime(day + " " + timestamp, "%Y.%m.%d %H.%M.%S")

            # If the file was within 30 minutes of the timespan, read it in.
            # (File timestamps are when the file was written, not when the data was taken)
            if start - td(minutes=30) <= dt <= stop + td(minutes=30):
                get_data = fq.queue_work(key.name)
                def row_iterator(key=key, get_data=get_data):
                    with t['blocked']:
                        data = get_data()

                    with t['process']:
                        for line in data.split('\n'):
                            if not line or line == '-':
                                continue

                            try:
                                row = FactRow(json_loads(line))
                            except ValueError, ve:
                                print >>sys.stderr, ve, repr(line)
                            else:
                                row['dt'] = datetime.datetime.utcfromtimestamp(row.get('ts', 0))
                                if start <= row['dt'] <= stop:
                                    yield row

                iterators.append(row_iterator)
        current += datetime.timedelta(1)
        
    fq.start()
    return iterators

def iterator(start=None, stop=None, test=False, all=False):
    pieces = sharded_iterator(start, stop, test, all)
    for e, iterator in enumerate(pieces):
        # Force the output so it gets sent to Jenkins in a timely fashion
        if e % 80 == 0:
            sys.stdout.write("\n%s of %s " % (e, len(pieces)))
        else:
            sys.stdout.write(".")
        sys.stdout.flush()
        for row in iterator():
            yield row
    print

def trailing_days(days=1):
    """
    Returns an iterator for results that start from now - days.

    `days`: The number of trailing days
    """
    stop = datetime.datetime.utcnow()
    start = stop - td(days=days)
    return iterator(start=start, stop=stop)


if __name__ == "__main__":
    for row in iterator(start=datetime.datetime.utcnow() - td(minutes=60)):
        print row

