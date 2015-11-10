var system = require('system');
var host = 'http://savnac.com';
if (system.args.length === 2) {
    host = system.args[1];
}

var page = new WebPage();

page.onConsoleMessage = function (msg) { console.log(msg); };

var TIMEOUT = 30 * 1000;

var unixtime = function () { return (new Date()).getTime(); };

page.open(host + '/js_testing', function (status) {
    var start = unixtime();

    if (status !== 'success') {
        console.log("phantomjs> Could not load /js_testing");
        phantom.exit(1);
    }

    var poll = function () {
        var results = page.evaluate(function () {
            // I evaluate in the context of the page, and do not have access to globals from here
            if (typeof check_for_qunit_results != 'undefined') {
                return check_for_qunit_results();
            }
        });

        if (!results) {
            if (unixtime() - start > TIMEOUT) {
                console.log("TIMEOUT");
                phantom.exit(-1);
            } else {
                window.setTimeout(poll, 10);
            }
        } else {
            var fs = require('fs');
            var xmlfile = fs.open('/var/canvas/website/run/results-qunit.xml', 'w');
            xmlfile.write(results.xml);
            xmlfile.close();
            page.viewportSize = {width: 1024, height: 1024};
            page.pageSize = {width: 1024, height: 1024};
            page.render("./run/js_tests.png");
            phantom.exit(results.testsFailed);
        }
    };

    poll();
});

