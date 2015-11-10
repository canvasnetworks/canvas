import urllib, time, collections
from redis import Redis

trailing_times = collections.deque(maxlen=10000)

def percentile(data, p):
    return sorted(data)[int(float(len(data)) / 100 * p)]

REDIS_PORT = 6379
REDIS_HOST = 'ip-10-218-7-231.ec2.internal'
REDIS_DB_MAIN = 0

redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_MAIN)

while True:
    start = time.time()
    result = redis.get("foo")
    end = time.time()

    elapsed = int((end-start) * 1000)

    trailing_times.append(elapsed)

    if elapsed < 3000:
        continue

    print elapsed, 'ms', len(result), 'bytes',
    for th in (50, 90, 95, 99):
        print "%sth: %s" % (th, percentile(trailing_times, th)),
    print
    time.sleep(1)
