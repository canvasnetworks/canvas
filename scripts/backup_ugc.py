from datetime import datetime, date
import os
import re
import subprocess
import yaml

from boto.s3.connection import S3Connection

bucket_name = 'canvas_public_ugc'
results_bucket_name = 'canvas-ugc-backup-logging'
bucket_path = 'original'
base_dest = '/Volumes/Backup/ugc-backups'
prefix_dir_length = 3
use_date_directories = False

def datestr():
    today = date.today()
    return "{0}{1}{2}".format(today.year, str(today.month).zfill(2), str(today.day).zfill(2))

def destination_directory():
    if use_date_directories:
        return "{0}/{1}".format(base_dest, datestr())
    else:
        return base_dest

def ensure_destination_directory(name):
    if not os.path.exists(name):
        os.makedirs(name)

def shasum(fname):
    hash_output = subprocess.Popen(['shasum', fname], stdout=subprocess.PIPE).communicate()[0]
    try:
        return hash_output.split()[0]
    except IndexError:
        print hash_output
        return "doesnotmatch"

def check_hash(full_path, filename):
    expected = re.sub(r'^([^\.]+)\..+$', r'\1', filename)
    actual = shasum(full_path)
    correct = (expected == actual)
    if not correct:
        print "{0}-{1}:{2}".format(full_path, actual, correct)
    return correct

def get_dir_size(name):
    p1 = subprocess.Popen(['df', '-h'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['grep', 'Backup'], stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()
    return p2.communicate()[0]

def store_results(start_time, end_time, stored, skipped, failed, failed_list):
    keyname = 'ugc-backup-results-{0}'.format(datestr())
    conn = S3Connection()
    bucket = conn.get_bucket(results_bucket_name)
    key = bucket.new_key(keyname)
    backup_size_str = get_dir_size(destination_directory())
    report = {
        'start_time': start_time,
        'end_time': end_time,
        'stored': stored,
        'skipped': skipped,
        'failed': failed,
        'size': backup_size_str,
        'failed_list': failed_list,
    }
    key.set_contents_from_string(yaml.dump(report))

def do_backup():
    stored = 0
    skipped = 0
    failed = 0
    failed_list = []
    start_time = datetime.utcnow()

    dest = destination_directory()
    ensure_destination_directory(dest)
    conn = S3Connection()
    bucket = conn.get_bucket(bucket_name)

    try:
        for k in iter(bucket.list(prefix=bucket_path)):
            try:
                if not k.name.endswith("/"):
                    key_part = k.name.split('/')[1]
                    sdir = "{0}/{1}".format(dest, key_part[:prefix_dir_length])
                    fname = "{0}/{1}".format(sdir, key_part)
                    ensure_destination_directory(sdir)

                    if not os.path.exists(fname):
                        print "Getting {0}/{1} ...".format(bucket.name, k.name),
                        k.get_contents_to_filename(fname)
                        print "done"
                        if check_hash(fname, key_part):
                            stored += 1
                        else:
                            raise Exception("File content does not match hash")
                    else:
                        skipped += 1

            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                failed_list.append(k.name)
                failed += 1

    except KeyboardInterrupt:
        print
        print "finishing up..."
    finally:
        store_results(start_time, datetime.utcnow(), stored, skipped, failed, failed_list)


if __name__ == "__main__":
    do_backup()

