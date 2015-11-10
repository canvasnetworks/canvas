
def patch_email_field():
    """
    Patch EmailField to default to 254 chars instead of 75 
    http://stackoverflow.com/questions/915910/django-auth-user-truncating-email-field
    """
    from django.db.models.fields import EmailField, CharField
    def email_field_init(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 254)
        CharField.__init__(self, *args, **kwargs)
    EmailField.__init__ = email_field_init
    
patch_email_field()

def patch_debug_500_template():
    patch = """
<!--
{% autoescape off %}
{% for frame in frames %}
File "{{ frame.filename }}", line {{ frame.lineno }}, in {{ frame.function }}
{{ frame.context_line }}
{% endfor %}
{% endautoescape %}
-->
    """
    
    from django.views import debug
    tmpl = debug.TECHNICAL_500_TEMPLATE
    token = '<head>'
    splice_point = tmpl.find(token) + len(token)
    debug.TECHNICAL_500_TEMPLATE = tmpl[:splice_point] + patch + tmpl[splice_point:]
    
patch_debug_500_template()

def south_add_UnixTimestampField():
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ['^canvas\.util\.UnixTimestampField'])
south_add_UnixTimestampField()

def non_debug_timing_info():
    from django.core.exceptions import ImproperlyConfigured
    from django.http import HttpRequest
    from canvas import hacks
    import time, sys, logging

    def logging_wrapper(fun):
        def wrapper(*args, **kwargs):
            start = time.time()
            results = fun(*args, **kwargs)
            end = time.time()

            request = hacks.find_request()

            if request:
                if not hasattr(request, "_sql_queries"):
                    request._sql_queries = []

                request._sql_queries.append((end-start) * 1000)

            return results
        return wrapper

    def wrap_cursor(CursorClass):
        CursorClass.execute = logging_wrapper(CursorClass.execute)
        CursorClass.executemany = logging_wrapper(CursorClass.executemany)

    try:
        from django.db.backends.sqlite3.base import SQLiteCursorWrapper
    except ImproperlyConfigured:
        pass
    else:
        wrap_cursor(SQLiteCursorWrapper)

    try:
        from django.db.backends.mysql.base import CursorWrapper
    except ImproperlyConfigured:
        pass
    else:
        wrap_cursor(CursorWrapper)

non_debug_timing_info()

def integrate_faulthandler():
    import faulthandler, signal
    fout = file('/var/canvas/website/run/faulthandler.log', 'a')
    faulthandler.register(signal.SIGUSR2, file=fout)

integrate_faulthandler()
