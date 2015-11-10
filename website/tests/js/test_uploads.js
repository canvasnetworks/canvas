module("test_uploads");

test("uploading from curi triggers uploadend", function() {
    expect(1);
    var handler = {};
    $(handler).bind("uploadend", function() {
        ok(true);
    });
    canvas.upload_url("content://foo", handler);
});
