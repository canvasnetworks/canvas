#!/usr/bin/env python
# http://blog.kowalczyk.info/article/Parsing-s3-log-files-in-python.html
import re

s3_line_logpats  = r'(\S+) (\S+) \[(.*?)\] (\S+) (\S+) ' \
           r'(\S+) (\S+) (\S+) "([^"]+)" ' \
           r'(\S+) (\S+) (\S+) (\S+) (\S+) (\S+) ' \
           r'"([^"]+)" "([^"]+)"'

s3_line_logpat = re.compile(s3_line_logpats)

(S3_LOG_BUCKET_OWNER, S3_LOG_BUCKET, S3_LOG_DATETIME, S3_LOG_IP,
S3_LOG_REQUESTOR_ID, S3_LOG_REQUEST_ID, S3_LOG_OPERATION, S3_LOG_KEY,
S3_LOG_HTTP_METHOD_URI_PROTO, S3_LOG_HTTP_STATUS, S3_LOG_S3_ERROR,
S3_LOG_BYTES_SENT, S3_LOG_OBJECT_SIZE, S3_LOG_TOTAL_TIME,
S3_LOG_TURN_AROUND_TIME, S3_LOG_REFERER, S3_LOG_USER_AGENT) = range(17)

s3_names = ("bucket_owner", "bucket", "datetime", "ip", "requestor_id", 
"request_id", "operation", "key", "http_method_uri_proto", "http_status", 
"s3_error", "bytes_sent", "object_size", "total_time", "turn_around_time",
"referer", "user_agent")

class S3Log(object):
    def __init__(self, results):
        self.__dict__.update(zip(s3_names, results))

def parse_s3_log_line(line):
    match = s3_line_logpat.match(line)
    result = [match.group(1+n) for n in range(17)]
    return S3Log(result)
    
def sizeof_fmt(num):
    # http://blogmag.net/blog/read/38/Print_human_readable_file_size
    for x in ['B','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0

def main():
    import os, sys, urlparse, collections
    
    if len(sys.argv) != 2:
        print "Usage: parse_s3_logs.py [logdir]"
        return
        
    basepath = sys.argv[1]
        
    zerodict = lambda: collections.defaultdict(lambda: 0)
    
    buckets = zerodict()
    domains = zerodict()
    urls = zerodict()
    bytes_by_domain = zerodict()
    
    for filename in os.listdir(basepath):
        if filename.startswith('2011-'):
            rows = 0
            print "Processing ", filename,
            for line in file(os.path.join(basepath, filename)):
                try:
                    row = parse_s3_log_line(line)
                except Exception, e:
                    print "Exception", e, "parsing", repr(line)
                    
                if row.operation != "REST.GET.OBJECT":
                    continue
                
                rows += 1
                
                url = urlparse.urlparse(row.referer)
                bytes_by_domain[url.netloc] += int(row.bytes_sent) if row.bytes_sent != '-' else 0
                
                if url.netloc in ("example.com", "example.com."):
                    buckets['1st-party'] += 1
                elif row.referer == '-':
                    buckets['none'] += 1
                else:
                    buckets['3rd-party'] += 1
                    domains[url.netloc] += 1
                    urls[row.referer] += 1
            print "rows:", rows
                    
                    
    value_sort = lambda d: sorted(d.items(), key=lambda (k,v): -v)
    def pretty(d, size = False):
        total = float(sum(d.values()))
        for key, count in value_sort(d)[:25]:
            if size:
                print sizeof_fmt(count).rjust(8, ' '), 
            else:
                print str(count).rjust(8, ' '),
            print '(%04.02f%%)' % (count/total*100), key
    
    print
    print "HITS BY URL:"
    print "-" * 80
    pretty(urls)
    print
    print "HITS BY DOMAIN:"
    print "-" * 80
    pretty(domains)
    print
    print "BYTES BY DOMAIN:"
    print "-" * 80
    pretty(bytes_by_domain, size=True)
    print
    print "SOURCES:"
    print "-" * 80
    pretty(buckets)

if __name__ == "__main__":
    main()
