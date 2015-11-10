activity_stream = {};

activity_stream._stale = true;

activity_stream.load_contents = function () {
    var def = $.Deferred();
    var ul = activity_stream.container.find('ul');

    function _show () {
        setTimeout(function () {
            ul.scrollTop(0);
        }, 10);
        def.resolve();
    }

    if (activity_stream._stale) {
        ul.html('<li class="loading">Loading activity stream… <img src="/static/img/loading.gif"></li>');

        canvas.api.activity_stream().done(function (activities) {
            activities = $(activities);
            ul.html(activities);
            _show();
            canvas.wire_follow_buttons(activities);
            activity_stream._infinite_scroll.enable_scroll_callback();

            activity_stream._stale = false;
        });
    } else {
        _show();
    }
    return def.promise();
};

activity_stream.dismiss = function () {
    activity_stream.container.find('.activity_item').removeClass('unread');
};

activity_stream.realtime_update = function (messages) {
    $.each(messages, function (_, activity) {
        if (activity === 'activity_stream_viewed') {
            header.mark_all_read();
            return;
        }

        activity_stream._stale = true;

        activity_html = $(activity.html);
        if (activity.type !== 'daily_free_stickers') {
            header.show_new_activity(activity_html);
        }
        if (!activity.read) {
            header.increase_unread_count();
        }
        canvas.wire_follow_buttons(activity_html);
    });
};

activity_stream.wire = function () {
    activity_stream.container = header.nodes.activity;
    canvas.prevent_scroll_propagation($('.ul_wrapper > ul', header.nodes.notification_dropdown));

    realtime.subscribe(current.activity_stream_channel, activity_stream.realtime_update);

    if (current.daily_free_stickers_activity) {
        header.show_new_activity(current.daily_free_stickers_activity);
    }

    activity_stream._infinite_scroll = canvas.infinite_scroll({
        buffer_px: 300,
        cutoff_selector: activity_stream.container.find('.infinite_scroll_cutoff'),
        scroll_window: activity_stream.container.find('ul'),
        scroll_callback: function (disable_scroll_callback) {
            // Using .data here mutates the float from its redis value since it casts it to a js float.
            // Let's keep it as a string instead.
            var last_ts = header.nodes.activity.find('.activity_item:last').attr('data-timestamp');
            var disable_scroll_callback;
            return canvas.api.activity_stream({earliest_timestamp_cutoff: last_ts}).done(function (activities) {
                if (!$.trim(activities)) {
                    disable_scroll_callback();
                    return;
                }

                activities = $(activities);
                activity_stream.container.find('ul').append(activities);
                canvas.wire_follow_buttons(activities);
            });
        }
    });
};

