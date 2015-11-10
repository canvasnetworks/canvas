import datetime
import inspect
import os
import string

from django.core.urlresolvers import reverse, NoReverseMatch

import apps.activity.api
import apps.analytics.api
import apps.comments.api
import apps.comment_hiding.api
import apps.feed.api
import apps.following.api
import apps.invite_remixer.api
import apps.logged_out_homepage.api
import apps.monster.api
import apps.share_tracking.views
import apps.sticky_threads.api
import apps.suggest.api
import apps.tags.api
import apps.threads.api
from canvas import api
from canvas.api_decorators import api_functions

CANVAS_PATH = "/var/canvas"

#TODO use django string templates instead - would be much cleaner without too much more work.

AJAX_FUNCTION_TEMPLATE = \
"""
    /**
$doc
     */
    $function_name: function($js_args) {
        var params = {};
        var args = arguments;
        $$.each([$required_args], function(i, v) {
            params[v] = args[i];
        });
        $optional_params_handler
        this.data = params;
        return this._call('$url', $async, this.data);
    },"""

CANVAS_API_FILE_TEMPLATE = \
"""
/*
 * Canvas Ajax API
 *
 * Returns a $$.Deferred promise instance.
 *
 * Any doneCallbacks will receive two params: `data`, `jq_xhr` (from $$.ajax's success callback).
 *
 * failCallbacks receive two params: `data`, `jq_xhr`. `data` will be a JSON hash, even if it was an HTTP error,
 * in which case the `reason` parameter will be the HTTP error message (`textStatus` from $$.ajax's `error` callback.
 * If it's a service-level error (our Canvas API returns success: false), then it will be the JSON given in that
 * response, which includes a `reason` item.
 *
 * See:
 *     http://api.jquery.com/category/deferred-object/
 *     http://api.jquery.com/jQuery.ajax/
 */
canvas.api = {
    _fail: function (_, resp) {
        if (this.stop_propagation) {
            return;
        }
        canvas.on_api_fail(this.data, resp);
    },

    $methods

    _response_type: function (jq_xhr) {
        // Can detect text/html or application/json. If unknown, returns null. If known, returns the type name.
        var content_type = jq_xhr.getResponseHeader('Content-Type');
        var match = null;
        $$(['text/html', 'application/json']).each(function (i, candidate) {
            if (content_type.indexOf(candidate) !== -1) {
                match = candidate;
            }
        });
        return match;
    },

    _call: function (url, async, params) {
        var def = new $$.Deferred();
        var that = this;
        $$.ajax({
            url: url,
            type: 'POST',
            async: async,
            contentType: 'application/json',
            data: JSON.stringify(params),
            success: function(data, text_status, jq_xhr) {
                var content_type = that._response_type(jq_xhr);
                if (content_type === 'text/html') {
                    def.resolve(data, jq_xhr);
                } else {
                    if (data.success) {
                        def.resolve(data, jq_xhr);
                    } else {
                        def.reject(data, jq_xhr);
                        def.fail(that._fail);
                    }
                }
            },
            error: function(jq_xhr) {
                def.reject({'success': false, 'reason': jq_xhr.status}, jq_xhr);
                def.fail(that._fail);
            }
        });
        return def.promise();
    }
};
"""

class APICall(object):
    """ A wrapper around an inspected API call. """
    def __init__(self, function):
        self.name, self.function_object = function
        self.url = reverse(self.function_object.url_name)
        self.doc = inspect.getdoc(self.function_object) or ""
        self.args = self.function_object.arg_spec.args[1:]
        self.kwargs = self.function_object.arg_spec.kwargs
        self.async = self.function_object.async

def get_api_calls(api_functions=api_functions, ignore_unfound=False):
    """ Returns a list of APICall. """
    functions = [(n,f) for (n,f) in api_functions if getattr(f, "is_api", False)]
    functions = sorted(functions, key=lambda (n,f): n)
    ret = []
    for function in functions:
        try:
            ret.append(APICall(function))
        except NoReverseMatch:
            if not ignore_unfound:
                raise
    return ret

def get_api_js_filename():
    return os.path.join(CANVAS_PATH, "website", "static", "js", "canvas_api.js")

def generate_api_javascript():
    # Grab the API file...
    function_bodies = []
    # Get a tuple of functions. Each tuple is: (function_name, function_object).
    #
    # The "is_api" attribute is added by one of the api view wrapper methods. We add the "is_api" flag because
    # there is no way to inspect what wrappers a function object has.
    for function in get_api_calls():
        doc = "\n".join([("     * %s" % line) for line in function.doc.split("\n")])

        args, optional_args = [], []
        if function.args:#[1:]: # Skip `request`
            args = function.args

        js_args = args[:]
        if function.kwargs:
            js_args.append('optional_params')
        js_args = u', '.join(js_args)

        def quote_args(args):
            return u', '.join(u'"{0}"'.format(arg) for arg in args)
        js_required_args = quote_args(args)

        d = {
             'js_args': js_args,
             'required_args': js_required_args,

             'function_name': function.name,
             'doc': doc,
             'url': function.url,
             'async': str(function.async).lower(),
        }
        d['optional_params_handler'] = ("""
        if (typeof optional_params !== 'undefined') {
            $.extend(params, optional_params);
        }"""
            if function.kwargs else '')

        function_body = string.Template(AJAX_FUNCTION_TEMPLATE).substitute(d)
        function_bodies.append(function_body)

    canvas_api = "/* DO NOT EDIT THIS FILE BY HAND. It is generated by canvas/js_api.py"
    canvas_api += string.Template(CANVAS_API_FILE_TEMPLATE).substitute({'methods': "\n".join(function_bodies)})
    return canvas_api

