import os
import re
import subprocess
import sys

path = "/Volumes/Backup/ugc-backups"

failed = 0
succeeded = 0

def shasum(fname):
    hash_output = subprocess.Popen(['shasum', fname], stdout=subprocess.PIPE).communicate()[0]
    try:
        return hash_output.split()[0]
    except IndexError:
        print hash_output
        return "doesnotmatch"

def check_hash(root_path, sub_dir, filename):
    full_path = "{0}/{1}/{2}".format(root_path, sub_dir, filename)
    expected = re.sub(r'^([^\.]+)\..+$', r'\1', filename)
    actual = shasum(full_path)
    correct = (expected == actual)
    if not correct:
        print "{0}-{1}:{2}".format(full_path, actual, correct)
    return correct

try:
    for top_root, top_dirs, top_files in os.walk(path):
        for d in top_dirs:
            for root, dirs, files in os.walk("{0}/{1}".format(path, d)):
                for f in files:
                    if not f.startswith("."):
                        if check_hash(path, d, f):
                            succeeded += 1
                        else:
                            failed += 1
except KeyboardInterrupt:
    print "finishing up..."
    print

print "{0} failed".format(failed)
print "{0} succeeded".format(succeeded)
sys.exit(failed)
