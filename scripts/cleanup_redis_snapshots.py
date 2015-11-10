#!/usr/bin/python

from datetime import datetime, date, timedelta
import os
import sys; sys.path += ['/var/canvas/common', '../../common']
import yaml
from collections import defaultdict

from boto.ec2.connection import EC2Connection

from configuration import aws

def clean_backups():
    """
    dumb script that cleans up all the duplicate ebs snapshots our two cron servers
    create while backing up redis
    """
    conn = EC2Connection(*aws)
    snapshots = conn.get_all_snapshots()
    shots = defaultdict(list)
    for snapshot in conn.get_all_snapshots(owner=352407978521):
        if snapshot.tags.get('Name') is not None:
            t = snapshot.tags['Name']
            ttype = ""
            if 'Pink' in t:
                ttype = 'pink'
            elif 'Yellow' in t:
                ttype = 'yellow'
            dt = datetime.strptime(snapshot.start_time, "%Y-%m-%dT%H:%M:%S.000Z")
            key = (ttype, dt.year, dt.month, dt.day)
            val = snapshot.id

            shots[key].append(val)

    to_delete = []
    for k, v in shots.iteritems():
        if len(v) >= 2:
            to_delete.append(v[0])

    for d in to_delete:
        print "deleting", d, "..."
        conn.delete_snapshot(d)


if __name__ == '__main__':
    clean_backups()