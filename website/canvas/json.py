import simplejson

loads = simplejson.loads # For symmetry. 
JSONDecodeError = simplejson.JSONDecodeError

def backend_dumps(things, **kwargs):
    def convert_object(obj):
        if hasattr(obj, "to_backend"):
            return obj.to_backend()
        else:
            raise Exception("Unjsonable object of type %r (%r)" % (type(obj), obj))

    return simplejson.dumps(things,
                            default = convert_object,
                            **kwargs)

def dumps(things, **kwargs):
    """
    Dumps `things` into JSON.

    Note that we use the "default" parameter in json.dumps to use the to_dict implementation, if defined, on
    objects to convert them to JSON.

    Defaults to to_client if to_dict doesn't exist, as a fallback.
    """
    def convert_object(obj):
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif hasattr(obj, 'to_client'):
            return obj.to_client()
        raise Exception("Unjsonable object of type %r (%r)" % (type(obj), obj))

    return simplejson.dumps(things,
                            default = convert_object,
                            **kwargs)

def client_dumps(obj, **kwargs):
    """ Dumps `obj.to_client()` (or just `obj` as a fallback) into JSON, for client-side consumption. """
    thing = getattr(obj, 'to_client', lambda: obj)()
    return simplejson.dumps(thing,
                            default = lambda obj: getattr(obj, 'to_client', lambda: obj)(),
                            **kwargs)

