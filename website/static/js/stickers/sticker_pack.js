sticker_pack = {};

sticker_pack.descriptions = {
    smiley: "For things that make you smile.",
    frowny: "For something so awful... and yet.. you kind of like it.",
    monocle: "Reserved for all things classy, intelligent or eloquent.",
    lol: "For things that make you laugh out loud.",
    wow: "For things that amaze or surprise you.",
    question: "For something you'd like to know more about.",
    num1: "For things you like the most.",
    cookie: "For things that deserve a cookie.",
    heart: 'For things that make you say "awwww".',
};

sticker_pack.wire = function () {
    stickers.pack_selector = '#sticker_pack';
    sticker_pack.wire_scrolling();

    $('#sticker_pack .sticker_container').each(function () {
        var sticker = $(this);
        if ($('#page.thread').length) {
            // Use the old sticker stuff for threads for now.
            stickers.wire_sticker(sticker);
        } else {
            sticker_pack.wire_sticker(sticker);
        }
        var description = sticker_pack.descriptions[sticker.data('name')];
        if (description) {
            sticker.tooltip({content: description, delay_on: 500, escape_html: false});
        }
        stickers.check_for_animation(sticker.data("type_id"), sticker.attr("class").split(" ")[1]);
    });

    $('#sticker_pack header button, #sticker_pack footer button').click(function () {
        if (current.logged_in) {
            new canvas.StickerShopDialog();
        } else {
            canvas.encourage_signup('sticker_shop');
        }
    });

    sticker_pack.minimized_state = $.cookie('sticker_pack_minimized');
    if (sticker_pack.minimized_state == "false") {
        sticker_pack.minimized_state = false;
    }
    if (sticker_pack.minimized_state) {
        $('#sticker_pack').addClass("minimized");
    }

    if (current.seasonal_event) {
        setInterval(stickers.update_seasonal_timer, 1000);
        stickers.update_seasonal_timer();
    }
};

sticker_pack.wire_sticker = function(sticker) {
    sticker.mobileDrag({
        targetClass: "stickerable",
        draggableClass: stickers.draggable_class,
        draggingClass: stickers.dragging_class,
        drag: function () {
            $("body").addClass(stickers.body_dragging_class);
            realtime.pause_updates();
            stickers.incr_remaining(sticker, -1);
            var placeholder = sticker_pack.current_placeholder = sticker.clone();
            placeholder
                .removeClass(stickers.draggable_class + " " + stickers.dragging_class)
                .addClass("empty show_count backing")
                .css({
                    backgroundPosition: "0 " + -(sticker.height() * 2) + "px"
                })
                .insertAfter(sticker);
            sticker.tooltip('clear').addClass("shadow");
        },
        endDrag: sticker_pack.end_drag.partial(sticker),
        drop: function (drop) {
            var element = $(drop);
            var comment_id = element.attr('data-comment_id');
            var type_id = sticker.data('type_id');
            sticker_pack.attempt_drop(sticker, drop, comment_id, type_id);
        }
    });
};

sticker_pack.end_drag = function (sticker) {
    sticker.mobileDrag('makeUndraggable');
    sticker.addClass("absolute");
    var dragStart = sticker.data("mobileDrag")["dragStart"];
    var placeholder = sticker_pack.current_placeholder;
    var return_time = (dragStart.left == sticker.position().left && dragStart.top == sticker.position().top) ? 0 : 200;
    // Subtract one from the count if limited to clarify this will use one up.
    stickers.incr_remaining(sticker, 1);
    sticker.animate({
        left: dragStart.left,
        top: dragStart.top
    }, return_time, "swing", function () {
        placeholder.remove();
        sticker.tooltip('reset').mobileDrag('makeDraggable').removeClass("shadow absolute");
    });
    realtime.unpause_updates();
};

sticker_pack.regenerate_sticker = function (drag) {
    // The effect for the sticker fading back in after successful stick
    var sticker_name = drag.data("name");
    var placeholder = $(".empty." + sticker_name, drag.parent());
    var dragStart = drag.data("mobileDrag").dragStart;
    placeholder.removeClass("empty");
    var fadeback_opacity = (drag.data('limited') && drag.data('remaining') <= 0) ? 0.5 : 1;
    var fadeback_speed = 500;
    drag.removeClass("shadow").addClass("absolute").insertBefore(placeholder).css({
        left: dragStart.left,
        top: dragStart.top,
        opacity: 0
    }).animate({
        opacity: fadeback_opacity
    }, fadeback_speed, null, function(){
        placeholder.remove();
        drag.tooltip('reset').removeClass("absolute");
        drag.mobileDrag('makeDraggable');
        drag.css("opacity", "");
        if(drag.attr('data-is_limited').toLowerCase() == "true" && drag.data('remaining') <= 0) {
            drag.addClass("none_remaining").mobileDrag('makeUndraggable');
        }
    });
};

sticker_pack.show_top_stickers = function (drop) {
    var sticker_flavor = $('.sticker_flavor', drop);
    sticker_flavor.addClass("js_fake_hover");
    setTimeout(function(){
        sticker_flavor.removeClass("js_fake_hover");
    }, 1500);
};

/* THIS IS NOW DEPRECATED UNLESS WE GO BACK TO CHANGING THEME WHEN STICKERED

sticker_pack.make_viewer_sticker_top_sticker = function(drag, drop) {
    // Clones the sticker we dragged and puts it onto the drop item
    var clone = drag.clone();
    var drag_offset = drag.offset();
    var target = $('.sticker_target', drop);
    var target_parent = target.parent();
    var target_offset = target_parent.offset();
    var target_pos = target.position();
    var target_size = target.width();

    // Remove the sticker count if cloning something with a count
    var count = $('.sticker_remaining', clone);
    if (count.length) {
        count.remove();
    }

    clone
        .insertAfter(target)
        .css({
            left    : drag_offset.left - target_offset.left,
            top     : drag_offset.top - target_offset.top,
            width   : 50,
            height  : 50,
        })
        .animate({
            left    : target_pos.left,
            top     : target_pos.top,
            width   : target_size,
            height  : target_size,
        }, 200, "swing", function() {
            $(this)
                .removeClass("absolute")
                .css({
                    left    : "",
                    top     : "",
                })
            ;
        })
    ;
};
*/

sticker_pack.populate_tray_from_sorted_counts = function(drop, sorted_counts, theme_name) {
    var tray = $('.top_stickers', drop);
    tray.html("");
    for (var i = 0; i < sorted_counts.length; i++) {
        if (i === 0) {
            sticker_pack.replace_top_sticker(drop, sorted_counts[i]);
            continue
        }
        sticker_pack.add_sticker_to_tray(sorted_counts[i], tray, theme_name);
    }
};

sticker_pack.add_sticker_to_tray = function (stick, tray, theme_name) {
    var count = stick.count || 0;
    var sticker = canvas.render(
        "sticker_template",
        {
            name    : stick.name,
            count   : count,
            type_id : stick.type_id,
        }
    );
    var sticker_wrapper = $('<span></span>');
    sticker_wrapper.append(sticker);
    tray.append(sticker_wrapper);
    sticker_wrapper.after(" ");
    stickers.check_for_animation(stick.type_id, stick.name);
    return sticker;
};

sticker_pack.replace_top_sticker = function(drop, stick) {
    var top_sticker = $('.sticker_flavor > .sticker_container', drop);
    var top_sticker_count = $('.sticker_flavor > .sticker_container + .sticker_count', drop);
    if (top_sticker.length) {
        top_sticker.remove();
    }
    if (top_sticker_count.length) {
        top_sticker_count.remove();
    }
    sticker_pack.add_top_sticker(drop, stick);
};

sticker_pack.add_top_sticker = function(drop, stick) {
    var count = (stick.count > 1) ? stick.count : 0
    var sticker = canvas.render(
        "sticker_template",
        {
            name    : stick.name,
            count   : count,
            type_id : stick.type_id,
        }
    );
    var flavor = $('.sticker_flavor', drop);
    flavor.prepend(sticker);
};

sticker_pack.roll_in_sticker_count = function(drop, type_id) {
    var target_count = drop.find(".sticker_container." + current.stickers[type_id].name + " + .sticker_count");
    // If there isn't a sticker_count, don't roll in
    if (target_count.length) {
        var count_span = target_count.children("span");
        var count = parseInt(count_span.text(), 10);
        var old_count_span = $('<span>' + (count - 1) + '</span>');
        old_count_span.insertBefore(count_span);
        old_count_span.css({
            position    : "relative",
            top         : 0,
        });
        var height = old_count_span.outerHeight(true);

        // Wait for the overlay to fade in
        setTimeout(function() {
            old_count_span.animate({
                marginTop   : -height,
            }, 500, function() {
                old_count_span.remove();
            });
        }, 800);
    }
};

sticker_pack.update_stickers = function(drag, drop) {
    // We're going to fake adding our sticker to the sorted counts
    // This will give us the same results the API would have given on success.

    var type_id = drag.data("type_id");
    var sorted_counts = $.extend([], drop.data("details").sorted_sticker_counts);
    var old_sticker_theme = (sorted_counts[0]) ? sorted_counts[0].name : "";
    sorted_counts = sticker_pack.fake_sorted_counts_updated(sorted_counts, type_id);
    var new_sticker_theme = sorted_counts[0].name;

    if (old_sticker_theme !== new_sticker_theme) {
        var retheme = $('.sticker_themed, .sticker_flavor > .sticker_container', drop);
        retheme.removeClass(old_sticker_theme).addClass(new_sticker_theme);
    }
    sticker_pack.populate_tray_from_sorted_counts(drop, sorted_counts, new_sticker_theme);
    sticker_pack.roll_in_sticker_count(drop, type_id);
};

sticker_pack.fake_sorted_counts_updated = function(sorted_counts, type_id) {
    // Returns the sorted count as if received from the API, but without the wait

    // Add the sticker to the sorted counts
    var match = false;
    for (var i = 0; i < sorted_counts.length; i++) {
        var count = sorted_counts[i];
        if (count.type_id == type_id) {
            count.count += 1;
            match = true;
        }
    }
    if (!match) {
        sorted_counts.push({
            count   : 1,
            name    : current.stickers[type_id].name,
            type_id : type_id,
        });
    }

    // Re-sort based on sorting from stickers.py
    var get_sort_key = function(count) {
        var sticker = current.stickers[count.type_id];
        var cost = sticker.cost + 1 || 1;
        var score = count.count * cost
        var limited = (sticker.is_limited) ? 1 : 0;
        return [score, limited, sticker.preference];
    };

    sorted_counts.sort(function(a, b) {
        key_a = get_sort_key(a);
        key_b = get_sort_key(b);
        for (var i = 0; i < key_a.length; i++) {
            var diff = key_b[i] - key_a[i];
            if (diff) {
                return diff;
            }
        }
    });

    return sorted_counts;
};

sticker_pack.drag_to_corner = function(drag, drop) {
    // Clone the sticker and show it getting added to the sticker counts
    var clone = drag.clone();
    clone
        .removeClass(stickers.draggable_class + " " + stickers.dragging_class)
        .addClass("absolute")
        .prependTo("body")
        .css({
            left    : drag.offset().left,
            top     : drag.offset().top,
        })
    ;
    var target = $('.sticker_target', drop);
    var target_offset = target.offset();
    var size = target.width();
    clone.animate({
        left    : target_offset.left,
        top     : target_offset.top,
        width   : size/2,
        height  : size/2,
    }, 300, function() {
        clone.remove();
    });
};

sticker_pack.attempt_drop = function (drag, drop, comment_id, type_id) {
    drag.mobileDrag('makeUndraggable').addClass("absolute");

    var comment_url = 'http://' + document.domain + drop.data('details').url;

    var add_to_comment = function (epic_message) {
        var params = {};
        if (epic_message) {
            params = { epic_message: epic_message };
        }
        return canvas.api.add_sticker_to_comment(comment_id, type_id, params).done(function (response) {
            stickers.special_sticker_metrics(type_id);
            sticker_pack.on_drop_success_confirmed(drag, drop, response);
            FB.getLoginStatus(function(response) {
                if (response.authResponse) {
                    var accessToken = response.authResponse.accessToken;
                    canvas.api.share_sticker(comment_url, accessToken)
                }
            });
        }).fail(function (response) {
            this.stop_propagation = true;
            if (response.reason == 403) {
                var type_id = drag.attr("data-type_id");
                canvas.record_metric('sticker_attempt', {type_id: type_id});
                canvas.encourage_signup("sticker", {type_id: type_id});
            } else {
                sticker_pack.on_drop_failure(drag, drop, response);
            }
        });
    };

    var sticker = current.stickers[type_id];
    if (sticker.cost && sticker.cost >= current.EPIC_STICKER_COST_THRESHOLD) {
        canvas.api.can_sticker_comment(comment_id, type_id).done(function (response) {
            var dialog = new canvas.EpicStickerDialog(function () {
                var message = dialog.get_message();
                add_to_comment(message);
            }, function () {
                add_to_comment();
            });
        }).fail(function (response) {
            add_to_comment();
        });
    } else {
        add_to_comment();
    }

    // Assume the sticker went through for now
    sticker_pack.on_drop_success(drag, drop);
};

sticker_pack.on_drop_success_confirmed = function() {
    realtime.unpause_updates();
};

sticker_pack.on_drop_success = function(drag, drop) {
    drop.removeClass("stickerable").addClass("stickered stickered_by_viewer");
    drop.trigger("sticker_resize");

    // Effects
    stickers.effects.you_voted(drag);
    stickers.effects.flash_outline(drop, 60);
    sticker_pack.show_top_stickers(drop);
    sticker_pack.drag_to_corner(drag, drop);
    sticker_pack.update_stickers(drag, drop);
    sticker_pack.regenerate_sticker(drag);
};

sticker_pack.on_drop_failure = function (drag, drop, response) {
    // Give text feedback using the drop target border element.
    if (response.reason != 403) {
        var text;
        if (response.reason == "Already stickered.") {
            text = "You've already stickered this post.<br/>Make better decisions next time!";
        } else if (response.reason == "No self stickering.") {
            text = "Nice try. You're not allowed to vote on your own posts.";
        } else if (response.reason == "Moderated post.") {
            text = "This post has been moderated and further stickering of it is disabled.";
        } else {
            text = "Error: " + response.reason;
        }
        sticker_pack.overlay_message(drop, text, 3000, 50);
    }
    realtime.unpause_updates();
};

sticker_pack.overlay_message = function (target, message, hide_delay, height_diff) {
    var message_node = $('.sticker_message_overlay', target);
    message_node.html("<p>" + message + "</p>").css("display", "block");
    var message_p = $('p', message_node);
    height_diff = (height_diff) || 0;
    height_diff = Math.max(0, Math.min(message_node.height() - message_p.outerHeight(true) - 5, height_diff));
    message_node.css({
        paddingTop  : height_diff,
    }).animate({
        opacity : 1,
    }, 200, function() {
        if (hide_delay) {
            var self = $(this);
            self.delay(hide_delay).animate({opacity:0}, 150, "swing", function () {
                self.html("").css("display", "none");
            });
        }
    });
};

sticker_pack.toggle = function() {
    $('#sticker_pack').toggleClass("minimized");
    var state = (sticker_pack.minimized_state) ? null : true;
    $.cookie('sticker_pack_minimized', null); /* Fix until cookies in wrong path are expired */
    $.cookie('sticker_pack_minimized', state, { path: '/' });
    sticker_pack.minimized_state = !sticker_pack.minimized_state;
};

sticker_pack.increase_sticker_count_flourish = function(type_id) {
    // This will increase the count with a flourish.
    // Use for gaining new stickers, such as daily #1s.
    var name = current.stickers[type_id].name;
    var sticker = $('#sticker_pack .' + name);
    if (!sticker.length) {
        return false;
    }
    var offset = sticker.offset();
    canvas_effects.sticker_grow_then_fade(offset.left, offset.top, type_id);
    canvas_effects.give_bonus(1, offset.left + 25, offset.top + 25);
};

sticker_pack.wire_scrolling = function() {
    var sticker_pack_node = $('#sticker_pack .fixed_wrapper');
    var pack_height = sticker_pack_node.height();
    var content_height = $('#content').height();
    var threshold = $('#header').height() + 20;
    var pack_top = sticker_pack_node.offset().top;
    var pack_bottom = pack_top + content_height;
    var is_fixed = true;

    $('#content').resize(function() {
        content_height = $('#content').height();
        pack_bottom = pack_top + content_height
    });

    $(window).bind("scroll", function() {
        // Make sure we only do this if the sticker pack is expanded out
        if (sticker_pack_node.css("bottom") !== "auto") {
            return false;
        }

        var window_top = $(window).scrollTop() + threshold;
        var is_above = window_top < pack_top;
        var is_below = window_top > pack_bottom - pack_height;

        if ((is_above || is_below) && is_fixed) {
            var top_pos = (is_above) ? "auto" : (content_height - pack_height);
            is_fixed = !is_fixed;
            sticker_pack_node.css({
                position    : "relative",
                top         : top_pos,
            });
        } else if (!is_above && !is_below && !is_fixed) {
            is_fixed = !is_fixed;
            sticker_pack_node.css({
                position    : "fixed",
                top         : threshold,
            });
        }
    });
};
