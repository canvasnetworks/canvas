sticker_actions = {};

sticker_actions.perform = function (drag, drop, comment_id, type_id) {
    realtime.unpause_updates();
    // Grab the sticker dictionary
    // This has the same attributes as the Sticker model.
    var sticker = current.stickers[type_id];

    drag.mobileDrag('makeUndraggable').addClass("absolute");
    var action_call = function () {
        type = current.stickers[type_id].name;
        if (type == "downvote_action") {
            type = "downvote";
        }
        // Give some feedback and make sure the sticker can't still be dragged.
        var spinner = $('<div class="sticker_spinner"></div>').prependTo(drag);
        return canvas.api[type + "_comment"](comment_id, type_id)
            .done(function(response) {
                spinner.remove();
                sticker_actions.on_drop_success(drag, drop, comment_id, type_id, response);
            }).fail(function(response) {
                if (response.reason === 403) {
                    this.stop_propagation = true;
                    canvas.record_metric('sticker_attempt', {type_id: type_id});
                    canvas.encourage_signup("sticker", {type_id: type_id});
                }
                spinner.remove();
                sticker_actions.on_drop_failure(drag, drop, comment_id, type_id, response);
            });
    };

    // Flag / downvote / pin / repost
    if (type_id == 3001 || type_id == 3002 || type_id == 3003 || type_id == 3006) {
        action_call();
    // Admin only action?
    } else if (sticker.admin_only) {
        admin.on_admin_sticker_drop(drag, drop, comment_id, type_id);
    // Sharing.
    } else if (type_id >= 2000 && type_id < 3000) {
        //TODO dead code? kill.
        stickers.end_drag(drag);
        var is_expanded = (window.thread) ? thread.reply_is_expanded(drop) : false;
        sticker_actions.share_comment(type_id, comment_id, is_expanded);
    // Founder off-topic.
    } else if (sticker.name == "offtopic") {
        sticker_actions.mark_offtopic(drag, drop, comment_id);
    } else {
        throw 'Unknown action type: ' + type_id;
    }
};

sticker_actions.share_comment = function (type_id, comment_id, is_expanded, origin) {
    origin = typeof origin === 'undefined' ? null : origin;
    var name = current.stickers[type_id].name;
    var comment = canvas.getComment(comment_id);
    var prefix = "http://example.com";
    var img_url = (comment.reply_content.original.animated) ? comment.reply_content.ugc_original.url : comment.reply_content.giant.url;
    var comment_url = comment.share_page_url;
    var invite_remixer_origin = 'invite_remixers';
    var invite_remixer_url_input = $('.invite_remixers .arbitrary input.invite_url');
    var invite_remixer_url;

    var share_callback = function (url, share_get_arg, share_id) {
        canvas.record_metric('share', { is_expanded: is_expanded, share_url: comment_url, origin: origin, share: share_id });
        canvas.record_metric(name, { is_expanded: is_expanded, share_url: comment_url, origin: origin, share: share_id });

        if (name == 'facebook') {
            var params = $.parseParams(share_get_arg);
            if (comment_url.indexOf('?') !== -1) {
                $.extend(params, $.parseParams(comment_url));
                params = $.parseParams(comment_url);
            }

            var args = {
                link: prefix + comment_url.split('?')[0] + "?" + $.param(params),
                redirect_uri: "http://example.com/static/html/close_popup.html",
                app_id: "176245562391022",
                display: "popup",
            };

            if (comment.reply_content) {
                args.source = comment.reply_content.ugc_original.url.replace(/https/, "http");
            }

            if (origin === invite_remixer_origin) {
                args.name = "Come Remix With Me!";
                if (comment.title) {
                    args.description = "I just started a thread on Canvas, \"" + comment.title + "\". Click the link to add your remix to the thread!";
                } else {
                    args.description = "I just started a thread on Canvas. Click the link to add your remix to the thread!";
                }

                FB.ui({
                        method: 'apprequests',
                        message: args.description,
                        data: args.link,
                    },
                    function (resp) {
                        if (resp && resp.to.length) {
                            canvas.record_metric('invite_facebook_friends_to_remix', {
                                friends_invited: resp.to.length,
                                user_id: current.user_id,
                            });
                        }
                    }
                );
            } else {
                window.open("https://www.facebook.com/dialog/feed?" + $.param(args), "facebook_share", "width=600, height=300");
            }
        } else if (name === 'twitter') {
            var max_char = 140;
            var message = "Remix this image";

            if (origin === invite_remixer_origin) {
                if (comment.title) {
                    part1 = "I just started a thread, \"";
                    part2 = "\". " + url + " Come remix with me! via @canv_as";
                    title = comment.title;
                    title_max = max_char - part1.length - part2.length;
                    if (title.length > title_max) {
                        title = title.substr(0, title_max - 2);
                        title += "…\""
                    }
                    message = part1 + title + part2;
                } else {
                    message = "I just started a thread. " + url + " Come remix with me! via @canv_as";
                }
            } else {
                if (comment.title) {
                    message = comment.title;
                } else if (comment.reply_text) {
                    message = comment.reply_text;
                } else if (comment.reply_content.remix_text) {
                    message = canvas.remove_line_breaks(comment.reply_content.remix_text);
                }
                var max_char = 140;
                /* The old Twitter posting interface we use does not truncate URLs.
                var url_length = 19; // https://support.twitter.com/articles/78124
                */
                var callout = (comment.reply_text) ? "via @canv_as" : "on @canv_as";
                var message_max = max_char - 1 - url.length - 1 - callout.length; // -1s to allow for white space
                if (message.length > message_max) {
                    message = message.substr(0, message_max - 2);
                    message += "…"
                }
                message = message + " " + url + " " + callout;
            }

            window.open('http://twitter.com/intent/tweet?text=' + encodeURIComponent(message), "twitter_share", "width=600, height=400");
        } else if (name === 'stumbleupon') {
            window.open('http://www.stumbleupon.com/submit?url=' + encodeURI(url), "stumbleupon_share", "width=1050, height=450");
        } else if (name === 'tumblr') {
            var line_break = (comment.reply_text) ? "<br><br>" : "";
            var message = tmpl.ugc_text(comment.reply_text, 140, false, true);
            if (comment.title) {
                message = comment.title + " - ";
            }
            window.open('http://www.tumblr.com/share/photo?source=' + encodeURIComponent(img_url + "?tumblr") + '&clickthru=' + encodeURIComponent(url) + '&caption=' + encodeURIComponent(message) + encodeURIComponent(line_break + "Remix this image on <a href=\"" + url + "\">" + url + "</a>."), "tumblr_share", "width=450, height=400");
        } else if (name === 'reddit') {
            window.open('http://www.reddit.com/submit?url=' + encodeURI(url) + '&title=', "reddit_share", "width=875, height=725");
        } else if (name === 'email') {
            if (origin == invite_remixer_origin) {
                subject = "Come remix with me!";
                if (comment.title) {
                    body = "I just started a thread on Canvas, \"" + comment.title + "\". " + encodeURI(url) + " Come remix with me!";
                } else {
                    body = "I just started a thread on Canvas. " + encodeURI(url) + " Come remix with me!";
                }
            } else {
                subject = "Check out this image on Canvas";
                body = "Check out this image: " + encodeURI(url);
            }
            window.location.href='mailto:?subject=' + subject + '&body=' + body;
        }
    };

    if (origin === invite_remixer_origin) {
        canvas.api.invite_url({comment_id: comment_id}).done(function (response) {
            share_callback(response.invite_url, response.invite_get_arg);
        });
    } else {
        $.ajax({
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({url: comment_url, channel: name}),
            url: '/api/share/create',
            async: false, // If we try to open the popup outside of a mouseclick, it will fail.
            success: function (response) {
                share_callback(prefix + response.share_url, response.share_get_arg, response.share_id);
            },
        });
    }
};

sticker_actions.unflag = function (target, flag_id) {
    return canvas.apiPOST(
        '/comment/unflag',
        {'flag_id': flag_id},
        function (response) {
            var message = response.success ? 'Post successfully unflagged.<br/>Thanks for your attention to detail!' : 'An error has occurred.';
            stickers.overlay_message(target, message, 5000);
        }
    );
};

sticker_actions.mark_offtopic = function (drag, drop, comment_id) {
    return canvas.apiPOST(
        '/comment/mark_offtopic',
        {'comment_id': comment_id, 'ot_hidden': true },
        function (response) {
            var message = response.success ? 'Post succesfully marked offtopic. <a href="#" id="undo_offtopic_' + comment_id + '">Undo</a>.' : response.reason;
            stickers.end_drag(drag);
            stickers.overlay_message(drop, message);
            $('#undo_offtopic_' + comment_id).bind('click', function (event) {
                event.preventDefault();
                sticker_actions.undo_mark_offtopic(drop, comment_id);
            });
        }
    )
};

sticker_actions.undo_mark_offtopic = function (drop, comment_id) {
    return canvas.apiPOST(
        '/comment/mark_offtopic',
        {'comment_id': comment_id, 'ot_hidden': false },
        function (response) {
            var message = response.success ? 'Post no longer marked offtopic.' : response.reason;
            stickers.overlay_message(drop, message);
        }
    )
};

sticker_actions.on_drop_success = function (drag, drop, comment_id, type_id, response) {
    var flag_id = response.flag_id,
        unflag_id = 'unflag_' + flag_id,
        flag_name = current.stickers[type_id].name;

    stickers.end_drag(drag);

    if (type_id == 3001) {
        stickers.overlay_message(drop, 'This post has been flagged. Thanks for letting us know; we\'ll take a peek!<br/><a class="overlay_link" id="' + unflag_id + '" href="#">Undo flag</a>');
        $('a#' + unflag_id).click(function () {
            sticker_actions.unflag(drop, flag_id);
        });
    } else if (type_id == 3002) {
        stickers.overlay_message(drop, 'This post has been successfully downvoted.', 3000);
    } else if (type_id == 3003) {
        stickers.add_pin_to_comment(comment_id).find('.pin').css({opacity: 0}).animate({opacity: 1}, 1000);
        stickers.overlay_message(drop, 'This thread has been successfully pinned. New replies will appear in the Pinned tab.', 5000);
    } else if (type_id == 3006) {
        stickers.overlay_message(drop, 'Thanks for letting us know, in the future we\'ll attempt to use this data to hide things you\'ve likely seen before.', 5000);
    } else {
        throw 'Unknown success type: ' + type_id;
    }
};

sticker_actions.on_drop_failure = function (drag, drop, comment_id, type_id, response) {
    var message = null;
    stickers.end_drag(drag);

    if (response.reason == "Already flagged.") {
        message = "You've already flagged this post. Thanks!";
    } else if (response.reason == "No self stickering.") {
        message = "Nice try. You're not allowed to vote on your own posts.";
    } else if (response.reason == "Already stickered.") {
        message = "You've already voted on this post.";
    } else if (response.reason != 403) {
        throw response.reason;
    }

    stickers.overlay_message(drop, message, 2000);
};

sticker_actions.wire = function () {
};

