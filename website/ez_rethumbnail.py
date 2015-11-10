#!/usr/bin/env python
import threading
import subprocess
import sys

import sys; sys.path += ['/var/canvas/common', '../../common']
import time

import ec2

from configuration import Config

conn = ec2.connection()

running = {'instance-state-name': 'running', 'tag:CanvasStatus': 'bootstrapped'}

def dns(instances):
    return ["%s:30583" % instance.private_dns_name for instance in instances]

def group(group_name, limit=None):
    return dns(ec2.get_instances(conn, filters=dict(running, **{'group-name': group_name})))[:limit]

def rethumbnail(start, stop, stdout):
    subprocess.Popen(["python", "manage.py", "rethumbnail_images", str(start), str(stop)], stdout=stdout, stderr=subprocess.STDOUT).communicate()

def main(threads_per):
    workers = group('Cron')
    num_workers = len(workers)
    interval = (1.0 / (num_workers * threads_per))
    to_run = []
    threads = []

    for i in range(num_workers):
        worker = workers[i]
        for n in range(threads_per):
            start = (i * 2 + n) * interval
            end = start + interval
            cmd = "m rethumbnail_images {} {}".format(start, end)
            to_run.append((worker, start, end))

    for host, start, stop in to_run:
        thread = threading.Thread(target=rethumbnail, args=(start, stop, sys.stdout))
        thread.start()
        threads.append(thread)
    [thread.join() for thread in threads]


if __name__ == "__main__":
    raise Exception("this doesn't work yet for want of ssh stuffs")
    try:
        threads_per = int(sys.argv[1])
    except IndexError:
        threads_per = 2
    main(threads_per)

