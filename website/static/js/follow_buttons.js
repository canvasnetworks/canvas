canvas.wire_follow_buttons = function (base_selector) {
    if (typeof base_selector == 'undefined') {
        var base_selector = $(document);
    }

    var user_buttons = base_selector.find('.follow_user_toggle');

    user_buttons.each(function (_, button) {
        button = $(button);
        var user_profile_id = button.data('user_id');
        var initial_state = button.data('initial_state');

        new canvas.ToggleButton(button, {
            on_text             : 'Following',
            off_text            : 'Follow',
            off_action_text     : 'Unfollow',
            on_class            : 'js_already_following',
            off_class           : 'js_not_following',
            off_action_class    : 'js_unfollow',
            initial_state       : initial_state,
            toggle_callback     : function (state) {
                if (!current.logged_in) {
                    canvas.encourage_signup('follow_user');
                    return;
                }

                if (state) {
                    canvas.api.unfollow_user(user_profile_id);
                } else {
                    canvas.api.follow_user(user_profile_id);
                }
            },
        });
    });

    var topic_buttons = base_selector.find('.follow_topic_toggle');

    topic_buttons.each(function (_, button) {
        button = $(button);
        var topic_name = button.data('topic_name');
        var initial_state = button.data('initial_state');
        var show_name = button.data('show_name');

        new canvas.ToggleButton(button, {
            on_text             : 'Following',
            off_text            : 'Follow',
            off_action_text     : 'Unfollow',
            on_class            : 'js_already_following',
            off_class           : 'js_not_following',
            off_action_class    : 'js_unfollow',
            initial_state       : initial_state,
            toggle_callback     : function (state) {
                if (!current.logged_in) {
                    canvas.encourage_signup('follow_topic');
                    return;
                }

                if (state) {
                    canvas.api.unfollow_tag(topic_name);
                } else {
                    canvas.api.follow_tag(topic_name);
                }
            },
        });
    });

    var thread_buttons = base_selector.find('.follow_thread_toggle');

    thread_buttons.each(function (_, button) {
        button = $(button);
        var thread_id = button.data('thread_id');
        var initial_state = button.data('initial_state');

        new canvas.ToggleButton(button, {
            on_text             : 'Following',
            off_text            : 'Follow',
            off_action_text     : 'Unfollow',
            on_class            : 'js_already_following',
            off_class           : 'js_not_following',
            off_action_class    : 'js_unfollow',
            initial_state       : initial_state,
            toggle_callback     : function (state) {
                if (!current.logged_in) {
                    canvas.encourage_signup('follow_thread');
                    return;
                }

                if (state) {
                    canvas.api.unfollow_thread(thread_id);
                } else {
                    canvas.api.follow_thread(thread_id);
                }
            },
        });
    });

};

$(function () {
    canvas.wire_follow_buttons();
});

