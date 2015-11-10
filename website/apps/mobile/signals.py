from compressor.signals import post_compress

from canvas.redis_models import RedisHash

class _CompressedFiles(object):
    hashes = {
        'css': RedisHash('compressed:css'),
        'js': RedisHash('compressed:js'),
    }

    def set(self, type, name, path):
        self.hashes[type].hset(name, path)

    def get(self, type, name):
        return self.hashes[type].hget(name)

compressed_files = _CompressedFiles()

def watch_compressed_files(sender, type, mode, context, **kwargs):
    """ Only works with Django templates, since the Jinja one doesn't parse the name field. """
    name = context.get('name')
    if name and mode == "file":
        compressed_files.set(type, name, context['url'])

post_compress.connect(watch_compressed_files)

