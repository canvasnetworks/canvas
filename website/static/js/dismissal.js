
canvas.wire_dismissables = function () {
    var base_selector = ".dismissable .close_options ";

    var get_item = function(event) {
        var item = $(event.target).closest('.dismissable');
        remove_items(item);
        item.addClass("hidden_by_user");
        return item;
    };

    var remove_items = function(comments) {
        comments.hide('blind', 200, function() {
            $(this).remove();
        });
    };

    var remove_items_with_matching_data = function (key, item) {
        // excludes `item` itself from removal.
        var hide_comments =
            $('body')
            .find('.dismissable[data-' + key + '=' + item.data(key) + ']')
            .not('.hidden_by_user');
        remove_items(hide_comments);
    };

    // Sticky
    $('body').delegate(base_selector + ".sticky_post", "click", function(e) {
        var item = get_item(e);
        admin.sticky(item.data('comment_id'));
    });

    // Flag
    $('body').delegate(base_selector + ".hide_offensive", "click", function(e) {
        var item = get_item(e);
        canvas.api.flag_comment(item.data('comment_id'));
    });

    // Downvote
    $('body').delegate(base_selector + ".hide_comment", "click", function(e) {
        var item = get_item(e);
        canvas.api.hide_comment(item.data('comment_id'));
    });

    // Hide Thread
    $('body').delegate(base_selector + ".hide_thread", "click", function(e) {
        var item = get_item(e);
        canvas.api.hide_thread(item.data('thread_op_comment_id'));
        remove_items_with_matching_data('thread_op_comment_id', item);
    });

    // Unfollow User
    $('body').delegate(base_selector + ".hide_unfollow", "click", function(e) {
        var item = get_item(e);
        canvas.api.unfollow_user(item.data('author_id'));
        remove_items_with_matching_data('author_id', item);
    });

    // Unsubscribe followed Thread
    $('body').delegate(base_selector + ".hide_unfollow_thread", "click", function(e) {
        var item = get_item(e);
        canvas.api.unfollow_thread(item.data('thread_op_comment_id'));
        remove_items_with_matching_data('thread_op_comment_id', item);
    });
};

