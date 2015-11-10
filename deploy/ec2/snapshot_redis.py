#!/usr/bin/env python
import sys; sys.path.insert(0, '/var/canvas/common')
import datetime

import boto, ec2
conn = ec2.connection()

def group(group_name):
    return ec2.get_instances(conn, filters={'instance-state-name': 'running', 'group-name': group_name})

vols = dict([(v.id, v) for v in conn.get_all_volumes()])
snapshot_name = "redis automated backup"
dev = '/dev/sdf'
redii = list(group("Redis"))

print "Beginning snapshot of %s for %s redis instances." % (dev, len(redii))
for redis in redii:
    try:
        devs = redis.block_device_mapping
        redis_ebs = devs[dev]
        redis_vol = vols[redis_ebs.volume_id]
        snap = redis_vol.create_snapshot(snapshot_name)
        print "%s SUCCESS: %s" % (redis, snap)
    except Exception:
        pass

