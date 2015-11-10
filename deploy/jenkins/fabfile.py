import functools
import pipes
import sys; sys.path += ['/var/canvas/common', '../../common']
import time
from datetime import datetime

from fabric.api import *
import ec2

from configuration import Config


conn = ec2.connection()

running = {'instance-state-name': 'running', 'tag:CanvasStatus': 'bootstrapped'}


def dns(instances):
    return ["%s:30583" % instance.private_dns_name for instance in instances]

def all_hosts():
    return dns(ec2.get_instances(conn, filters=running))

def group(group_name, limit=None):
    return dns(ec2.get_instances(conn, filters=dict(running, **{'group-name': group_name})))[:limit]

def redis_master():
    return [host for host in group('Redis') if host.split(':')[0] == Config['redis_host']]

def redis_slaves():
    return [host for host in group('Redis') if host.split(':')[0] != Config['redis_host']]


env.user = 'ubuntu'
env.roledefs.update({
    'all': all_hosts,
    'web': functools.partial(group, 'Web'),
    'drawquest_web': functools.partial(group, 'Drawquest_web'),
    # Testrunner isn't included in nonweb since it needs to manage its own version, otherwise deploys can roll it back mid-test and break things.
    'nonweb': lambda: set(all_hosts()) - set(group('Web')) - set(group('Testrunner')) - set(group('Drawquest_web')) - set(group('Drawquest_testrunner')),
    'pips': lambda: set(group('Web') + group('Drawquest_web') + group('Cron') + group('Testrunner') + group('Drawquest_testrunner') + group('Sentry')),
    'production': lambda: set(group('Frontend') + group('Backend') + group('Utility')),
    'redis_master': [Config['redis_host'] + ":30583"],
    'redis_slave': [Config['redis_slave'] + ":30583"],
})

@roles('all')
def whoami():
    with cd('/var/canvas/website'):
        run('whoami')

def _update(commit, branch='master'):
    with cd('/var/canvas/'):
        run('git checkout {}'.format(branch))
        run('git pull origin {} -q'.format(branch))
        run('git checkout %s' % commit)

@roles('nonweb')
def update_nonweb(commit='HEAD'):
    _update(commit)


@roles('web')
def update_and_build_web(commit='HEAD'):
    _update(commit, branch='canv_dot_as')
    with cd('/var/canvas/website'):
        run('python manage.py compress')

@roles('drawquest_web')
def update_and_build_drawquest_web(commit='HEAD'):
    _update(commit)

def nginx():
    with cd('/var/canvas/website'):
        if env.host_string in env.roledefs['drawquest_web']():
            run('./nginx.py --project=drawquest')
        else:
            run('./nginx.py')

@roles('web')
def reconfig_web():
    nginx()

@roles('drawquest_web')
def reconfig_drawquest_web():
    nginx()

@roles('web', 'drawquest_web')
def hard_restart_gunicorn():
    with cd('/var/canvas/website'):
        run('kill `cat run/gunicorn.pid`')
    nginx()

@roles('pips')
def pip_install_requirements():
    with cd('/var/canvas'):
        # Since this runs on production boxes in the ELB, let's be nice about it, as it may result in compilation.
        sudo('nice -n 10 pip install --download-cache=/tmp -r requirements/requirements_for_this_instance.txt --no-index')

@roles('all')
def upgrade_package(package):
    with settings(warn_only=True):
        if not 'Status: install ok' in sudo('dpkg -s %s' % package):
            print "Package %s not installed, not attempting to upgrade." # When upgrading, don't just intall the package everywhere
            return

    sudo('apt-get -qq update')
    sudo('DEBIAN_FRONTEND=noninteractive apt-get -q -y install %s' % package)

@roles('all')
def update_apt_cache():
    sudo('apt-get -qq update')

@roles('all')
def puppet():
    with settings(warn_only=True):
        sudo('puppetd --test')

def cloudwatch_metric(name, command, unit="Kilobytes"):
    with cd('/var/canvas/common'):
        run('python /var/canvas/deploy/ec2/put_metric %s %s %s' % (name, unit, pipes.quote(command)))

@roles('redis_master')
def update_redis_slave_sync_ts():
    run('redis-cli set redis_slave_sync_ts "`date +%s`"')

@roles('redis_slave')
def check_redis_slave_sync_ts(timeout=120):
    timeout = float(timeout)

    with settings(warn_only=True):
        slave_of = run('redis-cli info | grep "master_host:"').strip().split(':')[-1]

    if slave_of != Config['redis_host']:
        raise Exception("Redis slave is not syncing with the redis master.")

    try:
        ts = float(run('redis-cli get redis_slave_sync_ts').replace('"', ''))
    except ValueError:
        raise Exception('No redis_slave_sync_ts key found, or invalid value.')

    now = time.time()
    print 'Time now:', now

    if now < ts:
        raise Exception('Redis slave sync timestamp is somehow in the future.')

    if now - ts > timeout:
        raise Exception('Redis slave is out of sync, as of {0} seconds ago: {1}'.format(int(ts - time.time()),
                                                                                        env.host))

def rethumbnail(settings='settings'):
    hosts = [
        # put internal hostnames here
    ]

    threads_per = 4
    num_workers = len(hosts)
    interval = (1.0 / (num_workers * threads_per))

    for i in range(num_workers):
        worker = hosts[i]
        with settings(host_string="{}:30583".format(worker)):
            with settings(warn_only=True):
                run('killall -9 python')
            for n in range(threads_per):
                start = (i * threads_per + n) * interval
                end = start + interval
                cmd = "DJANGO_SETTINGS_MODULE={} screen -d -m python manage.py rethumbnail_images {} {}".format(settings, start, end)
                with cd('/var/canvas/website'):
                    run(cmd, pty=False)

@roles('redis_master')
def backup_redis():
    with cd('/var/redis'):
        date_string = datetime.now().strftime("%Y-%m-%d")
        fname = "/mnt/redis-master-{}.tgz".format(date_string)
        sudo('tar czf {} dump.rdb'.format(fname))
        sudo('s3cmd put {} s3://canvas-redis-backup/ --no-progress'.format(fname))
        sudo('rm {}'.format(fname))

