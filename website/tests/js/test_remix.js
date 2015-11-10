module("test_remix");

/*

Tests are for old remixer. Leaving them here as a reminder that we need test coverage for new remixer.

function fake_postwdiget() {
    var noop = function () {};
    return {
        hideRemix: noop,
        scrollToRemix: noop,
        showRemix: noop,
        attachRemix: noop,
    }
}

// Can just call jQuery.Event directly once we upgrade to 1.6
function make_event(name, properties) {
    var event = jQuery.Event(name);
    $.each(properties, function (k, v) {
        event[k] = v;
    });
    return event;
}

function show_visual_test(expected_canvas, actual_canvas, delta) {
    var test = QUnit.config.current;
    // Delay is a hack to make sure it shows up under the real QUnit output.
    setTimeout(function () {
        var template = $('<div class="visual_output">Expected: <img class="expected"> Actual: <img class="actual"> Delta: ' + delta + '</div>');
        $('span.delta', template).text(delta);
        $('img.expected', template).attr('src', expected_canvas.getDataURL());
        $('img.actual', template).attr('src', actual_canvas.getDataURL());
        template.appendTo($('#' + test.id));
    }, 100);
}

function preload(path, fun) {
    canvas.preload_image(path + "?cache_breaker=" + canvas.unixtime(), fun);
}

function canvas_from_url(url, fun) {
    preload(url, function (img) {
        var temp_canvas = $("<canvas></canvas>");
        temp_canvas.attr({'width': img.width, 'height': img.height});
        temp_canvas.ctx().drawImage(img, 0,0, img.width, img.height);
        fun(temp_canvas);
    });
}

function image_from_canvas(canvas) {
    var img = $("<img/>");
    img.attr('src', canvas.getDataURL());
    return img;
}

function canvas_is_known(url, actual_canvas, fun, threshold) {
    if (threshold === undefined) {
        threshold = 10000;
    }
    var width = actual_canvas.attr('width');
    var height = actual_canvas.attr('height');

    canvas_from_url(url, function (expected_canvas) {
        var actual_data = actual_canvas.ctx().getImageData(0,0, width, height).data;
        var expected_data = expected_canvas.ctx().getImageData(0,0, width, height).data;
        var delta = 0;
        for (var pixel = 0; pixel < width*height*3; ++pixel) {
            var actual = actual_data[pixel];
            var expected = expected_data[pixel];
            delta += Math.pow(expected - actual, 2);
        }

        show_visual_test(expected_canvas, actual_canvas, delta);
        ok(delta <= threshold);
        fun();
    });
}

function create_remix() {
    var base = $(
        '<div class="remix">' +
            '<div class="canvas_container">' +
                '<canvas class="output"></canvas>' +
            '</div>' +
            '<div class="layers">' +
                '<canvas class="foreground"></canvas>' +
                '<canvas class="background"></canvas>' +
            '</div>' +
        '</div>'
    );

    var ui = remix.ui = new remix.RemixWidget(base, fake_postwdiget())
    ui.wire();

    ui.loadBlank(100, 100);

    return base;
}

function fake_mouse_event(base, event_name, x,y, which) {
    var container = $('.canvas_container', base);
    var pos = container.position();
    var event_data = {
        which: (which === undefined) ? 1 : which,
        pageX: pos.left + x,
        pageY: pos.top + y,
        target: container.get(0),
    }
    container.trigger(make_event(event_name, event_data));
}

function fake_mouse_drag(base, start_x, start_y, end_x, end_y) {
    fake_mouse_event(base, "mousedown", start_x, start_y);
    fake_mouse_event(base, "mousemove", end_x, end_y);
    fake_mouse_event(base, "mouseup", end_x, end_y);
}

if (navigator.userAgent.indexOf("PhantomJS") == -1) {
    // These currently fail on PhantomJS due to QTWebKit bugs
    // They also fail subtly on Safari and Firefox, but those are probably real failures 
    // (Remix is not very "stable" across browsers at the moment)

    asyncTest("draw a line", function() {
        expect(1);
        var base = create_remix();

        remix.ui.pick_tool(remix.Airbrush.Tool);

        fake_mouse_drag(base, 10,10, 90,90);

        var output_canvas = $('canvas.output', base);
        canvas_is_known("/static/tests/airbrush_expected.png", output_canvas, function () { QUnit.start(); });
    });

    asyncTest("erase a line", function() {
        expect(1);
        var base = create_remix();

        preload("/static/tests/solid_orange.png", function (image) {
            $('canvas.foreground', base).ctx().drawImage(image, 0,0, image.width, image.height);
            remix.render(true);

            remix.ui.pick_tool(remix.Eraser.Tool);

            fake_mouse_drag(base, 10,10, 90,90);

            var output_canvas = $('canvas.output', base);
            canvas_is_known("/static/tests/eraser_expected.png", output_canvas, function () { QUnit.start(); });
        });
    });

    asyncTest("paintbucket lower right", function () {
       expect(1);
       var base = create_remix();

       preload("/static/tests/solid_orange.png", function (bg_img) {
           preload("/static/tests/blue_squiggle.png", function (fg_img) {
               $('canvas.background', base).ctx().drawImage(bg_img, 0,0, bg_img.width, bg_img.height);
               $('canvas.foreground', base).ctx().drawImage(fg_img, 0,0, fg_img.width, fg_img.height);
               remix.render(true);

               remix.ui.pick_tool(remix.Fill.Tool);

               fake_mouse_drag(base, 90,90, 90,90);

               var output_canvas = $('canvas.output', base);
               canvas_is_known("/static/tests/paintbucket_expected.png", output_canvas, function () { QUnit.start(); });
           });
       });
    });
}

asyncTest("draw a rectangle", function() {
    expect(1);
    var base = create_remix();

    remix.ui.pick_tool(remix.Rectangle);

    fake_mouse_drag(base, 10,25, 90,75);

    var output_canvas = $('canvas.output', base);
    canvas_is_known("/static/tests/rectangle_expected.png", output_canvas, function () { QUnit.start(); });
});

*/
