#!/usr/bin/python

from datetime import datetime, date, timedelta
import os
import sys; sys.path += ['/var/canvas/common', '../../common']
import yaml
import datetime
from collections import defaultdict

from boto.rds import RDSConnection

from configuration import aws

def snapshot_rds():
    """
    dumb script that cleans up all the duplicate ebs snapshots our two cron servers
    create while backing up redis
    """

    (key, secret) = aws
    conn = RDSConnection(key, secret)

    for db in conn.get_all_dbinstances():
        print "backing up rds", db.id, "..."
        now = datetime.datetime.now()
        conn.create_dbsnapshot("snapshot-backup-{0}".format(now.strftime("%Y-%m-%d")), db.id)

if __name__ == '__main__':
    snapshot_rds()