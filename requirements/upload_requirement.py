#!/usr/bin/env python
import sys; sys.path += ['/var/canvas/common', '../../common']
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import urllib2
import os
import urlparse
import json
from configuration import aws

BUCKET = "canvas-public-artifacts"

def get_url(info):
    for url in info["urls"]:
        if url['python_version'] == 'source':
            return url["url"]

def upload_requirement(requirement):
    conn = S3Connection(*aws)
    try:
        info_raw = urllib2.urlopen("http://pypi.python.org/pypi/%s/json" % requirement).read()
    except urllib2.HTTPError, error:
        if error.code == 404:
            print "Package not found (%r)" % requirement
            sys.exit(1)
        else:
            raise
        
    info = json.loads(info_raw)

    url = get_url(info)
    if not url:
        url = info['info']['download_url']

    if not url:
        print "No source package found."
        sys.exit(1)

    print "Fetching", url

    filedata = urllib2.urlopen(url).read()

    conn = S3Connection(*aws)
    bucket = conn.get_bucket(BUCKET)

    key = Key(bucket)
    key.key = os.path.basename(urlparse.urlparse(url).path)

    print "Uploading %s (%s kb)" % (key.key, len(filedata) // 1024)
    key.set_contents_from_string(filedata, headers={'Content-Type': 'application/x-compressed'})
    print "Success!"
    print
    print "Now add this URL to the appropriate requirements text file:\nhttps://s3.amazonaws.com/%s/%s" % (BUCKET, key.key)
    print

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage: python ./upload_requirement.py [package name]"
    else:
        upload_requirement(sys.argv[1])