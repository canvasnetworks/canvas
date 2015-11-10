from inspect import getargspec

from django.utils.functional import curry
from django import template as django_template


class Library(django_template.Library):
    def context_tag(self, func):
        params, xx, xxx, defaults = getargspec(func)

        class ContextNode(django_template.Node):
            def __init__(self, vars_to_resolve):
                self.vars_to_resolve = map(django_template.Variable, vars_to_resolve)

            def render(self, context):
                resolved_vars = [var.resolve(context) for var in self.vars_to_resolve]
                return func(context, *resolved_vars)

        compile_func = curry(django_template.generic_tag_compiler,
                             params[1:],
                             defaults[1:] if defaults else None,
                             getattr(func, "_decorated_function", func).__name__,
                             ContextNode)

        compile_func.__doc__ = func.__doc__

        self.tag(getattr(func, "_decorated_function", func).__name__, compile_func)
        return func

