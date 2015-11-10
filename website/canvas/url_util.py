import urlparse

from django.conf.urls.defaults import url

from canvas.exceptions import ServiceError

re_slug = lambda name: "(?P<%s>[a-zA-Z0-9_.,-]+)" % name
re_group_slug = lambda name: "(?P<%s>[-a-zA-Z0-9_]+)" % name
re_int = lambda name: "(?P<%s>\d+)" % name

re_year = re_int('year')
re_month = re_year + "/" + re_int("month")
re_day = re_month + "/" + re_int('day')

def url_decorator(urls):
    def decorator(url_regexp, *args, **kwargs):
        def wrapper(fun):
            urls.append(url(url_regexp, fun, *args, **kwargs))
            return fun
        return wrapper
    return decorator
    
def dynamic_urls():
    """
    Usage Example: 
    urls, api = dynamic_urls()
    """
    urls = []
    return urls, url_decorator(urls)

def maybe(regexp):
    return '(%s|)' % regexp

def verify_first_party_url(url):
    """
    Also allows iTunes store URLs.
    """
    if not url or not url.startswith('/'):
        parsed_url = urlparse.urlparse(url)

        try:
            protocol = parsed_url[0]
            domain = parsed_url[1]
        except IndexError:
            raise ServiceError("Invalid share url.")

        if protocol not in ['http', 'https'] or domain not in  ['itunes.apple.com', 'example.com']:
            # Only 1st party redirects, to avoid security holes that 3rd party redirects imply
            raise ServiceError("Invalid share url.")

