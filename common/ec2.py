import commands
import itertools
import sys
import os

from configuration import Config

def _connect(conn_class):
    return conn_class(Config['aws']['access_key'], Config['aws']['secret_key'])

def connection():
    from boto.ec2.connection import EC2Connection
    return _connect(EC2Connection)

def autoscale_connection():
    from boto.ec2.autoscale import AutoScaleConnection
    return _connect(AutoScaleConnection)

def cloudwatch_connection():
    from boto.ec2.cloudwatch import CloudWatchConnection
    return _connect(CloudWatchConnection)

def elb_connection():
    from boto.ec2.elb import ELBConnection
    return _connect(ELBConnection)

def s3_connection():
    from boto.s3.connection import S3Connection
    return _connect(S3Connection)

def check_output(command):
    # In Python 2.7 we can just use subprocess.check_output.
    status, output = commands.getstatusoutput(command)
    if status != 0:
        raise Exception(output)
    return output

# Want to add a new role? Check out https://sites.google.com/a/example.com/canvas/operations/creating-a-new-role
category = {
    # Roles that talk to backend roles
    'frontend': ['web', 'cron', 'sentry', 'redislive', 'drawquest_web'],

    # Roles that are talked to by frontend roles
    'backend': ['redis', 'solr', 'factlog'],

    # Roles with unique communication patterns
    'utility': ['jenkins', 'gateway', 'puppetmaster'],

    # Roles that talk to no one
    'isolated': ['gaming', 'testrunner', 'drawquest_testrunner'],
}

roles = list(itertools.chain.from_iterable(category.values()))

def get_role_size(role):
    return {
        'redis': 'm1.large',
        'gateway': 't1.micro',
        'sentry': 't1.micro',
        'puppetmaster': 't1.micro',
        'web': 'c1.medium',
        'drawquest_web': 'c1.medium',
        'testrunner': 'c1.medium',
        'drawquest_testrunner': 'c1.medium',
    }.get(role, 'm1.small')

def get_category(role):
    for cat, roles in category.items():
        if role in roles:
            return cat

def is_valid_role(role):
    return bool(get_category(role)) or (role.endswith("_debug") and bool(get_category(role[:-len("_debug")])))

def get_groups(role):
    categories = ["all"]

    if role.endswith("_debug"):
        categories.append("debug")
        role = role[:-len("_debug")]

    categories += [role, get_category(role)]

    return categories

def get_instances(conn, *args, **kwargs):
    for reservation in conn.get_all_instances(*args, **kwargs):
        for instance in reservation.instances:
            yield instance

def get_instance_id():
    return check_output("wget -q -O - http://169.254.169.254/latest/meta-data/instance-id")

