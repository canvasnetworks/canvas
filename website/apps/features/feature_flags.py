feature_funcs = set()

def feature(func):
    """ Feature functions take a request as their single argument. """
    feature_funcs.add(func)
    return func

@feature
def requirejs(request):
    return 'requirejs' in request.GET

@feature
def thread_new(request):
    return True

@feature
def lazy_content(request):
    return True
