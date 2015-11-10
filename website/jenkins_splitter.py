from collections import defaultdict
import json
import os.path
import pickle
import re
import subprocess
import urllib2

def get_existing(project='canvas'):
    args = ["python", "manage.py", "test", "--collect-only", "--with-id", "--exclude=compressor", "--noinput"]
    if project == 'drawquest':
        args = ['DJANGO_SETTINGS_MODULE=settings_drawquest'] + args
    subprocess.check_call(args)
    return set((i[1] for i in pickle.load(open('.noseids'))['ids'].values()))

def get_previous():
    test_class_durations = defaultdict(int)

    aggregatedReport = subprocess.check_output(["curl", "-k", "https://canvas:REDACTED@jenkins.example.com/job/run_tests_in_parallel/lastStableBuild/aggregatedTestReport/"])
    downstreamReports = re.findall('"([^"]+/testReport/)"', aggregatedReport)

    for report in downstreamReports:
        results = json.loads(subprocess.check_output(["curl", "-k", "https://canvas:REDACTED@jenkins.example.com/%s/api/json" % report]))

        for result in results['suites']:
            for case in result['cases']:
                filename = '.'.join(case['className'].split('.')[:-1])
                # 2012-2-6 Looks like there's about 1.1s of Django test overhead not being accounted for here
                test_class_durations[filename] += float(case['duration']) + 1.1

    return test_class_durations

def main(num_buckets=2):
    """
    num_buckets is for canvas tests. drawquest only uses one bucket for now.
    """
    buckets = [[[], 0] for i in range(num_buckets)]

    testfiles = get_existing()
    durations = get_previous()
    avg = sum(durations.values()) / len(durations) if durations else 1

    for testfile in sorted(testfiles, key=lambda x: -durations.get(x, avg)):
        duration = durations.get(testfile, avg)
        shortest_bucket = sorted(buckets, key=lambda x: x[1])[0]
        shortest_bucket[0].append(testfile)
        shortest_bucket[1] += duration

    print "Created %s buckets of durations: %s" % (num_buckets, [x[1] for x in buckets])
    properties = ""
    for i, bucket in enumerate(buckets):
        print "cpytest %s" % " ".join(bucket[0])
        properties += "BUCKET_%i = %s\n" % (i, " ".join(bucket[0]))
    open("buckets.properties", "w").write(properties)

if __name__ == '__main__':
    main()

