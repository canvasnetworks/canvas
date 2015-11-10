stickers = {};
stickers.effects = {};

stickers.descriptions = {
    // Stickers
    smiley: "For things that make you smile.",
    frowny: "For something so awful... and yet.. you kind of like it.",
    monocle: "Reserved for all things classy, intelligent or eloquent.",
    lol: "For things that make you laugh out loud.",
    wow: "For things that amaze or surprise you.",
    question: "For something you'd like to know more about.",
    num1: "For things you like the most.",
    cookie: "For things that deserve a cookie.",
    heart: 'For things that make you say "awwww".',

    // Sharing
    facebook: "Share to your Facebook wall.",
    twitte: "Share to Twitter.",
    stumbleupon: "Share to StumbleUpon.",
    tumblr: "Share to Tumblr.",
    reddit: "Share to Reddit.",
    email: "Share via Email.",

    // Actions
    flag: "Flag NSFW and hate speech for moderators.",
    downvote_action: "Downvote a post.",
    pin: "Follow this thread in 'Pinned'.",
    offtopic: "Mark as off-topic, hiding the post.",
    seenthis: "For things you've seen before.",
    curated: "Hide from Everything's popular page.",
    remix: "Remix an image to make your own version of it.",
};

stickers.animations = {
    /* FPS, then the frames in order (left to right) */
    "number-oneocle": [24, 1, 1, 1, 1, 1, 1, 2, 2, 2, 3, 3, 4, 5, 6, 7, 8, 8, 9, 9, 9, 10, 10, 10, 10, 10, 10, 9, 9, 9, 8, 8, 7, 6, 5, 4, 3, 3, 2, 2, 2],
    fuckyeah        : [12, 1, 2, 3, 4, 5],
    partyhard       : [12, 1, 2, 3, 4, 5, , 6, 7],
    "super-lol"     : [8, 1, 2, 3, 4, 5, 6],
    "trololol"     : [8, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
};

stickers.animated_types = []; // populated based on what is rendered

stickers.dragging_class = "dragging";
stickers.draggable_class = "drag";
stickers.body_dragging_class = "dragging";

stickers.Animation = function (type_id, name) {
    this.type_id = type_id;
    this.name = name;
    this.animation = stickers.animations[name];
    this.delay = 1000/this.animation.shift();
    this.i = 0;
    var that = this;
    setInterval(function () {
        if (that.i >= that.animation.length) { that.i = 0; }
        $(".sticker_container."+that.name).each(function () {
            if ($(this).is(":visible")) {
                var sticker = $(this);
                var y_pos = "-100%";
                if (sticker.is(".shadow")) {
                    y_pos = 0;
                } else if (sticker.is(".backing")) {
                    y_pos = "100%";
                }
                sticker.css("background-position", -(that.animation[that.i]-1)*$(this).width() + "px " + y_pos);
            }
        });
        that.i++;
    }, this.delay);
};

stickers.check_page_for_animations = function() {
    var animated = ["number-oneocle", "fuckyeah", "partyhard", "super-lol", "trololol"]
    for (var i = 0; i < animated.length; i++) {
        var sticker_name = animated[i];
        var sticker = $('#page .sticker_container .' + sticker_name);
        stickers.check_for_animation(sticker.data("type_id"), sticker_name);
    }
};

stickers.check_for_animation = function(type_id, name) {
    if (name == undefined) {
        name = current.stickers[type_id].name;
    }
    if (stickers.animations[name] && $.inArray(name, stickers.animated_types) == -1) {
        stickers.animated_types.push(name, 10);
        new stickers.Animation(type_id, name);
    }
};

stickers.append_sticker = function(stick, container, template) {
    if (!template) {
        template = "sticker_template";
    }
    var count = stick.count || 0;
    var name = current.stickers[stick.type_id].name;
    var sticker = canvas.render(
        template,
        {
            name: name,
            count: count,
            type_id: stick.type_id
        }
    );
    $(container).append(sticker);
    stickers.check_for_animation(stick.type_id, name);
    return sticker;
};

stickers.get_scores = function (counts) {
    var scores = {
        upvote: 0,
        downvote: 0,
    };
    if (!counts || !counts.length) {
        return scores;
    }
    $.each(counts, function (type_id, count) {
        if (current.stickers[type_id]) {
            if (current.stickers[type_id].value < 0) {
                scores.downvote += count;
            } else {
                scores.upvote += (current.stickers[type_id].cost || 1) * count;
            }
        }
    });
    return scores;
};

stickers.get_sticker_from_id = function(type_id) {
    for (var id in current.stickers) {
        if (id = type_id) {
            return current.stickers[id];
        }
    }
};

stickers.style_sticker_themed = function(themed, sticker_id) {
    // First remove other stylings.
    $.each(current.stickers, function(i, sticker) {
        themed.removeClass(sticker.name);
    });
    // Then add the new styling.
    themed.addClass(current.stickers[sticker_id].name);
};

/*
 * This should be called regardless of if the content has any stickers to:
 *   - empty the stickerable if it should be
 *   - set the stickerable data

 * Logic for picking the winner:
 *  - A sticker's score is its cost in the store
 *  - Free stickers and downvotes have cost 1
 *  - Let a post's upvote score be the total sum of all positive sticker scores, and its downvote score is the count of downvotes
 *  - If the downvote score is two downvotes higher than the upvote score, show the downvote icon
 *    - (If the downvote score is three downvotes higher than the upvote score, show the collapsed downvoted post)
 *  - Otherwise, show the top scoring sticker
 */
stickers.update_stickerable = function (stickerable, comment_id, counts, sorted_counts, top_stick) {
    var themed = $('.sticker_themed', stickerable);
    $(stickerable).attr('data-comment_id', comment_id);

    // First, empty all the sticker containers, as we will repopulate them.
    $('.top_sticker, .sticker_overlay', stickerable).empty();

    // Iterate over stickers by count descending, putting them in the appropriate container.
    var scores = stickers.get_scores(counts);
    // Add stickered class to elements that have a sticker for width adjustment
    sorted_counts = typeof sorted_counts === 'undefined' ? [] : sorted_counts;
    if (sorted_counts.length) {
        stickerable.addClass("stickered");
    }

    if (scores.upvote < 4 && stickerable.hasClass("reply") && !stickerable.hasClass("expanded") && !stickerable.hasClass("op") && !stickerable.hasClass("unthemed_expanded")) {
        stickerable.addClass("unthemed");
    } else if (stickerable.hasClass("expanded")) {
        stickerable.removeClass("unthemed").addClass("unthemed_expanded");
    } else {
        stickerable.removeClass("unthemed").removeClass("unthemed_expanded");
    }

    var sticker_overlay = $('.sticker_overlay', stickerable);
    for (var i = 1; i < sorted_counts.length; ++i) {
        stickers.append_sticker(sorted_counts[i], sticker_overlay);
    }

    if (top_stick) {
        if (top_stick.count === 1) {
            top_stick.count = 0;
        }
        stickers.append_sticker(top_stick, $('.top_sticker', stickerable));
        // Theme the themed element if it exists.
        if (themed.length) {
            // Style based on top sticker
            stickers.style_sticker_themed(themed, top_stick.type_id);

            // If this is the last tile in a column, style footer too.
            for (var i=0; i < stickerable.length; i++) {
                if ( $(stickerable[i]).is(":nth-child(" + $(stickerable[i]).parents(".column").children(".image_tile").length + ")")  ) {
                    $(stickerable[i]).parents(".column").children(".footer").addClass(current.stickers[top_stick.type_id].name);
                }
            }
        }
    }

    // Unbind and bind top_sticker hover
    var top_sticker = $(".top_sticker .sticker_container", stickerable);
    top_sticker.unbind("mouseover").unbind("mouseout").bind("mouseover", function () {
        $(this).parent().siblings(".image_sticker_details").css({ opacity: 0, zIndex: 2 }).removeClass("invisible").stop().animate({ opacity: 1 }, 200, "swing");
    }).bind("mouseout", function () {
        $(this).parent().siblings(".image_sticker_details").stop().animate({ opacity: 0 }, 200, "swing", function () {
            $(this).css({ opacity: 0, zIndex: 0 }).addClass("invisible");
        });
    });
};

stickers.special_sticker_metrics = function(type_id) {
    // Seasonal and shop sticker usage metrics
    if (type_id >= 100 && type_id < 300 && type_id !== 103) {
        canvas.record_metric('seasonal_sticker_used', { 'type_id': type_id });
    } else if (type_id == 103 || (type_id >= 300 && type_id < 500)) {
        canvas.record_metric('shop_sticker_used', { 'type_id': type_id });
    }
};

stickers.add_to_comment = function (drag, drop, comment_id, type_id) {
    drag.mobileDrag('makeUndraggable').addClass("absolute");

    var add_to_comment = function (epic_message) {
        var spinner = $('<div class="sticker_spinner"></div>').prependTo(drag);
        var params = {};
        if (epic_message) {
            params = { epic_message: epic_message };
        }
        return canvas.api.add_sticker_to_comment(comment_id, type_id, params).done(function (response) {
            spinner.remove();
            stickers.special_sticker_metrics(type_id);
            stickers.on_drop_success(drag, drop, comment_id, response);
        }).fail(function (response) {
            this.stop_propagation = true;
            if (response.reason == 403) {
                var type_id = drag.attr("data-type_id");
                canvas.record_metric('sticker_attempt', {type_id: type_id});
                canvas.encourage_signup("sticker", {type_id: type_id});
            }
            spinner.remove();
            stickers.on_drop_failure(drag, drop, comment_id, response);
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
};

stickers.add_pin_to_comment = function (comment_id) {
    // A comment may appear pinned on behalf of another, such as recent replies in active/pinned.
    var stickerable = $('.post_'+comment_id).addClass('pinned').append($('<div class="sticker_container pin"></div>'));
    stickerable.find('.pin').click(function () {
        var pin = $(this);
        var spinner = $('<div class="sticker_spinner"></div>').prependTo(pin);
        return canvas.apiPOST('/comment/unpin', {'comment_id': comment_id},
            function (response) {
                spinner.remove();
                if (response.success) {
                    pin.animate({opacity: 0}, 500).remove();
                } else {
                    canvas.log(response);
                }
            }
        );
    });
    return stickerable;
};

stickers.overlay_message = function (target, message, hide_delay, height_diff) {
    // Insert the html before returning so sticker_actions.js for example can bind to elements in it immediately after this call.
    var overlay = $(".drop_target_border", target);
    overlay.html("<p>" + message + "</p>");
    var overlay_p = $("p", overlay);

    overlay.css("padding-top", 0);
    height_diff = (height_diff) || 0;
    height_diff = Math.max(0, Math.min(overlay.height() - overlay_p.outerHeight(true) - 5, height_diff));

    overlay.css({
        opacity : 0,
        backgroundColor : "#eee",
        zIndex : 3,
        paddingTop : height_diff,
    }).animate({opacity:0.9}, 150, "swing", function () {
        if (hide_delay) {
            $(this).delay(hide_delay).animate({opacity:0}, 150, "swing", function () {
                $(this).html("").css({opacity:1, backgroundColor:"transparent", zIndex:""});
            });
        }
    });
};

stickers.effects.drag_to_corner = function (drag, drop) {
    // Clone sticker and drag to corner while shrinking
    var new_sticker = drag.clone();
    new_sticker.removeClass(stickers.draggable_class + " " + stickers.dragging_class).addClass("absolute").css({zIndex:3}).prependTo("body").css({
        left : drag.offset().left,
        top : drag.offset().top,
    });
    var top_sticker = $(".top_sticker .sticker_container", drop);
    var left_destination = "",
        top_destination = "";
    if (top_sticker.length > 0) {
        left_destination = (top_sticker.offset().left + (top_sticker.width() / 2));
        top_destination = (top_sticker.offset().top + (top_sticker.height() / 2));
    } else {
        left_destination = drop.offset().left + drop.width() - new_sticker.width();
        top_destination = drop.offset().top + drop.parent().height() - new_sticker.height();
    }

    var target_sticker = drop.find(".sticker_container." + current.stickers[drag.data('type_id')].name);

    new_sticker.animate({
        left: left_destination,
        top: top_destination,
        width: drag.width() / 4,
        height: drag.height() / 4
    }, 800, "swing", function(){
        new_sticker.remove();
        top_sticker.trigger("mouseover");
        setTimeout(function(){
            top_sticker.trigger("mouseout");
        }, 3000);
        // +1 effect
        if (target_sticker.length) {
            canvas_effects.give_bonus(1, target_sticker.offset().left + (target_sticker.width()/2), target_sticker.offset().top + (target_sticker.height()/2));
        } else {
            console.log("No target sticker.", drag);
        }
    });
};

stickers.effects.roll_in_count = function (drag, drop) {
    // Roll in count animation
    var target_count = drop.find(".sticker_container." + current.stickers[drag.data('type_id')].name + " + .sticker_count");
    if (target_count.length) {
        var count_span = target_count.children("span");
        var count = parseInt(count_span.text(), 10);
        var current_count = $('<span class="animated">' + (count) + '</span>');
        var old_count = $('<span class="animated">' + (count - 1) + '</span>');
        count_span.addClass("hide_text");
        current_count.insertBefore(count_span);
        old_count.insertBefore(count_span);
        var height = old_count.outerHeight();
        var padding_top = count_span.position().top;
        var padding_left = parseInt(count_span.parent().css("padding-left"), 10);
        current_count.css({
            top:height + padding_top,
        });
        old_count.css({
            top:padding_top,
        });
        // Wait for the overlay to fade in
        setTimeout(function () {
            current_count.animate({top:padding_top}, 300, function () {
                $(this).remove();
            });
            old_count.animate({top:-height}, 300, function () {
                $(this).remove();
                count_span.removeClass("hide_text");
            });
        }, 800);
    }
};

stickers.effects.put_back = function (drag) {
    // Putting sticker back in place
    var sticker_name = drag.data("name");
    var dragStart = drag.data("mobileDrag").dragStart;
    var placeholder = $("#page .empty." + sticker_name);
    placeholder.removeClass("empty");
    var fadeback_opacity = (drag.data('limited') && drag.data('remaining') <= 0) ? 0.5 : 1;
    var fadeback_speed = 500;
    if (drag.is(".stale") || drag.is(".stop") || drag.is(".poop")) {
        fadeback_opacity = 0.5;
    }
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

        if(drag.data('is_limited') == "True" && drag.data('remaining') <= 0) {
            drag.addClass("none_remaining").mobileDrag('makeUndraggable');
        }
    });
};

stickers.effects.flash_outline = function (drop, speed) {
    var i = 4;
    speed = speed || 50
    var flash = setInterval(function (){
        if (i > 0) {
            drop.toggleClass("drop_target");
        } else {
            clearInterval(flash);
        }
        i--;
    }, speed);
};

stickers.effects.you_voted = function (drag) {
    return canvas_effects.short_message("you voted!", drag.offset().left + 25, drag.offset().top - 10, 400);
};

stickers.on_drop_success = function (drag, drop, comment_id, response) {
    canvas.fire("stickered");
    stickers.update_stickerable(drop, comment_id, response.new_counts, response.sorted_counts, response.top_sticker);
    realtime.unpause_updates();

    stickers.effects.you_voted(drag);

    stickers.effects.flash_outline(drop);
    stickers.effects.drag_to_corner(drag, drop);
    stickers.effects.roll_in_count(drag, drop);
    stickers.effects.put_back(drag);
};

stickers.on_drop_failure = function (drag, drop, comment_id, response) {
    stickers.end_drag(drag);

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

        var height_diff = drag.offset().top - drop.offset().top;
        stickers.overlay_message(drop, text, 3000, height_diff);
    }
    realtime.unpause_updates();
};

stickers.incr_remaining = function (sticker, incr, check_remainder) {
    if (!isNaN(parseInt(sticker * 1))) {
        sticker = $(stickers.pack_selector + ' .sticker_container[data-type_id=' + sticker + ']');
    } else {
        sticker = $(sticker);
    }
    var remaining = parseInt(sticker.data('remaining'), 10);
    if (!remaining) {
        remaining = 0
    }
    remaining += incr;
    stickers.set_remaining(sticker, remaining, check_remainder);
};

stickers.set_remaining = function (sticker, remaining, check_remainder) {
    var sticker = $(sticker);
    sticker
        .data('remaining', remaining)
        .find('.sticker_remaining_number').text(remaining);

    sticker.parent().children(".sticker_remaining").find(".sticker_remaining_number").text(remaining);

    if (sticker.data('name') == 'num1') {
        shop_balance = $('.sticker_shop .shop_footer .balance');
        if (shop_balance.length) {
            shop_balance.children(".sticker_currency_count").text(remaining);
        }
    }
    if (remaining == 1) {
        sticker.mobileDrag('makeDraggable').removeClass("none_remaining");
    } else if (check_remainder && remaining <= 0) {
        sticker.mobileDrag('makeUndraggable').addClass("none_remaining");
    }
};

stickers.last_updated_counts = null;
stickers.update_counts = function (counts) {
    stickers.last_updated_counts = counts;
    $.each(current.stickers, function (type_id, sticker) {
        if (!sticker.is_limited) return;

        var sticker_container = $(stickers.pack_selector + ' .sticker_container.' + sticker.name);
        if (!sticker_container.length && counts[type_id]) {
            // If we don't have the sticker assume it needs to be added to inventory
            var inventory_node = $(stickers.pack_selector + " .stickers_inventory");
            if ($('#sticker_pack').length) {
                if (!inventory_node.length) {
                    $('<section class="stickers_inventory"></section>').insertAfter($('#sticker_pack .stickers_primary'));
                }
                inventory_node = $(stickers.pack_selector + " .stickers_inventory");
                sticker_container = stickers.append_sticker(sticker, inventory_node, "inventory_sticker_template").find(".sticker_container");
            } else {
                sticker_container = stickers.append_sticker(sticker, inventory_node, "inventory_sticker_template").find(".sticker_container");
            }
            if ($('#page.thread').length) {
                stickers.wire_sticker(sticker_container);
            } else {
                sticker_pack.wire_sticker(sticker_container);
            }
            inventory_node.removeClass('empty_inventory');
        } else if (!sticker_container.length) {
            return;
        }

        var count = counts[type_id] || 0;
        current.stickers[type_id].user_remaining = counts[type_id] || 0;

        stickers.set_remaining(sticker_container, count, true);
    });
    console.log("Setting sticker_currency_count (update_counts)", counts[7] || 0)
    $('.sticker_currency_count').text(counts[7] || 0);
};

stickers.end_drag = function (sticker) {
    $('.menu').removeClass('disabled');
    sticker.mobileDrag('makeUndraggable');
    sticker.addClass("absolute");
    $('nav:not(.fixed) .groups').css('z-index', '');
    var dragStart = sticker.data("mobileDrag")["dragStart"];
    var placeholder = $(stickers.pack_selector + " .empty");
    placeholder.removeClass("empty");
    $("body").removeClass(stickers.body_dragging_class);
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

stickers.wire_sticker = function (sticker) {
    sticker.mobileDrag({
        targetClass: "stickerable",
        draggableClass: stickers.draggable_class,
        draggingClass: stickers.dragging_class,
        drag: function () {
            realtime.pause_updates();
            $('nav:not(.fixed) .groups').css('z-index', '0');
            $('.menu').addClass('disabled');
            stickers.incr_remaining(sticker, -1);
            sticker.clone().removeClass(stickers.draggable_class + " " + stickers.dragging_class).addClass("empty show_count backing").css({
                backgroundPosition: "0 " + -(sticker.height() * 2) + "px"
            }).insertAfter(sticker);
            sticker.tooltip('clear').addClass("shadow");
            canvas.trigger_scroll();
        },
        endDrag: stickers.end_drag.partial(sticker),
        drop: function (drop) {
            $('.menu').removeClass('disabled');
            $('nav:not(.fixed) .groups').css('z-index', '');
            var element = $(drop);
            var comment_id = element.attr('data-comment_id');
            var type_id = sticker.data('type_id');
            var callable = type_id < 2000 ? stickers.add_to_comment : sticker_actions.perform;
            $("body").removeClass(stickers.body_dragging_class);
            callable(sticker, drop, comment_id, type_id);
        }
    });
};

stickers.toggle_actions = function () {
    var actions_wrapper = $("#sticker_widget .sticker_actions .wrapper");
    var span = $("#sticker_widget .actions_toggle span");
    if (stickers.actions_open) {
        span.text("Show actions");
        actions_wrapper.slideUp(50);
    } else {
        span.text("Hide actions");
        actions_wrapper.slideDown(100);
    }
    stickers.actions_open = !stickers.actions_open;
};

stickers.update_seasonal_timer = function () {
    var zfill = function (str) {
        str = str.toString();
        while (str.length < 2) {
            str = "0" + str;
        }
        return str;
    }

    var delta = current.seasonal_event.end_time - canvas.unixtime();

    if (delta <= 0) {
        $('.stickers_seasonal .timer')
            .addClass('out_of_time')
            .text("00:00:00");
    } else {
        var hours = Math.floor(delta / 3600);
        var minutes = Math.floor((delta / 60) % 60);
        var seconds = Math.floor(delta % 60);

        $('.stickers_seasonal .timer').text(zfill(hours) + ":" + zfill(minutes) + ":" + zfill(seconds));
    }
};

stickers.wire = function (fixed) {
    stickers.pack_selector = "#sticker_widget";

    $("#sticker_widget .sticker_container").each(function () {
        var sticker = $(this);
        stickers.wire_sticker(sticker);
        var description = stickers.descriptions[sticker.data('name')];
        if (description) {
            sticker.tooltip({content: description, delay_on: 500, escape_html: false});
        }
    });

    var widget_padding = (current.is_mobile) ? 25 : $("nav").outerHeight(true) + parseInt($("#page").css("marginTop"));
    if (fixed == true) {
        // Make stickers mobile if there is room vertically
        $(window).bind("scroll", function () {
            $("#sticker_widget").addClass("shadow");
            if ($(window).scrollTop() > $("#sticker_column_border").offset().top - widget_padding
            && (current.is_mobile || $(window).height() > $("#sticker_widget").outerHeight(true))
            && $(window).scrollTop() + $("#sticker_widget").outerHeight(true) + widget_padding < ($("#sticker_column_border").offset().top + $("#sticker_column_border").height())
            ) {
                if (current.is_mobile) {
                    $("#sticker_widget").css({position:"absolute", top:widget_padding + $(window).scrollTop() - $("#sticker_column_border").offset().top, bottom:"auto", left:0});
                } else {
                    $("#sticker_widget").css({position:"fixed", top:widget_padding, bottom:"auto", left:$("#sticker_column").offset().left-$(window).scrollLeft()});
                }
            } else if ($(window).scrollTop() + $("#sticker_widget").outerHeight(true) + widget_padding >= ($("#sticker_column_border").offset().top + $("#sticker_column_border").height())) {
                $("#sticker_widget").css({position:"absolute", top:"auto", bottom:0, left:0}).removeClass("shadow");
            } else {
                $("#sticker_widget").css({position:"static"});
            }
        });
    }
    // Set sticker column min-height
    $("#sticker_column_border").css("min-height", $("#sticker_widget").height());
    $("#sticker_column").css("min-height", $("#sticker_column").height() + $("#sticker_widget").height());
    // Set up listener to fix height of column and listen for change in page size
    $("#sticker_column").parent().resize(function () {
        $("#sticker_column_border").css("height", Math.max($("#sticker_widget").outerHeight(), ($("#sticker_column").parent().height() - $("#sticker_column_border").position().top - parseInt($("#sticker_column").css("padding-bottom")) + parseInt($("#sticker_column").parent().css("padding-top")))));
        canvas.trigger_scroll();
    })
    $("#sticker_widget").resize(function () {
        if ($("#sticker_widget").outerHeight(true) > $("#sticker_column_border").outerHeight(true)) {
            $("#sticker_column, #sticker_column_border").css("height", $("#sticker_widget").outerHeight(true));
        }
        else {
            $("#sticker_column_border").css("height", $("#sticker_column_border").outerHeight(true));
        }

        canvas.trigger_scroll();
    })
    $("#sticker_column").parent().trigger("resize");

    // Back to top
    $("#sticker_widget .back_to_top").click(function () {
        $.scrollTo(0, 500);
        canvas.trigger_scroll();
    });
    $("#sticker_column_border .back_to_top img").click(function () {
        $.scrollTo(0, 500);
        canvas.trigger_scroll();
    });

    $("#sticker_widget .actions_toggle").bind("click", function (e) {
        stickers.toggle_actions();
    });

    // Check for animations in sticker widget
    $("#sticker_widget .sticker_container").each(function () {
        stickers.check_for_animation($(this).data("type_id"), $(this).attr("class").split(" ")[1]);
    });

    // Custom tooltip for Andrew WK sticker
    $(".sticker_container.partyhard").tooltip({
        content: "Andrew W.K. stickered this post!",
        delegate: $("body"),
        top: 50,
    });

    $('#sticker_widget .shop_ad').bind('click', function () {
        if (current.logged_in) {
            new canvas.StickerShopDialog();
        } else {
            canvas.encourage_signup('sticker_shop');
        }
    });

    if (current.seasonal_event) {
        setInterval(stickers.update_seasonal_timer, 1000);
        stickers.update_seasonal_timer();
    }
};
