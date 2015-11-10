import sys

from django.http import HttpRequest

def find_request():
    next_frame = sys._getframe()
    while next_frame:
        frame = next_frame
        next_frame = frame.f_back

        request = frame.f_locals.get('request')
        if isinstance(request, HttpRequest):
            return request
