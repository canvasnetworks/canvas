from apps.features.feature_flags import feature_funcs


class Features(object):
    def __init__(self):
        self._features = {}

    def _add(self, func, request):
        self._features[func.__name__] = lambda: func(request)

    def __getattr__(self, name):
        return self._features[name]()


def features_context(request):
    features = Features()

    context = {
        'features': features,
    }

    for func in feature_funcs:
        features._add(func, request)

    return context

