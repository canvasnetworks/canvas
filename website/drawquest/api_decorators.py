from canvas.api_decorators import *

def drawquest_inner_api(*args, **kwargs):
    kwargs['force_csrf_exempt'] = True
    return inner_api(*args, **kwargs)

def api_decorator(urls):
    """
    Returns an API decorator for the given URL space.
    """
    url_decorator = url_util.url_decorator(urls)
    return drawquest_inner_api(url_decorator)

