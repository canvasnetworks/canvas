#!/usr/bin/env python
import sys; sys.path += ['/var/canvas/common', '../../common']
import os

from configuration import Config

def generate_conf(name, context={}):
    template = file(os.path.join("/var/canvas/deploy/ec2", name)).read()

    for key, value in context.items():
        template = template.replace("{{ %s }}" % key, value)

    return template

def main():
    context = Config['aws']
    dot_s3cfg = generate_conf('.s3cfg.template', context)
    file("/home/ubuntu/.s3cfg", 'w').write(dot_s3cfg)

if __name__ == "__main__":
    main()