#!/usr/bin/env python
""" Customized to allow for DJANGO_SETTINGS_MODULE. Inspired by Django 1.4. """
import os
import sys

if __name__ == "__main__":
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

    sys.path.append('/etc/canvas/website')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
