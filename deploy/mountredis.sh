#!/bin/bash
set -ex
# If you change the mount command, update the classes.pp::redis fstab entry!
sudo mount -t ext4 /dev/xvdf /var/redis
sudo chown -R redis.redis /var/redis
sudo /etc/init.d/redis-server restart

# Look here now https://sites.google.com/a/example.com/canvas/operations/redis
