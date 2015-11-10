sidebar = {};

sidebar.wire = function () {
    sidebar.untracked_tag = null;
    sidebar.tracked_tags = {};

    sidebar.tag_subscriptions = {};

    if (!$('#sidebar').length) {
        return false;
    }

    sidebar.tag_search_field = $('#sidebar .tag_search input');
    sidebar.tracked_tags_list = $('#sidebar .tracked_tags');

    canvas.bind_label_to_input(sidebar.tag_search_field);

    // Back to top setup
    sidebar.back_to_top_node = $('#sidebar .back_to_top');
    sidebar.back_to_top_bottom = sidebar.back_to_top_node.css("bottom");
    var scroll_to_top_is_visible = false;
    $(window).bind("scroll.back_to_top", function() {
        if ($(window).scrollTop() > 300) { // <-- Set threshold here
            if (!scroll_to_top_is_visible) {
                sidebar.show_back_to_top();
                scroll_to_top_is_visible = true;
            }
        } else if (scroll_to_top_is_visible) {
            sidebar.hide_back_to_top();
            scroll_to_top_is_visible = false;
        }
    });

    // realtime for untracked tags
    $(sidebar.tracked_tags_list.find('.untracked')).each(function () {
        var tag_name = $(this).find('a.remove').data('tag');
        sidebar.untracked_tag = tag_name;
        var channel = 'tu:' + tag_name;
        sidebar.tag_subscriptions[channel] = realtime.subscribe({
            channel: channel,
            last_message_id: null,
            timestamp: canvas.unixtime()
        }, sidebar.tag_realtime_update);
    });

    $(sidebar.tracked_tags_list.find('.tracked_tag')).each(function () {
        var tag_name = $(this).find('a.remove').data('tag');
        var initial = $(this).find('a.remove').data('unseen');
        if(initial) {
            if (initial == "10+") {
                sidebar.tracked_tags[tag_name] = 10;
            } else {
                sidebar.tracked_tags[tag_name] = 0;
            }
        } else {
            sidebar.tracked_tags[tag_name] = 0;
        }
    });

    // realtime for followed tags
    $(current.tag_channels).each(function () {
        sidebar.tag_subscriptions[this.channel] = realtime.subscribe(this, sidebar.tag_realtime_update);
    });

    var handle_search = function () {
        var val = sidebar.tag_search_field.val().trim();
        if (val.length > 0) {
            sidebar.search_tag(val);
            sidebar.tag_search_field.val('');
        }
    };

    sidebar.tag_search_field.keydown(function (e) {
        if(e.keyCode == 13) {
            e.preventDefault();
            handle_search();
        }
        if(e.keyCode == 32) {
            e.preventDefault();
        }
    });

    $('#sidebar .tag_search button').click(handle_search);

    $(sidebar.tracked_tags_list).delegate('a.remove', 'click', function() {
        var tag_name = $(this).data('tag');
        canvas.api.unfollow_tag(tag_name);
        sidebar.tracked_tags[tag_name] = -1;
        var channel = 'tu:' + tag_name;
        var uid = sidebar.tag_subscriptions[channel];
        realtime.unsubscribe(channel, uid);
        sidebar.tag_subscriptions[channel] = null;
        $(this).parent().addClass("untracked");
    });

    $('.suggestion_widget').delegate('div.close_options', 'click', function (event) {
        var type = $(event.target).data('type');
        var id = $(event.target).data('id');
        var section = $(event.target).parent();
        if (type == 'user') {
            canvas.api.hide_suggested_user(id).done(function (request) {
                if (request.success) { $(section).hide();}
            });
        } else if (type == 'tag') {
            canvas.api.hide_suggested_tag(id).done(function (request) {
                if (request.success) { $(section).hide();}
            });
        }

    });

    sidebar.wire_realtime_feed();
};

sidebar.wire_realtime_feed = function () {
    sidebar.feed_subscriptions = {};

    $(current.feed_following_channels).each(function () {
        sidebar.feed_subscriptions[this.channel] = realtime.subscribe(this, sidebar.feed_realtime_update);
    });

    sidebar.render_realtime_feed_count();
};

sidebar.feed_realtime_update = function (messages) {
    if (!messages.length) {
        return;
    }

    current.feed_unseen += messages.length;

    sidebar.render_realtime_feed_count();
};

sidebar.render_realtime_feed_count = function () {
    var count = $('#sidebar .feed .realtime_count');
    count.text(current.feed_unseen);

    if (current.feed_unseen) {
        count.show();
    } else {
        count.hide();
    }
};

sidebar.tag_realtime_update = function (messages) {
    if (!messages.length) {
        return;
    }

    var first = messages[0];
    sidebar.tracked_tags[first.tag] += messages.length;
    var len = sidebar.tracked_tags[first.tag];
    if (len >= 10) {
        len = "10+";
    }
    $('#sidebar li.tracked_tag').find('.realtime_count').each(function () {
        if ($(this).data('tag') == first.tag) {
            $(this).text(len);
        }
    });
};

sidebar.search_tag = function (tag_name) {
    if (! (sidebar.tracked_tags[tag_name] >= 0)) {
        sidebar.navigate_tag(tag_name);
    }
};

sidebar.navigate_tag = function (tag_name) {
    window.location = "/x/" + tag_name;
}

sidebar.make_tag_active = function (tag_name) {
    sidebar.tracked_tags_list.find('li .remove').each(function () {
        if ($(this).data('tag') == tag_name) {
            $(this).parent().addClass("active");
        } else {
            $(this).parent().removeClass("active");
        }
    });
};

sidebar.add_searched_tag = function ()  {
    if (sidebar.untracked_tag != null) {
        var tag_name = sidebar.untracked_tag;
        sidebar.untracked_tag = null;
        sidebar.tracked_tags[tag_name] = 0;
        canvas.api.follow_tag(tag_name);
        sidebar.tracked_tags_list.find('li .remove').each(function () {
            var self = $(this);
            if (self.data('tag') == tag_name) {
                var parent = self.parent();
                parent.removeClass("untracked").addClass("js_just_tracked");
                parent.one("mouseleave", function(e) {
                    parent.removeClass("js_just_tracked");
                });
            }
        });
    }
};

sidebar.add_tag = function (tag_name, untracked) {
    if (!sidebar.tracked_tags[tag_name] >= 0) {
        sidebar.tracked_tags_list.prepend(sidebar.make_tag(tag_name, untracked));
        sidebar.tracked_tags[tag_name] = 0;
    }
};

sidebar.make_tag = function (tag_name, untracked) {
    return canvas.render(
        'tracked_tag_template',
        {
            tag_name    : tag_name,
            untracked   : untracked,
        }
    );
};

sidebar.back_to_top = function() {
    $.scrollTo(0, 100);
};

sidebar.show_back_to_top = function() {
    sidebar.back_to_top_node.stop().animate({
        bottom  : 0
    }, 200);
};

sidebar.hide_back_to_top = function() {
    sidebar.back_to_top_node.stop().animate({
        bottom  : sidebar.back_to_top_bottom
    }, 200);
};
