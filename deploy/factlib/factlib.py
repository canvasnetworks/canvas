from ctypes import *
import os
import itertools
import sys

def _python_nginx_unescape(line):
    pointer = 0
    result = []
    while True:
        next = line.find('\\x', pointer)
        if next == -1:
            result.append(line[pointer:])
            break

        result.append(line[pointer:next])
        result.append(chr(int(line[next+2:next+4], 16)))
        pointer = next + 4

    return "".join(result)

def _c_nginx_unescape(line):
    buff = create_string_buffer(line)
    _factlib.nginx_unescape(buff)
    return buff.value
    

try:
    for extension, path in itertools.product(('dylib', 'so'), sys.path):
        path = os.path.join(path, "_factlib.%s" % extension)
        if os.path.exists(path):
            _factlib = cdll.LoadLibrary(path)
            break
    else:
        print >>sys.stderr, "WARNING: Couldn't find _factlib compiled C module. Please reinstall! (Falling back to python, VERY SLOW!)"
        _factlib = None
except OSError:
    print >>sys.stderr, "WARNING: Couldn't load _factlib compiled C module. Please reinstall! (Falling back to python, VERY SLOW!)"
    _factlib = None

nginx_unescape = _c_nginx_unescape if _factlib else _python_nginx_unescape
