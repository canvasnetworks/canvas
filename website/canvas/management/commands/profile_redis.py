import collections
import operator
import re

from django.core.management.base import BaseCommand, CommandError

from django.conf import settings
from canvas.redis_models import CanvasRedis

class Command(BaseCommand):
    args = 'sample_size'
    help = "Profile redis based on random key sampling. Override host with localhost for local testing."

    def handle(self, sample='10000', host='ip-10-203-46-218.ec2.internal', *args, **options):
        slave_redis = CanvasRedis(host=host, port=settings.REDIS_PORT, db=settings.REDIS_DB_MAIN)
        slave_cache = CanvasRedis(host=host, port=settings.REDIS_PORT, db=settings.REDIS_DB_CACHE)
        
        if sample != "*":
            sample = int(sample)

        def human(size):
            # Multiply size * 3 to roughly account for the difference in RDB vs in-memory size.
            return "%.1f MB" % (size * 3 / 1000000.0)

        for client in (slave_redis, slave_cache):
            dbsize = client.dbsize()
            if sample == "*":
                print "Summarizing total memory usage for db %s" % client.connection.db
                key_names = client.keys("*")
            else:
                groups = collections.defaultdict(lambda: 0)
                sizes = []
                scalar = 1.0 * dbsize / sample
                print "Sampling %s random keys (of %s) from db %s" % (sample, dbsize, client.connection.db)
                pipeline = client.pipeline()
                for i in range(sample):
                    pipeline.randomkey()
                key_names = pipeline.execute()

            chunksize = 10000
            cursor = 0
            key_sizes = []
            while cursor < len(key_names):
                pipeline = client.pipeline()
                for result in key_names[cursor:cursor+chunksize]:
                    pipeline.execute_command("DEBUG", "OBJECT", result)
                debug_chunk = pipeline.execute()
                for i, result in enumerate(debug_chunk):
                    debug_dict = dict([kv.split(':') for kv in ('type:' + result).split()])
                    key = key_names[cursor + i]
                    keysize = int(debug_dict['serializedlength']) + len(key)
                    key_sizes.append(keysize)
                cursor += chunksize

            if sample == "*":
                print human(sum(key_sizes))
                continue

            # TODO: msg_backlogs look big, figure out how to group these (probably show biggest 25 keys too)
            for key, keysize in zip(key_names, key_sizes):
                keygroup = re.sub("(?<=[:\.]).+(?=[:\.])", "#", key)
                groups[keygroup] += keysize

            print "== TOP 10 RESULTS =="
            for k in sorted(groups, key=lambda k: -groups[k])[:10]:
                size = groups[k]
                print k, human(size * scalar)
            avg = 1.0 * sum(key_sizes) / len(key_sizes)
            print "Average key size: %s (%s estimated total)" % (avg, human(avg * dbsize))
            print ""

