/*
* Subscribe to as many unhandled exceptions as we can, and send them to Sentry.
* See https://github.com/csnover/TraceKit/ for docs.
*
* Depends on jQuery and common.js
*
* Details on the stackInfo objects that TraceKit generates:
*   s.name              - exception name
*   s.message           - exception message
*   s.stack[i].url      - JavaScript or HTML file URL
*   s.stack[i].func     - function name, or empty for anonymous functions (if guessing did not work)
*   s.stack[i].args     - arguments passed to the function, if known
*   s.stack[i].line     - line number, if known
*   s.stack[i].column   - column number, if known
*   s.stack[i].context  - an array of source code lines; the middle element corresponds to the correct line#
*   s.mode              - 'stack', 'stacktrace', 'multiline', 'callers', 'onerror', or 'failed' -- method used to 
*                         collect the stack trace
*
* Supports:
*   - Firefox:  full stack trace with line numbers and unreliable column
*               number on top frame
*   - Opera 10: full stack trace with line and column numbers
*   - Opera 9-: full stack trace with line numbers
*   - Chrome:   full stack trace with line and column numbers
*   - Safari:   line and column number for the topmost stacktrace element
*               only
*   - IE:       no line numbers whatsoever
*/

TraceKit.report.subscribe(function(stackInfo) {
    var data = {
        url: window.location.href,
        stackInfo: stackInfo
    };
    //canvas.apiPOST('/sentry/js_exception', data);
    console.log(stackInfo);

    //alert("Sorry, Canvas has encountered an error. Please refresh the page.\n\nWe've been notified of the problem and will look into it ASAP.");
});

