window.new_thread = {
    display_buffer: 100,
    replies: {},
};

// nodes which have been expanded and had their detail modules loaded, so that we don't reload them.
new_thread._cached_posts = [];

new_thread.toggle_expanded_state = function (post_node) {
    var is_focused = post_node.hasClass("expanded_li");
    if (is_focused) { new_thread.remove_expanded_state(post_node); }
    else            { new_thread.give_expanded_state(post_node); }
};

new_thread.remove_expanded_state = function (post_node) {
    post_node.removeClass("expanded_li");
    var expanded = post_node.children(".expanded");
    var not_expanded = post_node.children(".not_expanded");
    var caption = expanded.find(".post_info > .caption");
    if (caption.length) {
        caption = caption.html();
        not_expanded.find(".caption").html(caption);
    }
    not_expanded.show();
    expanded.hide();
    new_thread.thread_info.removeClass("collapsed");
};

new_thread.load_post_details = function (post_node) {
    var comment_id = $(post_node).data('comment_id');

    if (new_thread._cached_posts.indexOf(comment_id) !== -1) {
        return;
    }
    var detail = post_node.find('.detail_modules');
    detail.addClass('loading');
    canvas.api.thread_comment_details(comment_id).done(function (resp) {
        detail.removeClass('loading');
        detail.html(resp);
        new_thread._cached_posts.push(comment_id);
    }).fail(function () {
        detail.text('Failed to load details, please refresh to try again.');
    });
};

new_thread.give_expanded_state = function (post_node) {
    var expanded = post_node.children(".expanded");
    var not_expanded = post_node.children(".not_expanded");
    var caption = not_expanded.find(".caption");
    if (caption.length) {
        caption = caption.html();
        expanded.find(".post_info > .caption").html(caption); // Make sure not to target the replies
    }
    expanded.show();
    not_expanded.hide();
    post_node.addClass("expanded_li");
    new_thread.thread_info.addClass("collapsed");

    new_thread.load_post_details(post_node);
};

new_thread.scroll_to_post_update_url = function (post_node) {
    var anchor = post_node.children("a.id_anchor");
    var id = anchor.attr("name");

    // Scroll to the anchor tag
    $(window).scrollTop(anchor.offset().top);

    // Now we also want to update the url (which will also remove the hash)
    window.history.replaceState({}, "", new_thread.base_url + "reply/" + id);
};

new_thread.goto_post = function (post_url) {
    var url_split = post_url.split('/');
    var post_id = url_split[url_split.length - 1];
    var post_is_on_page = false;
    for (var i = 0; i < new_thread.reply_ids.length; i++) {
        if (post_id == new_thread.reply_ids[i]) {
            post_is_on_page = true;
        }
    }
    if (post_is_on_page) {
        var post_node = $('ul.posts > li[data-comment_id = ' + post_id + ']');
        if (post_node.length) {
            new_thread.focus_post(post_node);
            return;
        }
    }
    document.location = post_url;
};

new_thread.focus_post = function (post_node) {
    $.each($('.expanded_li'), function () {
        new_thread.remove_expanded_state($(this));
    });
    if (post_node.hasClass("text_only")) {
        post_node.addClass("expanded_li");
        new_thread.scroll_to_post_update_url(post_node);
        return;
    }
    new_thread.give_expanded_state(post_node);
    new_thread.scroll_to_post_update_url(post_node);
    new_thread.place_nav_arrows(post_node);
    // Loading Giant images
    new_thread.load_large_image(post_node);
    var next_reply_with_content = new_thread.get_next_reply_with_content(post_node, "next");
    var prev_reply_with_content = new_thread.get_next_reply_with_content(post_node, "prev");
    new_thread.check_nav_arrow_status(post_node, prev_reply_with_content, next_reply_with_content);
    if (next_reply_with_content) {
        new_thread.load_large_image(next_reply_with_content);
    }
    if (prev_reply_with_content) {
        new_thread.load_large_image(prev_reply_with_content);
    }
    new_thread.set_max_sidebar_height(post_node);
};

new_thread.get_next_reply_with_content = function (post_node, dir) {
    var next_node = post_node[dir]();
    while (next_node.length && next_node.hasClass("text_only")) {
        next_node = next_node[dir]();
    }
    if (next_node.length && !next_node.hasClass("text_only")) {
        return next_node
    }
};

new_thread.focus_on_next = function (dir) {
    var next_node = new_thread.get_next_reply_with_content($(".expanded_li"), dir);
    if (next_node) {
        new_thread.focus_post(next_node);
    } else {
        if (dir == "prev" && new_thread.page_current > 1) {
            document.location = new_thread.base_url + (new_thread.page_current - 1) + '#last';
        } else if (dir == "next" && new_thread.page_current < new_thread.page_last) {
            document.location = new_thread.base_url + (new_thread.page_current + 1) + '#first';
        }
    }
};

new_thread.place_nav_arrows = function (post_node) {
    var nav_offset = $(window).scrollTop() - post_node.offset().top;
    $('nav', post_node).css({
        top     : nav_offset,
        height  : $(window).height(),
    });
};

new_thread.check_nav_arrow_status = function (post_node, prev_reply, next_reply) {
    if (!prev_reply && new_thread.page_current == 1) {
        $("nav .prev", post_node).addClass("disabled");
    }
    if (!next_reply && new_thread.page_current == new_thread.page_last) {
        $("nav .next", post_node).addClass("disabled");
    }
}

new_thread.show_timestamps = function () {
    var posts = $('ul.posts li');
    var last_timestamp;
    posts.each(function (index, value) {
        var timestamp_node = $(value).find('.not_expanded .timestamp p');
        var timestamp = timestamp_node.text();
        if (index <= 0 || last_timestamp !== timestamp) {
            timestamp_node.show();
        }
        last_timestamp = timestamp;
    });
};

new_thread.set_max_sidebar_height = function (post_node) {
    var scroll_node = $('.scrolling_wrapper', post_node);
    var image_height = $('.fullsize_image_wrapper', post_node).outerHeight();
    var reply_widget_height = $('.reply_widget', post_node).outerHeight();
    var new_height = image_height - reply_widget_height - 20;
    scroll_node.css("max-height", new_height);
};

new_thread.load_large_image = function (post_node) {
    var target_img = $('.expanded .fullsize_image_wrapper .image_container img', post_node);
    var img_url = target_img.attr("data-url");
    if (!img_url) {
        return false;
    }
    target_img.attr("src", img_url).removeAttr("data-url");
    target_img.load(function () {
        // We can only do this after the image loads so we have the have
        // the height of the image after CSS max-height has been applied
        // based on the media queries. It's messy, but it's the only way
        // I could get it to work. --dave
        new_thread.set_max_sidebar_height(post_node);
    });
    return true;
};

new_thread.toggle_image_size = function (img) {
    if (img.attr("style")) {
        img.removeAttr("style");
    } else {
        img.css({
            "max-height" : 10000,
        });
    }
};

new_thread.wire_comments = function (comments) {
    $.each(comments, function (_, comment) {
        var comment = new canvas.ThreadComment(new_thread, comment);
    });
};

new_thread.wire = function () {
    // For now we only wire the OP, since we do nothing special with the others yet.
    new_thread.wire_comments([new_thread.op_comment]);

    new_thread.thread_info = $('#page .thread_info');
    
    $("body")
    .delegate('#page ul.posts li .not_expanded .expand_post', "click", function(e) {
        if (e.button == 0) {
            var post = $(this).parents("li");
            new_thread.focus_post(post);
            return false;
        }
    })
    .delegate('#page a.js_check_for_local_link', "click", function (e) {
        if (e.button == 0) {
            var location = $(this).attr("href");
            new_thread.goto_post(location);
            return false;
        }
    })
    .bind("keydown", function (e) {
        if (e.keyCode == 38 || e.keyCode == 37 || e.keyCode == 40 || e.keyCode == 39) {
            e.preventDefault();
        }
    })
    .bind("keyup", function (e) {
        if (e.keyCode == 38 || e.keyCode == 37) {
            e.preventDefault();
            new_thread.focus_on_next("prev");
        } else if (e.keyCode == 40 || e.keyCode == 39) {
            e.preventDefault();
            new_thread.focus_on_next("next");
        }
    })
    .resize(function () {
        var expanded = $('#page .expanded_li');
        if (expanded.length) {
            new_thread.set_max_sidebar_height(expanded);
        }
    });

    canvas.prevent_scroll_propagation($('#page .scrolling_wrapper'));

    $('#page ul.posts li .close').click(function () {
        var target = $(this).parents("li");
        new_thread.remove_expanded_state(target);
        window.history.replaceState({}, "", new_thread.base_url);
        return false;
    });
    $('#page ul.posts li nav .prev').click(function () {
        new_thread.focus_on_next("prev");
        return false;
    });
    $('#page ul.posts li nav .next').click(function () {
        new_thread.focus_on_next("next");
        return false;
    });

    new_thread.show_timestamps();

    if (!document.location.hash && new_thread.comment_to_expand) {
        new_thread.focus_post($('.expanded_li'));
    } else if (['#first', '#last'].indexOf(document.location.hash) !== -1) {
        var anchor = $('a[name="' + document.location.hash.substr(1) + '"]');
        if (anchor.length) {
            new_thread.focus_post(anchor.closest('.post'));
        } else {
            window.history.replaceState({}, "", window.location.pathname);
        }
    }
};

