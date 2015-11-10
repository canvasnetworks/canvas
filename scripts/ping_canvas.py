import urllib, time, collections


trailing_times = collections.deque(maxlen=1000)

def percentile(data, p):
    return sorted(data)[int(float(len(data)) / 100 * p)]

while True:
    start = time.time()
    result = urllib.urlopen("http://example.com/").read()
    end = time.time()

    elapsed = int((end-start) * 1000)

    trailing_times.append(elapsed)

    print elapsed, 'ms', len(result), 'bytes', 
    for th in (50, 90, 95, 99):
        print "%sth: %s" % (th, percentile(trailing_times, th)), 
    print
    time.sleep(10)
