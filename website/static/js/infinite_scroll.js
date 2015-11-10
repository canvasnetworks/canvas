canvas.infinite_scroll = function (params) {
    // `scroll_callback` must return a Deferred, or false if it should turn off.
    params = $.extend({
        cutoff_selector: null,
        buffer_px: 1000,
        scroll_callback: null,
        scroll_window: window,
    }, params);

    params.cutoff_selector = $(params.cutoff_selector);

    var load_in_progress = false;
    var active = true;

    var win = $(params.scroll_window);
    win.scroll(function (e) {
        if (!active || load_in_progress) {
            return;
        }

        if (win.scrollTop() + win.height() >= params.cutoff_selector.offset().top - params.buffer_px) {
            load_in_progress = true;

            var always = function () {
                load_in_progress = false;
            };
            var disable_scroll_callback = function () {
                active = false;
            };
            params.scroll_callback(disable_scroll_callback).then(always, always);
        }
    });

    return {
        enable_scroll_callback: function () {
            active = true;
        },
    };
};

