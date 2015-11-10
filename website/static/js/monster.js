var monster = {};

monster.current_index = 0;

monster.remixer = null;

monster.wire = function () {
    var is_reply = ! (typeof monster.main_comment === "undefined");

    var default_title = "Drawing top half";
    var submit_text = "Save & Invite";

    if (is_reply) {
        default_title = "Drawing bottom half";
        submit_text = "It's Alive!";
    }

    var pw = new Postwidget({
        container: '.remix_wrapper',
        bind_type: 'column',
        default_text: 'Write something!',
        submit_text: submit_text,
        skip_to_remix: true,
        show_options_section: false,
        show_caption: false,
        parent_comment: monster.main_comment,
        is_reply: is_reply,
        default_title: default_title,
        post_submit_callback: function(post, response) {
            if(is_reply) {
                comment = new canvas.Comment(response.comment);
                var url = "/monster/" + comment.parent_url.split('/')[2];
                window.location = url;
                return false;
            } else {
                comment = new canvas.Comment(response.comment);
                var url = "/monster/" + comment.short_id;
                window.location = url;
                return false;
            }
        },
    });

    var remixer = monster.remixer = new remix.RemixWidget(pw, $('.remix_widget'));
    remixer.scroll_to = function () {};
    remixer.install_actions();
    $('#postwidget div.image_chooser').hide();
    action.remix(monster.monster_start_content.id, 'draw');
};

monster.share_monster = function (type_id, comment_id, reply_id) {
    var name = current.stickers[type_id].name;
    var prefix = "http://example.com";
    var comment_url = "/monster/" + comment_id + "/" + reply_id;
    jQuery.ajax({
        type: "POST",
        contentType: 'application/json',
        data: JSON.stringify({url: comment_url, channel: name}),
        url: '/api/share/create',
        async: false, // If we try to open the popup outside of a mouseclick, it will fail.
        success: function (response) {
            var origin = 'share_monster';
            canvas.record_metric('share', { share_url: comment_url, origin: origin, share: response.share_id });
            canvas.record_metric(name, { share_url: comment_url, origin: origin, share: response.share_id });

            var url = prefix + comment_url;

            if (name == 'facebook') {
                var params = $.parseParams(response.share_get_arg);
                if (comment_url.indexOf('?') !== -1) {
                    $.extend(params, $.parseParams(comment_url));
                    params = $.parseParams(comment_url);
                }
                var args = {
                    link: url + "?" + $.param(params),
                    redirect_uri: "http://example.com/static/html/close_popup.html",
                    app_id: "176245562391022",
                    display: "popup",
                    name: monster.monster_name,
                    description: "View more monsters and create your own on Monster Mash, a Canvas game!",
                };
                window.open("https://www.facebook.com/dialog/feed?" + $.param(args), "facebook_share", "width=600, height=300");
            } else if (name == 'twitter') {
                var tweet = "Check out " + monster.monster_name + ", created on Monster Mash via @canv_as! " + encodeURI(url);
                window.open('http://twitter.com/intent/tweet?text=' + encodeURIComponent(tweet), "twitter_share", "width=600, height=400");
            } else if (name == 'email') {
                var subj = "Check out " + monster.monster_name;
                var body = "View more monsters and create your own on Monster Mash, a Canvas game!%0A%0A" + encodeURI(url);
                window.location.href='mailto:?subject=' + subj + '&body=' + body;
            }
        },
    });
};

monster.share_monster_invite = function (type_id, comment_id) {
    var name = current.stickers[type_id].name;
    var prefix = "http://example.com";
    var comment_url = "/monster/" + comment_id + "/complete";
    jQuery.ajax({
        type: "POST",
        contentType: 'application/json',
        data: JSON.stringify({url: comment_url, channel: name}),
        url: '/api/share/create',
        async: false, // If we try to open the popup outside of a mouseclick, it will fail.
        success: function (response) {
            var origin = 'invite_monster_remixer';
            canvas.record_metric('share', { share_url: comment_url, origin: origin, share: response.share_id });
            canvas.record_metric(name, { share_url: comment_url, origin: origin, share: response.share_id });

            var url = prefix + comment_url;
            var subj = "Come make a monster with me";
            var tweet = "I've created a monster, now I need you to finish it! " + encodeURI(url) + " via @canv_as";

            if (name == 'facebook') {
                var params = $.parseParams(response.share_get_arg);
                if (comment_url.indexOf('?') !== -1) {
                    $.extend(params, $.parseParams(comment_url));
                    params = $.parseParams(comment_url);
                }
                var body = "I've created a monster, now I need you to finish it! " +
                           "Click the link to draw the bottom half of the monster " +
                           "I've started. Once you submit it, we'll find out what we've created!";
                var args = {
                    link: prefix + comment_url.split('?')[0] + "?" + $.param(params),
                    redirect_uri: "http://example.com/static/html/close_popup.html",
                    app_id: "176245562391022",
                    display: "popup",
                    name: subj,
                    description: body,
                };
                window.open("https://www.facebook.com/dialog/feed?" + $.param(args), "facebook_share", "width=600, height=300");
            } else if (name == 'twitter') {
                window.open('http://twitter.com/intent/tweet?text=' + encodeURIComponent(tweet), "twitter_share", "width=600, height=400");
            } else if (name == 'email') {
                var body = "I've created a monster, now I need you to finish it! %0A%0A" + encodeURI(url) +
                           "%0A%0AClick the link to draw the bottom half of the monster " +
                           "I've started. Once you submit it, we'll find out what we've created!";
                window.location.href='mailto:?subject=' + subj + '&body=' + body;
            }
        },
    });
};

monster.wire_keys = function () {
    $(document).keydown(function(event) {
        if (event.keyCode == 37) {
            monster.previous();
        } else if (event.keyCode == 39) {
            monster.next();
        }
    });
};

monster.next = function () {
    var replies = $('.replies');
    $(replies.children()[monster.current_index]).hide();
    monster.current_index++;
    if (monster.current_index >= replies.children().length) {
        monster.current_index = 0;
    }
    $(replies.children()[monster.current_index]).show();
};

monster.previous = function () {
    var replies = $('.replies');
    $(replies.children()[monster.current_index]).hide();
    monster.current_index--;
    if (monster.current_index == -1) {
        monster.current_index = replies.children().length - 1;
    }
    $(replies.children()[monster.current_index]).show();
};

monster.remove_context_menus = function() {
    $("body").undelegate(".composite_image", "contextmenu");
};

monster.content_context_menu = function () {
    $("body").delegate(".composite_image", "contextmenu", function (e) {
        var downloadify_url = function (ugc_url) {
            return ugc_url.replace('/ugc/','/ugc_download/');
        };

        var container = $(this);
        var parent_node = container.parents(".reply");
        if (!parent_node.length) {
            parent_node = container.parents(".image_tile");
        }
        if (!parent_node.length) {
            parent_node = container.parents('.explore_tile');
        }
        var details = parent_node.data('details');

        var get_url = function (content) {
            if (content.footer) {
                return content.footer.name;
            } else {
                return content.ugc_original.name;
            }
        }
        var footer_url = get_url(details.reply_content);

        var new_context = (canvas.user_agent.browser_name == "Safari") ? "Window" : "Tab";
        var menu_options = [
            {
                text    : "Open Image in New " + new_context,
                action  : function () {
                    window.open(footer_url, "_blank");
                }
            },
            {
                text    : "Save Image...",
                action  : function () {
                    window.open(footer_url, "_blank");
                }
            },
        ];

        if (container.hasClass("image_tile")) {
            menu_options.unshift({
                text    : "Open Monster in New " + new_context,
                action  : function () {
                    var url = $(".content_link", container).attr("href");
                    window.open(url, "_blank");
                }
            });
        }

        return canvas.show_context_menu(e, menu_options);
    });
};
