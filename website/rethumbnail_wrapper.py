#!/usr/bin/env python
import threading
import subprocess
import sys

def rethumbnail(start, stop, stdout, rethumbnail_args):
    subprocess.Popen(["python", "manage.py", "rethumbnail_images", str(start), str(stop)] + rethumbnail_args, stdout=stdout, stderr=subprocess.STDOUT).communicate()

def main(num_threads, rethumbnail_args):
    threads = []
    percents = [1.0/num_threads*x for x in range(num_threads+1)]
    for i, start in enumerate(percents[:-1]):
        stop = percents[i+1]
        thread = threading.Thread(target=rethumbnail, args=(start, stop, sys.stdout, rethumbnail_args))
        thread.start()
        threads.append(thread)
    [thread.join() for thread in threads]

if __name__ == "__main__":
    threads = int(sys.argv[1])
    rethumbnail_args = sys.argv[2:]
    main(threads, rethumbnail_args)
