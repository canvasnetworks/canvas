from collections import OrderedDict
from optparse import make_option
import os
import subprocess

from boto.exception import BotoServerError
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from django.core.management.base import BaseCommand, CommandError

from canvas.redis_models import redis
from canvas.util import flatten, gzip_string
from configuration import aws, Config
from javascripts import SCRIPTS, COMPILED_OUTPUT_DIR, ROOT_DIR
from django.conf import settings

def closure_args(input_files, output_file, root_dir=ROOT_DIR):
    args = [
        'java',
        '-jar', '/var/canvas/website/closure_compiler.jar',
        '--language_in', 'ECMASCRIPT5',
        '--compilation_level', 'SIMPLE_OPTIMIZATIONS',
        '--process_jquery_primitives',
        '--js',
    ]

    for path in OrderedDict((path, None,) for path in input_files).keys():
        args.append(os.path.join(root_dir, path))

    args.extend(['--js_output_file', output_file])

    return args

def upload_compiled_js_to_s3(local_path, s3_path):
    with file(local_path, 'rb') as handle:
        raw_filedata = handle.read()

    filedata = gzip_string(raw_filedata)

    headers = {
        'Cache-Control': 'max-age=315360000, public',
        'Expires': 'Thu, 31 Dec 2037 23:55:55 GMT',
        'Content-Encoding': 'gzip',
        'Content-Type': 'text/javascript',
    }

    conn = S3Connection(*aws)
    bucket = conn.get_bucket(Config['compress_bucket'])

    key = Key(bucket)
    key.key = s3_path
    try:
        if key.exists():
            print "Skipping", s3_path, " already exists."
        else:
            print "Uploading %s (%s kb)" % (s3_path, len(filedata) // 1024)
            key.set_contents_from_string(filedata, headers=headers)
    except BotoServerError, bse:
        print bse

def s3_path(compiled_js_filename):
    return '/compiled_js/' + compiled_js_filename

def s3_url(compiled_s3_path):
    return '//canvas-dynamic-assets.s3.amazonaws.com/static/' + compiled_s3_path.lstrip('/')

class Command(BaseCommand):
    args = ''
    help = ''

    option_list = BaseCommand.option_list + (
        make_option('--force',
            action='store_true',
            dest='force',
            default=False,
            help='Force offline compression regardless of COMPRESS_OFFLINE'),
        )

    def handle(self, *args, **options):
        if not settings.COMPRESS_OFFLINE and not options.get('force'):
            print "COMPRESS_OFFLINE must be True, or --force used to run."
            return

        # Make output dir.
        subprocess.check_call(['mkdir', '-p', COMPILED_OUTPUT_DIR])

        compiled_paths, compiled_s3_paths, compiled_s3_urls = {}, {}, {}
        for bundle_name, input_files in SCRIPTS.items():
            # Compile JS.
            output_path = os.path.join(COMPILED_OUTPUT_DIR, bundle_name)
            args = closure_args(input_files, output_path)
            print subprocess.check_output(args, stderr=subprocess.STDOUT)

            # Rename files with hash suffixes.
            suffix = '-' + subprocess.check_output(['git', 'hash-object', output_path]).strip()
            hashed_output_name = '{}{}.js'.format(bundle_name, suffix)
            hashed_output_path = os.path.join(COMPILED_OUTPUT_DIR, hashed_output_name)
            os.rename(output_path, hashed_output_path)

            compiled_paths[bundle_name] = hashed_output_path
            compiled_s3_path = compiled_s3_paths[bundle_name] = s3_path(hashed_output_name)
            compiled_s3_urls[bundle_name] = s3_url(compiled_s3_path)

        # Upload to S3.
        for bundle_name, local_path in compiled_paths.items():
            upload_compiled_js_to_s3(local_path, compiled_s3_paths[bundle_name])

        redis.delete('compiled_js_file_urls')
        redis.hmset('compiled_js_file_urls', compiled_s3_paths)

