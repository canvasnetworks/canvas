import threading

import solr

from django.conf import settings

class SolrConnection(threading.local):
    _connection = None
    
    def __init__(self, core):
        threading.local.__init__(core)
        self.core = core
    
    @property
    def connection(self):
        if self._connection:
            return self._connection
        else:
            return solr.Solr(settings.SOLR_HOST + '/' + self.core)

valid_core_names = ['comment', 'group']

local = {}
def get_local(core):
    assert core in valid_core_names
    if not core in local:
        local[core] = SolrConnection(core)
    return local[core]

def escape(input):
    escapes = '\\+-&|!(){}[]^~*?:"; '
    return "".join(
        (char if char not in escapes else '\\' + char)
        for char
        in input
    )

def query(core, *args, **kwargs):
    return get_local(core).connection.select(*args, **kwargs)
    
def add(core, *args, **kwargs):
    return get_local(core).connection.add(*args, **kwargs)
    
def update(core, doc, *args, **kwargs):
    get_local(core).connection.delete(doc['id'])
    return add(core, doc)
