from django.http import HttpResponse


class HttpResponseUnauthorized(HttpResponse):
    status_code = 401

    def __init__(self, www_authenticate):
        HttpResponse.__init__(self)
        self['WWW-Authenticate'] = www_authenticate


class HttpUnauthorizedException(Exception):
    def __init__(self, *args, **kwargs):
        self.response = HttpResponseUnauthorized(*args, **kwargs)
        super(HttpUnauthorizedException, self).__init__(unicode(self.response))


