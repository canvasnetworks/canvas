$(function () {
    // Don't show "loading more" if there are only a few responses
    var initial_results = $('#content_well .feed_item');
    if (initial_results.length < 7) {
        $('#content > footer').hide();
    }
    smooth_scroll.wire({
        selector            : "feed_item",
        top_threshold       : 4000,
        bottom_threshold    : 6000,
    });

    canvas.infinite_scroll({
        buffer_px: 1500,
        cutoff_selector: $('#content > footer'),
        scroll_callback: function (disable_scroll_callback) {
            // Using .data here mutates the float from its redis value since it casts it to a js float.
            // Let's keep it as a string instead.
            var last_ts = $('.feed_item:last').attr('data-timestamp');
            var disable_scroll_callback;
            return canvas.api.feed_items(last_ts).done(function (response) {
                if (!$.trim(response)) {
                    disable_scroll_callback();
                    $('#content > footer').hide();
                    return;
                }

                response = $(response).filter(".feed_item");
                $('.user_feed').append(response);
                canvas.wire_follow_buttons(response);
                canvas.wire_lazy_images(response);
                smooth_scroll.add_items(response);
            });
        }
    });

    canvas.wire_dismissables();
});

