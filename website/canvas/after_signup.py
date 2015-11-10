import urllib

from canvas import util


def make_cookie_key(key):
    return 'after_signup_' + str(key)

def _get(request, key):
    key = make_cookie_key(key)
    val = request.COOKIES.get(key)
    if val is not None:
        val = util.loads(urllib.unquote(val))
    return (key, val,)

def get_posted_comment(request):
    '''
    Gets a comment waiting to be posted, if one exists.

    Returns a pair containing the cookie key used to retrieve it and its deserialized JSON.
    '''
    #TODO use dcramer's django-cookies so that we don't rely on having the response object to mutate cookies.
    # That would make this API much cleaner and isolated.
    return _get(request, 'post_comment')

