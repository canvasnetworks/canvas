module("test_params");

var check_params = function(params) {
    equals(params['foo'], 'bar');
    equals(params['baz'], 'qux');
};

test("get params from query string", function() {
    expect(4);
    check_params($.parseParams("foo=bar&baz=qux"));
    check_params($.parseParams("?foo=bar&baz=qux"));
});

test("get params from URL", function() {
    expect(2);
    check_params($.parseParams("http://example.example/lol/what/?foo=bar&baz=qux"));
});

