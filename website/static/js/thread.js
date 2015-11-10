var thread = {
    last_timestamp: 0,
    replies: {},
    rendered_replies: {},
    unread: 0,
};

thread.get_replied_comment = function (id) {
    var replied = null;
    $.each(thread.reply_data, function (i, reply) {
        if (reply.id == id) {
            replied = new canvas.Comment(reply);
            return false;
        }
    });
    return replied;
};

thread.handle_comment = function (comment, selector) {
    post = $('.post_' + comment.id, selector);
    if (post.length > 1) {
        canvas.log('warning, .post_' + comment_id + " in " + selector + ' matched more than one element');
    }
    comment = new canvas.ThreadComment(thread, comment);
    thread.wire_comment(post, comment);
    canvas.format_comment_content(post, "column");
    if (selector === "#op") {
        // Special case handling of OP
        if (thread.user_infos.pinned) {
            stickers.add_pin_to_comment(thread.op_comment.id);
        }
        if (!post.is(".collapsed")) {
            thread.setupRemixSlider($("#op .slider_handle"));
        }
    }
    return post;
};

thread.wire_comment = function (rendered_comment, comment, options) {
    options = options || {};

    thread.rendered_replies[comment.id] = true;

    stickers.update_stickerable(rendered_comment, comment.id, comment.sticker_counts, comment.sorted_sticker_counts, comment.top_sticker);

    // Bind click if there is content
    if (comment.reply_content_id && (options.template != "comment_replied")) {
        $("a.content_expand:not(.audio_remix)", rendered_comment).bind("click", function () {
            thread.toggle_reply_content_size(rendered_comment, true);
            // load the tooltips just for this view.
            canvas.loadTooltips($(this));
            return false;
        });
        if (rendered_comment.hasClass("op")) {
            $("a.content_link", rendered_comment).bind("click", function () {
                if (comment.reply_content.original.animated) {
                    return true;
                }
                location.href = $(this).attr('data-footer-url');
                return false;
            });
        }
    }
    // Bind @ reply if needed
    var replied_link = rendered_comment.find("a.replied_link");
    if (replied_link.length) {
        var scroll_to_link = false;
        for (var i = 0; i < thread.standard_replies.length; i++) {
            if (thread.standard_replies[i].id == comment.replied_comment.id) {
                scroll_to_link = true;
                break;
            }
        }
        if (scroll_to_link) {
            replied_link.bind("click", function (e) {
                e.preventDefault();
                canvas.scrollToAndHighlight('.post_' + comment.replied_comment.id);
            });
        } else if (!comment.replied_comment.isUnviewable()){
            replied_link.attr("href", comment.replied_comment.getCommentURL());
        } else {
            replied_link.addClass("disabled");
        }
    }
    // Bind hover if there is @reply
    if (comment.replied_comment && (options.template != "comment_replied")) {
        var target_link = $("a.replied_link", rendered_comment);
        target_link.bind("mouseover", function () {
            $("#replied_comment").remove();
            var replied_comment = $('<div id="replied_comment"></div>');
            replied_comment.prependTo(rendered_comment);
            thread.render_and_append_comment(comment.replied_comment, $("#replied_comment"), {image_type: 'column', template: 'comment_replied'});
            replied_comment.css({
                left: target_link.position().left + target_link.width() + 40,
                top: target_link.offset().top - rendered_comment.offset().top + (target_link.height()/2) - (replied_comment.height()/2) - 5,
            });
            // Prevent replied comment from going offscreen vertically
            var top_of_screen = $(window).scrollTop() + $("nav").outerHeight() + 10;
            var bottom_of_screen = $(window).scrollTop() + $(window).height() - replied_comment.outerHeight() - 10;
            if (replied_comment.offset().top < top_of_screen) {
                replied_comment.css("top", top_of_screen - rendered_comment.offset().top);
            } else if (replied_comment.offset().top > bottom_of_screen) {
                replied_comment.css("top", bottom_of_screen - rendered_comment.offset().top);
            }
            var arrow = $(".arrow", rendered_comment);
            arrow.css("top", Math.min(replied_comment.outerHeight() - arrow.height() + 8, Math.max(0, target_link.offset().top - replied_comment.offset().top - (arrow.height()/2) + (target_link.height()/2))));

            // If the image isn't visible, check to see if the user made it visible and then show it
            if (comment.replied_comment.isCollapsed()) {
                canvas.log($(".post_" + comment.replied_comment.id).hasClass("collapsed"));
                if (!$(".post_" + comment.replied_comment.id).hasClass("collapsed")) {
                    // Make this a little more elegant in CSS
                    replied_comment.children(".image_tile").removeClass("collapsed");
                    replied_comment.find(".replied_collapsed_text").addClass("hidden");
                }
            }

            // Now fade it in
            replied_comment.animate({opacity:1}, 300);
        }).bind("mouseout", function () {
            $("#replied_comment").stop().animate({opacity:0}, 100, function () {
                $(this).remove();
            });
        });
    }
};

// We're still using this just for hover comments.
thread.render_and_append_comment = function (comment_data, parent, options) {
    var comment = new canvas.ThreadComment(thread, comment_data);
    var rendered_comment = $(comment.render(options));
    $(parent).append(rendered_comment);
    if (comment.reply_content_id) {
        canvas.format_comment_content(rendered_comment, options.image_type);
    }

    thread.wire_comment(rendered_comment, comment, options);
    return rendered_comment;
};

thread.render_and_append_reply_data = function (selector, comment, allowDupe) {
    selector = selector || "#comments .wrapper";
    // The area it is going into may be hidden, such as for a thread with no previous replies, so show it.
    $(selector).parent().removeClass("hidden");
    if (allowDupe || !thread.rendered_replies[comment.id]) {
        var element = thread.render_and_append_comment(comment, selector, {image_type: 'column', template: 'comment'});
        if (thread.expanded_view) {
            thread.expandReplyImage(element, false);
        }
    }
};

thread.fetch_new_replies = function () {
    $('.more_posts').removeClass('shown');
    document.title = "Canvas";
    canvas.apiPOST(
        '/comment/replies',
        {
            comment_id: thread.op_comment.id,
            replies_after_timestamp: thread.last_timestamp,
        },
        function (response) {
            thread.reply_data = thread.reply_data.concat(response.replies);
            $.map(response.replies, function (element, index) {
                thread.render_and_append_reply_data('#thread_column .new_replies', element);
            });
            thread.unread = 0;
            thread.disable_realtime = false;
        }
    );
};

thread.wire_sidebar = function () {
    var rendered_comment = $('.group_op_sidebar .parent_image');
    var comment = new canvas.ThreadComment(thread, thread.op_comment);
    if (comment.reply_content_id) {
        canvas.format_comment_content(rendered_comment, 'small_column');
    }
    thread.wire_comment(rendered_comment, comment, {image_type: 'small_column', template: 'comment_sidebar'});
};

thread.setupRemixSlider = function (handle) {
    // Check for padding first
    var remix_parent = handle.siblings(".remix_parent").children("img");
    if (remix_parent.length) {
        var remix_child = handle.parents(".reply").find(".comment-image");
        var parent_content = canvas.getContent(remix_parent.attr("id"));
        remix_parent.css({
            top: parseInt(remix_child.parent().css("padding-top")),
            right: Math.floor((handle.parent().width() - remix_child.width())/2),
            width: remix_child.width(),
            height: remix_child.height()
        });
        var data = null;
        handle.mobileDrag({
            easyDrag: false,
            constrainX: [handle.parent().width(), 0],
            constrainY: [0, 0],
            drag: function () {
                data = handle.data("mobileDrag");
            },
            move: function () {
                remix_parent.parent().css("width", data.originalPos.left - data.currentPos.left + 1 + "px");
            }
        });
    }
};

thread.toggle_reply_content_size = function (ctx, animate_bool, is_expanding) {
    if (!ctx.is(".transforming")) {
        if (is_expanding === undefined && !ctx.hasClass("expanded")) {
            is_expanding = true;
        }
        if (is_expanding) {
            ctx.addClass("expanded");
            if (ctx.hasClass("stickered")) {
                ctx.addClass("sticker_themed");
            }
        } else {
            ctx.removeClass("expanded");
            ctx.removeClass("sticker_themed");
        }
        var target_image = $(".comment-image", ctx);
        var content = canvas.getContent(target_image.attr("id"));
        var new_img_url = content.column.url;
        if (is_expanding) {
            new_img_url = (content.original.animated) ? content.ugc_original.url : content.giant.url;
            if (ctx.is(".unthemed.stickered")) {
                ctx.removeClass("unthemed").addClass("unthemed_expanded");
            }
        } else {
            if (ctx.hasClass("unthemed_expanded")) {
                ctx.addClass("unthemed").removeClass("unthemed_expanded");
            }
        }
        var desired_width = (is_expanding) ? 600 : 250;
        var speed = 300;
        var ease_type = "swing";
        var new_img_width = (is_expanding) ? content.giant.width : content.column.width;
        var new_img_height = (is_expanding) ? content.giant.height : content.column.height;
        var new_padding = 0;
        var formatting = canvas.get_content_formatting($(".image_container", ctx), {
            "img_width": new_img_width,
            "img_height": new_img_height,
            "container_width": desired_width,
        });
        new_img_width = formatting.img_width;
        new_img_height = formatting.img_height;
        new_padding = formatting.container_padding;
        if (new_padding) {
            target_image.addClass("small_image");
        } else {
            target_image.removeClass("small_image");
        }

        if (animate_bool) {
            var reply_content = $(".reply_content", ctx);
            ctx.addClass("transforming");
            // Preload full size image
            $('<img>').attr('src', new_img_url).load(function (){
                target_image.attr("src", new_img_url);
            });
            if (new_padding != parseInt($(".image_container", ctx).css("padding-top"))) {
                $(".image_container", ctx).animate({paddingTop:new_padding, paddingBottom:new_padding}, speed, ease_type);
            }
            target_image.animate({width:new_img_width, height:new_img_height}, speed, ease_type);
            reply_content.animate({width:desired_width}, speed, ease_type, function () {
                // jQuery 1.5 can't clean up after itself regarding overflows, causing the remix slider to be hidden
                // when expanding remixes.
                ctx.removeClass("transforming");
                $(this).css('overflow-x', '').css('overflow-y', '');
                if (is_expanding) {
                    thread.setupRemixSlider($(".slider_handle", ctx));
                }
                ctx.removeAttr("margin");
            });
        } else {
            if (new_padding != parseInt($(".image_container", ctx).css("padding-top"))) {
                $(".image_container", ctx).css({paddingTop:new_padding, paddingBottom:new_padding});
            }
            target_image.attr("src", new_img_url).css({width:new_img_width, height:new_img_height});
            $(".reply_content", ctx).css({width:desired_width});
            if (is_expanding) {
                thread.setupRemixSlider($(".slider_handle", ctx));
            }
        }
    }
};

thread.reply_is_expanded = function (target) {
    var target = $(target);
    if (!target.hasClass("reply")) {
        target = target.parents(".reply");
    }
    return target.hasClass("expanded");
};

thread.wire = function () {
    var replies_to_handle = thread.replies_to_handle;
    var url_action = thread.url_action;
    var page_current = thread.page_current;
    var page_last = thread.page_last;
    var gotoreply = thread.gotoreply;
    var draw_from_scratch_content = thread.draw_from_scratch_content;

    // Allow for different behaviors if going to page 1, or specifically OP
    var goto_op = (page_current == 1 && window.location.pathname.substr(window.location.pathname.length-2, 2) != "/1") ? true : false;

    thread.wire_sidebar();
    canvas.wire_invite_remixers();

    // Parse URL hash and query into actions
    if (gotoreply) {
        url_action = 'scroll_highlight';
    }
    if (document.location.hash) {
        var hash = document.location.hash.substr(1);
        if (hash.match(/re+mix/)) {
            // Go straight to remix with URL#remix
            url_action = 'remix';
        }
        if (hash.match(/audio_remix/)) {
            url_action = 'audio_remix';
        }
        if (hash.match(/reply/)) {
            // Go to reply widget for @reply
            url_action = 'reply';
        }
    }

    // Push replies to render.
    replies_to_handle.push(['#op', thread.op_comment]);
    $.each(thread.top_replies, function (i, reply) {
        replies_to_handle.push(['#top_replies .wrapper', reply]);
    });
    $.each(thread.standard_replies, function (i, reply) {
        replies_to_handle.push(['#comments .wrapper', reply]);
    });
    $.each(thread.recent_replies, function (i, reply) {
        replies_to_handle.push(['#recent_replies .wrapper', reply]);
    });
    // Handle replies.
    $.each(replies_to_handle, function () {
        var tuple = replies_to_handle.shift();
        var selector = tuple[0];
        var reply = tuple[1];
        thread.handle_comment(reply, selector);
    });

    $(".remix_link:not(.disabled)").tooltip({
        content : "Edit this picture to make your own version.",
        delegate: $("body"),
    });
    $(".remix_link.disabled").tooltip({
        content : "Remixing has been disabled in this group.",
        delegate: $("body"),
    });
    $(".icon_reply").tooltip({
        content : "Reply to this post.",
        delegate: $("body"),
    });

    if (thread.large_thread_view) {
        // Watch for user to get to the bottom of the thread
        $(window).bind("scroll.metric_watch", function () {
            var win = $(window);
            var col = $("#thread_column");
            if (win.scrollTop() + win.height() >= col.offset().top + col.height()) {
                canvas.record_metric("scrolled_to_bottom");
                win.unbind("scroll.metric_watch");
            }
        });
    }

    thread.image_chooser = new canvas.ImageChooser($('.pw_container .image_chooser'));
    var submit_button = $('.pw_container input[type=submit]');

    var remixer_open = function () {
        return $('.remix_widget').is(':visible');
    };
    var update_submit_button_state = function (ignore_remixer) {
        submit_button.attr('disabled', !($('#postwidget_caption').val() || (!ignore_remixer && remixer_open())));
    };

    if (url_action === 'remix') {
        thread.image_chooser.hide();
    }

    update_submit_button_state();
    var pw = thread.pw = new Postwidget({
        container: '#postwidget',
        is_reply: true,
        bind_type: 'column',
        default_text: '',
        submit_text: 'Post reply',
        parent_comment: thread.op_comment,
        skip_to_remix: true,
        pre_submit_callback: function () {
            // Don't show anymore new post notifications, so we don't see our own post.
            thread.disable_realtime = true;
        },
        post_submit_callback: function (post, response) {
            if (!post.reply_content) {
                // Temp hack, postwidget.js should own resetting the post widget, obv.
                this.scoped(".reply_addendum").css({opacity: 0});
                this.scoped(".pw_text").focus();
                this.reply_comment_id = null;
                thread.fetch_new_replies();
                return false;
            }
            return true;
        },
    });

    pw.wire_uploadify();

    thread.image_chooser.url_input_button.click(function (event) {
        pw.upload_url(thread.image_chooser.url_input_field.val());
        event.preventDefault();
    });

    thread.image_chooser.start_from.draw.click(function () {
        action.remix(draw_from_scratch_content.id, 'draw');
        pw.remix_started();
        pw.wire_uploadify();
    });

    $(pw.container).bind('closing', function () {
        thread.image_chooser.show();
        update_submit_button_state(true);
    });

    $('#postwidget_caption').keyup(function () {
        update_submit_button_state();
    });

    thread.remixer = new remix.RemixWidget(pw, $(".remix_widget"));
    thread.remixer.install_actions();

    local.wire();
    // Handle URL actions.
    if (url_action) {
        // Allowing linking directly to remix. Sorry, reeemix.
        if (url_action === 'remix') {
            var remix_id;
            if (gotoreply) {
                $.each(thread.standard_replies, function (i, comment) {
                    if (comment.id == gotoreply) {
                        remix_id = comment.reply_content.id;
                    }
                });
            } else {
                remix_id = thread.op_comment.reply_content.id;
            }

            if (remix_id) {
                var source = '';
                var hash = document.location.hash.substr(1);
                if (hash === 'remix_sticker') {
                    // Make sure to record remix sticker info
                    source = 'sticker';
                } else if (hash === 'remix') {
                    source = 'tile_hover_ui';
                } else if (hash === 'remix_reposted') {
                    source = 'repost_ui';
                }
                action.remix(remix_id, source);
                thread.pw.remix_started();
            }
        // Scroll to and highlight the comment specified.
        } else if (url_action === 'scroll_highlight' && gotoreply) {
            post = $($(".post_" + gotoreply)[0]);
            if (post.is(".has_content")) {
                canvas.unhide_collapsed_post(post);
                var comment = canvas.getComment(gotoreply);
                // Either play it if it's an audio remix, or just resize it
                if (comment && comment.has_audio_remix()) {
                    canvas.play_audio_remix(comment);
                } else {
                    thread.toggle_reply_content_size(post, false, true);
                }
            }
            canvas.scrollToAndHighlight('.post_' + gotoreply, false, true);
        // Go to reply widget for reply hash
        } else if (url_action === 'reply') {
            var reply_id;
            if (gotoreply) {
                $.each(thread.standard_replies, function (i, comment) {
                    if (comment.id == gotoreply) {
                        reply_id = comment.id;
                    }
                });
            } else {
                reply_id = thread.op_comment.id;
            }
            action.reply(reply_id);
        }
    } else if (page_current && !goto_op) {
        $.scrollTo($("#comments").offset().top - $("#header .top_bar").outerHeight(true) - 10, 500);
    }

    if (thread.admin_infos) {
        admin.update_status({ info: thread.admin_infos[thread.op_comment.id] });
    }

    $('.more_posts').bind('click', function (event) {
        thread.fetch_new_replies();
        event.preventDefault();
    });

    if (!thread.op_comment.moderated && $('#related_column').length) {
        // Scroll OP to always be at top
        var op_padding = $("nav").outerHeight() + 15,
            op_sidebar = $("#related_column .group_op_sidebar"),
            op_offset = op_sidebar.offset().top,
            op_position = op_sidebar.position().top,
            op_visible = true;

        $(window).bind("scroll", function () {
            // Hide or show the OP in sidebar depending on if it's visible on screen
            if ($(window).scrollTop() > $("#op").offset().top + $("#op .comment-image").height()) {
                if (op_visible == true) {
                    op_sidebar.removeClass("hidden");
                    op_sidebar.css("display", "block").animate({opacity:1}, 200);
                }
                op_visible = false;
            } else if ($(window).scrollTop() <= $("#op").offset().top + $("#op .comment-image").height()) {
                if (op_visible == false) {
                    op_sidebar.animate({ opacity: 0 }, 200, function () {
                        op_sidebar.addClass("hidden");
                    });
                }
                op_visible = true;
            }
            // Scroll the OP
            if (op_visible == false) {
                if ($(window).scrollTop() + op_sidebar.outerHeight(true) + op_padding >= ($("#sticker_column_border").offset().top + $("#sticker_column_border").height())) {
                   op_sidebar.css({position:"absolute", top:$("#sticker_column_border").height() - op_sidebar.outerHeight(true) + "px", left:0});
                } else {
                    if (current.is_mobile) {
                        op_sidebar.css({position:"absolute", top:op_padding + $(window).scrollTop() - op_sidebar.offset().top, bottom:"auto", left:0});
                    } else {
                        op_sidebar.css({position:"fixed", top:op_padding, left:op_sidebar.parent().offset().left - $(window).scrollLeft()});
                    }
                }
            }
        });

        // Handle remix links when remix is disabled in the comment's group.
        $(".remix_link.disabled").tooltip({
            content:"Remixing has been disabled in this group by the founder.",
            delegate:$("body")}
        );
    }

    if ($('.op_share_thread').length) {
        thread.op_share_thread = new canvas.ShareThreadWidget($('.op_share_thread'), thread.op_comment.id);
    } else {
        thread.invite_remixers_1 = new canvas.ShareThreadWidget($($('.invite_remixers')[0]), thread.op_comment.id);
        thread.invite_remixers_2 = new canvas.ShareThreadWidget($($('.invite_remixers')[1]), thread.op_comment.id);
    }
};

thread.on_load = function () {
    var replies_channel = thread.replies_channel;
    realtime.subscribe(replies_channel, function (messages) {
        if (thread.disable_realtime) {
            return;
        }

        $.each(messages, function (i, reply) {
            if (!thread.replies[reply.comment_id]) {
                thread.replies[reply.comment_id] = true;
                if (reply.timestamp > replies_channel.timestamp) {
                    // Ignore ghost messages, maybe from a moderated comment.
                    thread.unread += 1;
                }
            }
        });
        if (thread.unread) {
            var more = $('.more_posts'),
                text = "Click to show " + thread.unread + " new " + "post".pluralize(thread.unread, null, false);

            if (!more.hasClass('shown')) {
                more.css('opacity', 0).addClass('shown');
                more.text(text);
                more.animate({'opacity': 1}, 1500);
            } else {
                more.text(text);
            }

            document.title = "(" + thread.unread + ") Canvas";
        }
    });
    canvas.base_onload();
};

