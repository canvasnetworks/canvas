var site = new WebPage();

site.onConsoleMessage = function (msg) { console.log(msg); };

var TIMEOUT = 30 * 1000;

var unixtime = function () { return (new Date()).getTime(); };

fail = function () {
    console.log("TIMEOUT");
    phantom.exit(-1);
};

site.onLoadStarted = function () {
    console.log("load started");
};

site.onError = function(msg, trace) {
    console.log(msg);
    trace.forEach(function(item) {
        console.log('  ', item.file, ':', item.line);
    });
};

window.setTimeout(fail, 30 * 1000);

site.open("http://savnac.com/");
var start = unixtime();

var poll = function () {
    var results = site.evaluate(function () {
        if (window.check_ready) {
            return window.check_ready();
        }
    });
    if (!results) {
        if (unixtime() - start > TIMEOUT) {
            console.log("TIMEOUT");
            phantom.exit(-1);
        } else {
            window.setTimeout(poll, 100);
        }
    } else {
        console.log("page ready!")
        phantom.exit(0);
    }
};

poll();
