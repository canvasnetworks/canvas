module("test_common");

test("string pluralize works as expected", function() {
    expect(5);
    equals("1 cat", "cat".pluralize(1));
    equals("2 cats", "cat".pluralize(2));
    equals("0 cats", "cat".pluralize(0));
    equals("1 reply", "reply".pluralize(1, "replies"));
    equals("2 replies", "reply".pluralize(2, "replies"));
});

test("relative date works as expected", function() {
    expect(4);
    var time = canvas.unixtime();
    equals("1 hour ago", canvas.formatDateRelative(time - 60*60));
    equals("1 day ago", canvas.formatDateRelative(time - 60*60*24));
    equals("1 week ago", canvas.formatDateRelative(time - 60*60*24*7));
    equals("1 year ago", canvas.formatDateRelative(time - 60*60*24*365));
});

test("class inheritance works", function() {
    expect(3);

    var A = Object.createSubclass();
    A.prototype.foo = 'a';
    A.prototype.init = function (val) {
        equals(this.foo, val);
    };

    var B = A.createSubclass();
    B.prototype.foo = 'b';
    B.prototype.init = function (val) {
        equals(this.foo, val);
        B.__super__.init.apply(this, arguments);
    };

    var a = new A('a');
    var b = new B('b');
});

