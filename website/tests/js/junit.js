JUnitTestResult = function(suitename) {
    this.suitename = this.sanitize(suitename);
    this.assertions = 0;
    this.failures = 0;
    this.tests = 0;
    this.body = "";
};

JUnitTestResult.prototype.sanitize = function(value) {
    return value.replace(/ /g, "_");
}

JUnitTestResult.prototype.addTest = function(name, passed, message) {
    name = this.sanitize(name);
    var assertions = 1;
    var node = '    <testcase name="' + name + '" class="' + this.suitename + '" assertions="' + assertions + '"';
    if (passed) {
        node += '/>';
    } else {
        node += '>\n    <failure>derp</failure>\n    </testcase>';
        this.failures += 1;
    }
    this.tests += 1;
    this.assertions += assertions;
    this.body += node + '\n';
};

JUnitTestResult.prototype.render = function() {
    var header = '<?xml version="1.0" encoding="UTF-8"?>\n<testsuites>\n';
    header += '  <testsuite name="' + this.suitename +'" tests="' + this.tests + '" assertions="' + this.assertions + '" failures="' + this.failures + '" errors="0">\n';
    var footer = '  </testsuite>\n</testsuites>\n';
    var xml = header + this.body + footer;
    return xml;
};

