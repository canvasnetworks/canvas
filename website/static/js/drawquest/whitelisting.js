$(function() {
    var ANIMATION_LENGTH = 200;
    var JUDGEMENTS = [];
    var WAIT_UNTIL_SUBMIT = 4000;
    var INF_SCROLL_BUFFER = 1200;
    var PAGINATION_SIZE = 100;

    $('#whitelisting_toggle').click(function () {
        var enabled = $(this).data('enabled');
        if (enabled) {
            $.ajax({
                type        : "POST",
                url         : '/api/whitelisting/disable',
                contentType : 'application/json',
                data        : JSON.stringify({}),
            }).done(function () {
                location.reload();
            }).fail(function () {
                alert("Error disabling whitelist. Talk to Alex.");
            });
        } else {
            var id = prompt("At which comment ID to you want to start whitelisting? Right-click and click inspect on a drawing to find its comment ID. It and all earlier drawings (with lower IDs) will be allowed, all later ones will require whitelisting.");
            if (id == null) {
                return;
            }
            $.ajax({
                type        : "POST",
                url         : '/api/whitelisting/enable',
                contentType : 'application/json',
                data        : JSON.stringify({from_id: id}),
            }).done(function () {
                location.reload();
            }).fail(function () {
                alert("Error enabling whitelist. Talk to Alex.");
            });
        }
    });

    // Make the first item active
    $("ul li:first-of-type").addClass("active");

    // AJAX CALLS, FIRE AND FORGET
    var ajax_whitelist = function(id, done, fail) {
        url = "/api/whitelisting/allow";
        $.ajax({
            type        : "POST",
            url         : url,
            contentType : 'application/json',
            data        : JSON.stringify({
                comment_id  : id
            })
        }).done(done).fail(fail);
    };
    var ajax_disable = function(id, ban_user, done, fail) {
        url = "/api/whitelisting/deny";
        $.ajax({
            type        : "POST",
            url         : url,
            contentType : 'application/json',
            data        : JSON.stringify({
                comment_id      : id,
                disable_author  : ban_user
            })
        }).done(done).fail(fail);
    };
    var pagination_url_prefix = '/whitelisting/paginated/';

    if ($("body").hasClass('flag_queue')) {
        pagination_url_prefix = '/whitelisting/flagged/paginated/';
    }

    var ajax_more_posts = function(last_id, done, fail) {
        url = pagination_url_prefix + last_id;
        $.ajax({
            type    : "GET",
            url     : url,
        }).done(done).fail(fail);
    };

    var get_active_item = function() {
        return $("ul li.active");
    };

    var scroll_to_active = function() {
        if (!get_active_item().length) {
            return;
        }
        var top_of_page_buffer = 10;
        $('html,body').stop().animate({
            scrollTop: get_active_item().offset().top - top_of_page_buffer
        }, 100)
    };
    // Call it after page jumps
    setTimeout(scroll_to_active, 100);

    var select_particular_item = function(item) {
        var current = get_active_item();
        current.removeClass("active");
        item.addClass("active");
        setTimeout(scroll_to_active, ANIMATION_LENGTH + 1);
    }

    var select_next_item = function(should_fallback_to_prev) {
        var current = get_active_item();
        var next = current.next();
        if (next.length) {
            current.removeClass("active");
            next.addClass("active");
        } else if (should_fallback_to_prev === true) {
            var prev = current.prev();
            if (prev.length) {
                current.removeClass("active");
                prev.addClass("active");
            }
        }
        if (should_fallback_to_prev === true) {
            setTimeout(scroll_to_active, ANIMATION_LENGTH + 1);
        } else {
            scroll_to_active();
        }
    };

    var select_previous_item = function() {
        var current = get_active_item();
        var prev = current.prev();
        if (prev.length) {
            current.removeClass("active");
            prev.addClass("active");
        }
        scroll_to_active();
    }

    var remove_item = function(item, is_whitelisted) {
        var placeholder = $("<li class=\"js_ignore\"></li>");
        placeholder.css("width", "500px");
        placeholder.insertAfter(item);
        var pos = item.position()
        item.css({
            position    : "absolute",
            left        : pos.left,
            top         : pos.top
        });
        if (is_whitelisted) {
            item.animate({
                top : "-=50",
                opacity : 0
            }, ANIMATION_LENGTH);
        } else {
            item.animate({
                top : "+=60",
                opacity : 0,
            }, ANIMATION_LENGTH);
        }
        placeholder.animate({
            width : 0
        }, ANIMATION_LENGTH, function() {
            placeholder.remove();
            item.removeAttr("style");
            item.detach();
        });
    };

    var return_judged_item = function(node) {
        var active_item = get_active_item();
        if (active_item.length) {
            var pos = active_item.position();
            var placeholder = $("<li class=\"js_ignore\"></li>");
            placeholder.css("width", "0px");
            node.insertBefore(active_item);
            placeholder.insertBefore(active_item);
            node.css({
                position    : "absolute",
                left        : pos.left,
                top         : pos.top,
                opacity     : 0
            });
            node.animate({
                opacity : 1
            }, ANIMATION_LENGTH, function() {
                node.removeAttr("style");
            });
            placeholder.animate({
                width   : "500px"
            }, ANIMATION_LENGTH, function() {
                placeholder.remove();
            });
        } else {
            node.prependTo("ul");
        }
        select_particular_item(node);
    };

    var whitelist_item = function(item) {
        if (item[0] === get_active_item()[0]) {
            select_next_item(true);
        }
        var item_id = item.data("id");
        var judgement = {
            id          : item_id,
            node        : item,
            was_undone  : false
        };
        JUDGEMENTS.push(judgement);
        remove_item(item, true);
        setTimeout(function() {
            if (judgement.was_undone) {
                return;
            }
            clear_from_judgements(item_id);
            ajax_whitelist(item_id, function() {}, function() {
                alert("Something went wrong whitelisting item:" + item_id);
            });
        }, WAIT_UNTIL_SUBMIT);
    };

    var disable_item = function(item) {
        if (item[0] === get_active_item()[0]) {
            select_next_item(true);
        }
        var item_id = item.data("id");
        var judgement = {
            id          : item_id,
            node        : item,
            was_undone  : false
        };
        JUDGEMENTS.push(judgement);
        remove_item(item, false);
        setTimeout(function() {
            if (judgement.was_undone) {
                return;
            }
            clear_from_judgements(item_id);
            ajax_disable(item_id, false, function() {}, function() {
                alert("Something went wrong disabling item:" + item_id);
            });
        }, WAIT_UNTIL_SUBMIT);
    };

    var ban_and_disable_item = function(item) {
        author = ""
        if (confirm("Really BAN the user:" + author)) {
            if (item[0] === get_active_item()[0]) {
                select_next_item(true);
            }
            var item_id = item.data("id");
            var judgement = {
                id          : item_id,
                node        : item,
                was_undone  : false
            };
            JUDGEMENTS.push(judgement);
            remove_item(item, false);
            setTimeout(function() {
                if (judgement.was_undone) {
                    return;
                }
                clear_from_judgements(item_id);
                ajax_disable(item_id, true, function() {}, function() {
                    alert("Something went wrong disabling item:" + item_id);
                });
            }, WAIT_UNTIL_SUBMIT);
        }
    };

    var clear_from_judgements = function(item_id) {
        for (var i = 0; i < JUDGEMENTS.length; i++) {
            if (JUDGEMENTS[i].id === item_id) {
                JUDGEMENTS.splice(i, 1);
                break;
            }
        }
    };

    var undo = function() {
        var judgement = JUDGEMENTS.pop();
        if (judgement) {
            judgement.was_undone = true;
            return_judged_item(judgement.node);
        } else {
            alert("Nothing to undo, you only have " + WAIT_UNTIL_SUBMIT/1000 + " seconds to undo an action");
        }
    };

    // Bind buttons
    $("ul").on("click", "li footer button", function(e) {
        e.stopPropagation();
        var button = $(this);
        var li = button.closest("li");
        if (button.hasClass("whitelist")) {
            whitelist_item(li);
        } else if (button.hasClass("disable")) {
            disable_item(li);
        } else if (button.hasClass("ban")) {
            ban_and_disable_item(li);
        }
    });

    // Bind the keyboard
    keypress.combo("left", select_previous_item);
    keypress.combo("right", select_next_item);
    keypress.combo("meta z", undo);
    var key_combos = [
        {
            keys            : "u",
            prevent_repeat  : true,
            on_keydown      : undo
        },
        {
            keys            : "w",
            prevent_repeat  : true,
            on_keydown      : function() {
                whitelist_item(get_active_item());
            }
        },
        {
            keys            : "d",
            prevent_repeat  : true,
            on_keydown      : function() {
                disable_item(get_active_item());
            }
        },
        {
            keys            : "b",
            prevent_repeat  : true,
            on_keydown      : function() {
                ban_and_disable_item(get_active_item());
            }
        }
    ];
    keypress.register_many(key_combos);

    // Prevent user from leaving when we're not done processing
    window.onbeforeunload = function() {
        if (JUDGEMENTS.length) {
            return "Please wait 10 seconds for processing to finish before leaving.";
        }
    };

    // INFINITE SCROLL
    var is_loading = false;
    var append_to_node = $("ul");
    var get_last_id = function() {
        return $("ul li:last-of-type").data("id");
    }
    var loading_div = $("div.loading");
    $(window).scroll(function() {
        if (is_loading) {
            return false;
        }
        if ($(window).scrollTop() + $(window).height() + INF_SCROLL_BUFFER >= $(document).height()) {
            is_loading = true;
            loading_div.show()
            ajax_more_posts(get_last_id(), function(html) {
                loading_div.hide()
                if (html.replace(/\s+/g, '').length) {
                    append_to_node.append(html);
                } else {
                    return $(window).unbind("scroll");
                }
                is_loading = false;
            }, function() {
                loading_div.hide()
                is_loading = false;
                return $(window).unbind("scroll");
            });
        }
    });
});
