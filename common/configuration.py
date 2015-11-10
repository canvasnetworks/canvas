import json
import os
import platform
import sys

TESTING_BOX = os.path.exists('/etc/canvas/testing')
TESTING = 'test' in sys.argv
PRODUCTION = not TESTING and not TESTING_BOX and os.path.exists('/etc/canvas')
AWS_CREDENTIALS_PATH = '/etc/canvas/aws.json'
AWS_ALT_CREDENTIALS_PATH = os.path.expanduser('~/aws.json')

LOCAL_SANDBOX = platform.system() == 'Darwin'

Config = {
    # AWS credentials are filled in by puppet based on the role.
    'aws': {'access_key': None, 'secret_key': None},
    'facebook': {'app_id': '176245562391022', 'secret': '8682cb9e15760cba8ad34d03f8d80f0a'},

    'image_bucket': 'canvas_public_ugc',
    'image_fs': ('s3', 'canvas_public_ugc') if PRODUCTION else ('local', '/var/canvas/website/ugc'),
    'chunk_fs': ('s3', 'canvas-upload-pieces') if PRODUCTION else ('local', '/var/canvas/website/ugc/upload_pieces'),

    'drawquest_image_fs': ('s3', 'drawquest_public_ugc') if PRODUCTION else ('local', '/var/canvas/website/drawquest/ugc'),

    'script_bucket': 'canvas-public-plugins',
    'script_base_url': 'http://canvas-public-plugins.s3-website-us-east-1.amazonaws.com/' if PRODUCTION else 'http://savnac.com:9000/ugc/local_script_drop/',

    'compress_bucket': 'canvas-dynamic-assets',

    'default_following_groups': [
        'funny',
    ],

    'featured_groups': [
        'abstract',
        'canvas',
        'cute',
        'drawing',
        'funny',
        'gif_bin',
        'photography',
        'pop_culture',
        'video_games',
    ],

    'remixable_comments_daves_local': [
        "q6w",
        "q7f",
        "q8y",
        "q9h",
        "qa0",
        "qbj",
    ],

    'remixable_comments': [
        "nep4u",
        "ne708",
        "nvtun",
        "nx8v5",
        "nc5ae",
        "nsbyo",
    ],

    'additional_whitelisted_groups': [
        'drawcast',
        'cats',
    ],

    # All comparisons done against lowercase version of username.
    'blocked_usernames': ['moot', 'm00t', 'mootykins', 'm00tykins', 'chrispoole', 'christopherpoole', 'public', 'private', 'admin'],
    'blocked_username_fragments': ['canvas', 'administrator', 'drawquest'],

    'autoflag_words': ['fag', 'faggot', 'nigger', 'nigga', 'whore', 'jew', 'chink'],

    # Top replies settings in threads view.
    'minimum_top_replies': 3,
    'maximum_top_replies': 20,
    'posts_per_top_reply': 20,

    # Feature switches.
    # DEPRECATED, use apps.features instead.
    'show_login': True,

    # Reply boost.
    'reply_boost': 1.1,

    # If you change this, be sure to update the Jenkins node.
    'fact_host': '%s:9999' % ('ip-10-12-99-188.ec2.internal' if PRODUCTION else '127.0.0.1'),
    'drawquest_fact_host': '%s:9999' % ('ip-10-34-102-100.ec2.internal' if PRODUCTION else '127.0.0.1'),

    # Master.
    'redis_host': 'ip-10-84-89-110.ec2.internal' if PRODUCTION else 'localhost',
    'redis_slave': 'ip-10-218-7-231.ec2.internal' if PRODUCTION else None,

    'drawquest_redis_host': 'ip-10-83-142-11.ec2.internal' if PRODUCTION else 'localhost',
    'drawquest_redis_slave': 'ip-10-203-46-105.ec2.internal' if PRODUCTION else None,

    'memcache_hosts': ['cache_0.example.com:11211', 'cache_1.example.com:11211'] if PRODUCTION else ['127.0.0.1:11211'],
    'drawquest_memcache_hosts': [
        'cache_0.example.com:11211',
        'cache_1.example.com:11211',
        'cache_2.example.com:11211',
        'cache_3.example.com:11211',
    ] if PRODUCTION else ['127.0.0.1:11212'],

    'autoscale_group': 'web-sg-bd3a',
    'elb': 'canvas-load-balancer',

    'test_bgwork_path': '/var/canvas/website/run/test_bgwork' if not PRODUCTION else '',
}

_load_config = lambda path: Config.update(json.load(open(path)))

assert Config['redis_host'] != Config['redis_slave'], 'sanity check, you probably forgot to update the standby!'

# Load the AWS credentials for the box.
if os.path.exists(AWS_CREDENTIALS_PATH):
    _load_config(AWS_CREDENTIALS_PATH)
elif os.path.exists(AWS_ALT_CREDENTIALS_PATH):
    _load_config(AWS_ALT_CREDENTIALS_PATH)

# For convenience
aws = (Config['aws']['access_key'], Config['aws']['secret_key'])

