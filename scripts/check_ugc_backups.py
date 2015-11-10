from datetime import datetime, date, timedelta
import os
import sys; sys.path += ['/var/canvas/common', '../../common']
import yaml

from boto.s3.connection import S3Connection

from configuration import aws

# results format
#    {
#        'start_time': start_time,
#        'end_time': end_time,
#        'time': (end_time - start_time),
#        'stored': stored,
#        'skipped': skipped,
#        'failed': failed,
#        'size': backup_size_str,
#    }

results_bucket_name = 'canvas-ugc-backup-logging'
key_format_str = 'ugc-backup-results-{0}'

def datestr(_date=date.today()):
    return "{0}{1}{2}".format(_date.year, str(_date.month).zfill(2), str(_date.day).zfill(2))

def get_last_key():
    today = date.today()
    yesterday = today - timedelta(days=1)
    return key_format_str.format(datestr(yesterday))

def max_key(bucket):
    max_key = ''
    for key in bucket:
        if key.name > max_key:
            max_key = key.name
    return max_key

def are_results_recent(results):
    today = datetime.utcnow()
    start = results['start_time']
    yesterday = today - timedelta(days=2)
    if start < yesterday:
        return False
    return True

def print_results(results):
    start = results['start_time']
    end = results['end_time']
    print "Start: {0}".format(start)
    print "Finished: {0}".format(end)
    print "Time: {0}".format(str(end - start))
    print "Stored: {0}".format(results['stored'])
    print "Skipped: {0}".format(results['skipped'])
    print "Failed: {0}".format(results['failed'])
    print "Size: {0}".format(results['size'])
    try:
        print "Failed list:\n{0}".format(results['failed_list'])
    except KeyError:
        pass

def check_backups():
    conn = S3Connection(*aws)
    bucket = conn.get_bucket(results_bucket_name)
    key = max_key(bucket)
    results_str = bucket.get_key(key).get_contents_as_string()
    results = yaml.load(results_str)
    print_results(results)
    if are_results_recent(results) and results['failed'] == 0:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    check_backups()

