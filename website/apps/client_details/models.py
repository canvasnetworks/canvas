class ClientDetailsBase(object):
    """
    ClientDetails requires child classes to define a list TO_CLIENT_WHITELIST

    This list should contain string values or (string, boolean) tuples indicating
    whether or not a field is optionally included or (string, boolean, string) values 
    indicating the name of the attribute to store in the whitelisted fieldname.

    'foo' -> required {'foo': self.foo}
    ('foo', True) -> optional {'foo': self.foo}
    ('foo', False, 'bar') -> required {'foo': self.bar}
    """
    def __init__(self, details):
        self._d = details
        for k,v in details.iteritems():
            # we call this to handle wrapper methods and properties defined in child classes
            if not hasattr(self, k):
                setattr(self, k, v)
    
    def __eq__(self, other):
        return isinstance(other, self.__class__) and hasattr(other, '_d') and self._d == other._d

    def __getitem__(self, key):
        return getattr(self, key)

    def to_client(self):
        # Things to add to the JSON serialization.
        def get_val(val):
            if callable(val):
                return val()
            return val

        d = {}

        for property_name in self.TO_CLIENT_WHITELIST:
            if isinstance(property_name, tuple):
                if len(property_name) == 2:
                    key, optional = property_name
                    alias = key
                elif len(property_name) == 3:
                    alias, optional, key = property_name
            else:
                key = property_name
                optional = False
                alias = key

            try:
                val = getattr(self, key)
                d[alias] = get_val(val)
            except AttributeError as e:
                if optional:
                    pass
                else:
                    raise e

        return d

    def to_backend(self):
        return self._d

    @property
    @classmethod
    def TO_CLIENT_WHITELIST(cls):
        raise NotImplementedError("You must define TO_CLIENT_WHITELIST in order to serialize.")

