window.header = {};

header.wire = function () {
    // First find nodes we'll need
    header.nodes = {};
    header.nodes.progress_bar = $('#header .progress_bar');
    header.nodes.progress_fill = $('.progress_fill', header.nodes.progress_bar);
    header.nodes.progress_percentage = $('span', header.nodes.progress_fill);
    header.nodes.activity = $('#header .activity');
    header.nodes.notification_dropdown = $('#header .activity .dropdown');
    header.nodes.avatar = $('#header .avatar');
    header.nodes.user_dropdown = $('.dropdown', header.nodes.avatar);
    header.nodes.notification_count = $('#header .notification_count span');

    // Check if we need to level up
    header.check_for_level_up();

    header.nodes.progress_bar.click(function () {
        if (!header.activity_stream_visible()) {
            header.show_activity();
        }
    });

    // Hacking around Chrome CSS bug
    $('body').delegate('.hover_buffer', 'click', function() {
        var self = $(this);
        self.parents('.dropdown').removeAttr('style');
        self.css('display', 'none');
        setTimeout(function() {
            self.removeAttr('style');
        }, 10);
    });
    // We have to do with JS instead of :active because every browser but Chrome does it weird
    header.nodes.avatar.click(function () {
        fake_active_css_event(header.nodes.user_dropdown);
    });
    header.nodes.progress_bar.click(function () {
        if (!header.activity_stream_visible()) {
            header.nodes.notification_dropdown.css('display', 'block');
            setTimeout(function() {
                $('body').bind("click.dropdown", function (e) {
                    if (e.button !== 0 || e.metaKey) {
                        return;
                    }

                    if ($.contains(activity_stream.container.find('ul')[0], e.target)) {
                        return;
                    }

                    $('body').unbind("click.dropdown");
                    header.nodes.notification_dropdown.css("display", "none");
                    activity_stream.dismiss();
                });
            }, 1);
        }
    });

    var fake_active_css_event = function (node) {
        node.css('display', 'block');
        $(window).one('mousemove.temp', function () {
            node.removeAttr('style');
        });
    };

    if (current.logged_in) {
        activity_stream.wire();

        // Preload.
        activity_stream.load_contents();
    }
};

header.activity_stream_visible = function () {
    return header.nodes.notification_dropdown.css('display') !== 'none';
};

header.show_activity = function () {
    // Here we can assume they're reading the notifications
    header.mark_all_read();

    activity_stream.load_contents().done(function () {
        canvas.api.mark_all_activities_read();
    });
};

header.mark_all_read = function () {
    header.nodes.notification_count.text("0").parent().hide();
};

header.increase_unread_count = function (delta) {
    if (typeof delta === 'undefined') {
        var delta = 1;
    }
    var count = header.unread_count();
    count += delta;
    if (count > 0) {
        header.nodes.notification_count.text(count).parent().show();
    } else {
        header.nodes.notification_count.text('0').parent().hide();
    }
};

header.unread_count = function () {
    var count = header.nodes.notification_count.text();
    if (count) {
        return parseInt(count, 10);
    }
    return 0;
};

header.show_new_activity = function (activity_html) {
    var activity = $(activity_html);
    var is_epic = activity.hasClass("epic_sticker");
    var container = $('<div class="slide_in_container"></div>');
    var already_clicked = false;
    container.append(activity);
    header.nodes.activity.append(container);
    header.nodes.progress_bar.addClass("js_fake_hover");
    var height = activity.outerHeight();
    if (is_epic) {
        header.nodes.progress_bar.addClass("highlight");
        setTimeout(function() {
            header.nodes.progress_bar.removeClass("highlight");
        }, 2000);
    }
    container.animate({"height": height}, 300, function () {
        canvas_effects.sheen({
            target          : $('a', activity),
            delay           : 100,
            speed           : 1000,
            repeat_delay    : -1,
        });
        container.delay(2500).animate({"height": 0}, 200, function () {
            container.remove();
            if ($('.slide_in_container', header.nodes.activity).length == 0) {
                header.nodes.progress_bar.removeClass("js_fake_hover");
            }
        });
    }).click(function () {
        if (!already_clicked) {
            header.increase_unread_count(-1);
            already_clicked = true;

            canvas.api.mark_activity_read(activity.data('id'));
        }
    });
};

header.sticker_receieved = function () {
    header.update_progress_bar();
    header.render_current_sticker();
};

header.update_progress_bar = function () {
    var total = current.sticker.level_total;
    var progress = current.sticker.level_progress;

    if (progress >= total) {
        header.offer_level_up();
    }

    var percent = Math.min(100, Math.round(progress/total * 100));
    header.nodes.progress_fill.css("width", percent + "%");
    header.nodes.progress_percentage.text(percent);

    var new_tooltip = "Receive " + (total - progress) + " more points to get more #1 stickers!";
    header.nodes.progress_bar.data("tooltip", new_tooltip);
    header.nodes.progress_bar.attr("title", new_tooltip);
};

header.render_current_sticker = function () {
    if (!current.sticker.timestamp) {
        return; // Don't show the header at all if you haven't received a sticker yet.
    }
    // Render the sticker and replace the current sticker in header
    stickers.check_for_animation(current.sticker.type_id);
    var target_node = $('#header .last_sticker > a:first-of-type');
    target_node.html(
        tmpl.sticker(current.sticker.type_id) +
        tmpl.relative_timestamp(current.sticker.timestamp)
    ).attr("href", current.sticker.url);
};

header.update_flagged_count = function () {
    $('#header li.flagged span.count').html(current.flagged ? current.flagged : "");
};

header.check_for_level_up = function () {
    if (!current.sticker) {
        return false;
    }
    if (current.sticker.level_progress >= current.sticker.level_total) {
        header.offer_level_up();
    }
};

header.offer_level_up = function () {
    var level_up_bar = header.nodes.progress_bar.clone();
    var filler = $('.progress_fill', level_up_bar);

    $('> span', level_up_bar).remove();
    level_up_bar.addClass("level_up_ready").removeAttr("title").removeClass("tooltipped");
    filler.css({
        width: "100%",
    });
    $('span', filler).text('\xA0 Level up!');

    level_up_bar.insertBefore(header.nodes.progress_bar);
    //header.nodes.progress_bar.hide();

    level_up_bar.one('click', function () {
        header.acknowledge_level_up(level_up_bar);
        return false;
    });
};

header.acknowledge_level_up = function (bar) {
    canvas.apiPOST(
        '/user/level_up',
        {},
        function (result) {
            current.sticker = $.extend({}, current.sticker, result.stats);
            header.update_progress_bar();
            
            var filler = $('.progress_fill', bar);
            var count = result.reward_stickers; // TODO: Combine all level ups and get total we're awarded.
            var total_time = 2000;
            var time_per_award = total_time/(count + 1);

            filler.css("width", "0%");

            // Show stickers pop out of the bar,
            // and go into the sticker pack.
            var offset = bar.offset();
            var x = offset.left;
            var y = offset.top - bar.height()/2;
            for (var i = 0; i < count; i++) {
                setTimeout(function () {

                    // Add a sticker
                    canvas_effects.spit_out_sticker(x, y, -100, 7, "medium");
                    sticker_pack.increase_sticker_count_flourish(7);
                    stickers.incr_remaining(7, 1);
                    
                }, i * time_per_award);
            }
            setTimeout(function() {
                bar.remove();
            }, total_time);
        }
    );
};

