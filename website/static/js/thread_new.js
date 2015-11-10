window.thread_new = {
    last_timestamp  : 0,
    unread          : 0,
    replies         : {},
    replies_on_page : {},
    realtime_replies: {},
};

thread_new.scroll_to_post_update_url = function (post_node) {
    var anchor = $(post_node.children("a.goto_anchor")[0]);
    var id = anchor.attr("name");
    var new_url = thread_new.base_url + "reply/" + id

    // Check if this is the OP
    if (post_node.data('comment_id') == thread_new.op_comment.id) {
        new_url = thread_new.op_comment.url;
    }

    // Scroll to the anchor tag
    $(window).scrollTop(anchor.offset().top);
    // Now we also want to update the url (which will also remove the hash)
    window.history.replaceState({}, "", new_url);
};

thread_new.goto_post = function (post_url) {
    var url_split = post_url.split('/');
    var post_id = url_split[url_split.length - 1];
    var op_id = thread_new.op_comment.url.split('/');
    op_id = op_id[op_id.length - 1];
    if (post_id == op_id) {
        thread_new.focus_post($('#content .thread_op .thread_comment'));
        return;
    }
    if (thread_new.replies_on_page[post_id]) {
        var post_node = $('#content .thread_posts li[data-comment_id = ' + post_id + ']');
        if (post_node.length) {
            thread_new.focus_post(post_node);
            return;
        }
    }
};

thread_new.get_next_reply_with_content = function (dir) {
    var current = $('li.current');
    var next_node = current[dir]();
    if (!next_node.length && dir == "next" && (!current.length || current.parents(".thread_op").length)) {
        // Assume we're at the op and jumping into replies
        next_node = $('#content section.replies li.thread_comment:first-of-type');
    }
    while (thread_new.is_content_on_page && next_node.length && (next_node.hasClass("text_only") || next_node.hasClass("collapsed"))) {
        next_node = next_node[dir]();
    }
    if (next_node.length) {
        return next_node;
    }
    return false;
};

thread_new.focus_post = function (post_node) {
    $('#content li.current').removeClass("current");
    post_node.addClass("current");
    thread_new.scroll_to_post_update_url(post_node);
    var image_container = post_node.find(".image_container");
    var content_id = image_container.data("content_id");
    var is_playing = post_node.find('.animated_hint').hasClass("pause");
    if (!is_playing && post_node.hasClass("animated")) {
        canvas.animateGif(content_id, image_container, 'giant');
    } else if (post_node.hasClass("audio_remix")) {
        var comment_id = post_node.data("comment_id");
        canvas.animateGif(content_id, image_container, 'giant');
        canvas.play_audio_remix(comment_id);
    }
};

thread_new.focus_on_next = function (dir) {
    var next_node = thread_new.get_next_reply_with_content(dir);
    if (next_node) {
        thread_new.focus_post(next_node);
    } else {
        if (dir == "prev" && thread_new.page_current > 1) {
            document.location = thread_new.base_url + (thread_new.page_current - 1) + '#last';
        } else if (dir == "prev") {
            // Go up to op if we're on the first page
            thread_new.focus_post($('#content .thread_op .thread_comment'));
        } else if (dir == "next" && thread_new.page_current < thread_new.page_last) {
            document.location = thread_new.base_url + (thread_new.page_current + 1) + '#first';
        }
    }
};

thread_new.wire_remix_slider = function (comment_node) {
    var remix_parent = $('.remix_parent', comment_node);
    var handle = $('.slider_handle', comment_node);
    var image = $('.image_link .ugc_img', comment_node);
    var width = image.attr("width");
    var height = image.attr("height");
    if (width < 200 || height < 200) {
        // We don't want to show handle if the image is smaller than the handle
        remix_parent.hide();
        handle.hide();
        return false;
    }
    handle.mobileDrag({
        bodyDraggingClass : "slider_drag",
        easyDrag: false,
        constrainX: [width, 0],
        constrainY: [0, 0],
        drag: function () {
            data = handle.data("mobileDrag");
        },
        move: function () {
            var width = data.originalPos.left - data.currentPos.left + 1;
            remix_parent.css("width", width + "px");
            if (width > 1) {
                remix_parent.css("border-left", "1px solid #999");
            } else {
                remix_parent.css("border-left", "0");
            }
        }
    });
};

thread_new.handle_comment = function(comment) {
    new canvas.ThreadComment(window.thread_new, comment);
    thread_new.replies_on_page[comment.id] = true;
    var comment_node = $('.thread_comment[data-comment_id=' + comment.id + ']');
    thread_new.handle_comment_node(comment_node);
};

thread_new.handle_comment_node = function(comment_node) {
    if (comment_node.hasClass("remix")) {
        thread_new.wire_remix_slider(comment_node);
    }
};

thread_new.get_replied_comment = function (id) {
    var replied = null;
    $.each(thread_new.reply_data, function (i, reply) {
        if (reply.id == id) {
            replied = new canvas.Comment(reply);
            return false;
        }
    });
    return replied;
};

thread_new.render_and_append_comment = function (comment_data, parent, options) {
    var comment = new canvas.ThreadComment(thread_new, comment_data);
    var rendered_comment = $(comment.render(options));
    $(parent).append(rendered_comment);
    thread_new.handle_comment(rendered_comment, comment, options);
    return rendered_comment;
};

thread_new.fetch_new_replies = function () {
    thread_new.nodes.more_posts_button.removeClass("visible");

    if (thread_new.page_current !== thread_new.page_last) {
        return document.location.href = thread_new.base_url + thread_new.page_last;
    }

    canvas.apiPOST(
        '/comment/replies',
        {
            comment_id: thread_new.op_comment.id,
            replies_after_timestamp: thread_new.last_timestamp,
        },
        function (response) {
            // Remove dupes
            var comment_nodes = $(response.html).filter(".thread_comment");
            var new_comment_nodes = $();
            $.each(comment_nodes, function(_, node) {
                node = $(node);
                var id = node.data("comment_id");
                if (!thread_new.replies_on_page[id]) {
                    new_comment_nodes = new_comment_nodes.add(node);
                    canvas.wire_lazy_images(node);
                }
            });
            thread_new.nodes.replies_ul.append(new_comment_nodes);
            $.each(response.replies, function(_, comment) {
                if (!thread_new.replies_on_page[comment.id]) {
                    thread_new.handle_comment(comment);
                }
            });
            thread_new.unread = 0;
            thread_new.realtime_is_disabled = false;
            document.title = "Canvas";
        }
    );
};

thread_new.wire_postwidget = function() {
    thread_new.image_chooser = new canvas.ImageChooser($('#postwidget .image_chooser'));

    var remixer_open = function () {
        return $('.remix_widget').is(':visible');
    };
    var update_submit_button_state = function (ignore_remixer) {
        thread_new.nodes.submit_button.attr('disabled', !($('#postwidget_caption').val() || (!ignore_remixer && remixer_open())));
    };

    var pw = thread_new.pw = new Postwidget({
        container: '#postwidget',
        is_reply: true,
        bind_type: 'column',
        default_text: '',
        submit_text: 'Post reply',
        parent_comment: thread_new.op_comment,
        skip_to_remix: true,
        pre_submit_callback: function () {
            // Don't show anymore new post notifications, so we don't see our own post.
            thread_new.realtime_is_disabled = true;
        },
        post_submit_callback: function (post, response) {
            if (!post.reply_content && thread_new.page_current == thread_new.page_last && !thread_new.sort_by_top) {
                // Temp hack, postwidget.js should own resetting the post widget, obv.
                this.scoped(".reply_addendum").css({opacity: 0});
                this.scoped(".pw_text").focus();
                this.reply_comment_id = null;
                thread_new.fetch_new_replies();
                return false;
            }
            return true;
        },
    });

    pw.wire_uploadify();

    thread_new.image_chooser.url_input_button.click(function (event) {
        if (!current.logged_in) {
            return false;
        }
        pw.upload_url(thread_new.image_chooser.url_input_field.val());
        event.preventDefault();
    });

    thread_new.image_chooser.start_from.draw.click(function () {
        if (!current.logged_in) {
            return false;
        }
        action.remix(thread_new.draw_from_scratch_content.id, 'draw');
        pw.remix_started();
        pw.wire_uploadify();
    });

    $(pw.container).bind('closing audio_remix_closing', function () {
        thread_new.image_chooser.show();
        update_submit_button_state(true);
    });

    $('#postwidget_caption').keyup(function () {
        update_submit_button_state();
    });

    thread_new.remixer = new remix.RemixWidget(pw, pw.scoped(".remix_widget"));
    thread_new.remixer.install_actions();

    thread_new.audio_remixer = new canvas.AudioRemixWidget(pw, pw.scoped('.audio_remix_widget'));
    thread_new.audio_remixer.install_actions();

    local.wire();
};

thread_new.remix_from_hash = function() {
    var remix_id;
    if (thread_new.comment_to_expand) {
        remix_id = thread_new.comment_to_expand.reply_content.id;
    }
    if (remix_id) {
        var source = '';
        var hash = document.location.hash.substr(1);
        if (hash === 'remix_sticker') {
            // Make sure to record remix sticker info
            source = 'sticker';
        } else if (hash === 'remix') {
            source = 'tile_hover_ui';
        } else if (hash === 'audio_remix') {
            source = 'tile_hover_ui';
        } else if (hash === 'remix_reposted') {
            source = 'repost_ui';
        }
        if (hash === "audio_remix") {
            action.audio_remix(thread_new.comment_to_expand.id, remix_id, source);
        } else {
            action.remix(remix_id, source);
        }
        thread_new.pw.remix_started();
    }
};

thread_new.hide_share_thread = function() {
    $('body').unbind("click.share_thread");
    thread_new.nodes.share_thread.removeClass("visible");
};

thread_new.show_share_thread = function() {
    var position = thread_new.nodes.share_thread_button.position();
    var left = position.left - thread_new.nodes.share_thread.outerWidth()/2 + thread_new.nodes.share_thread_button.outerWidth()/2;
    var top = position.top + thread_new.nodes.share_thread_button.outerHeight() + 15;
    thread_new.nodes.share_thread
        .addClass("visible")
        .css({
            left    : left,
            top     : top,
        })
    ;
    setTimeout(function() {
        $('body').bind("click.share_thread", function(e) {
            if (!$(e.target).closest(".share_thread").length) {
                $('body').unbind("click.share_thread");
                thread_new.hide_share_thread();
            }
        });
    }, 1);
};

thread_new.toggle_share_thread = function() {
    if (thread_new.nodes.share_thread.hasClass("visible")) {
        thread_new.hide_share_thread();
    } else {
        thread_new.show_share_thread();
    }
};

thread_new.wire = function() {
    thread_new.nodes = {
        replies_ul          : $('#content section.replies > ul'),
        submit_button       : $('#postwidget input[type=submit]'),
        more_posts_button   : $('#content button.more_posts'),
        share_thread        : $('#content .thread_op .share_thread'),
        share_thread_button : $('#content .thread_op hgroup button.share'),
    };

    thread_new.is_content_on_page = $('a[name="first"]').length > 0;

    thread_new.nodes.more_posts_button.bind("click", thread_new.fetch_new_replies);

    var comments_to_handle = [];
    $.each(thread_new.reply_data, function(i, reply) {
        comments_to_handle.push(reply);
    });

    $.each(comments_to_handle, function(i, comment) {
        thread_new.handle_comment(comment);
    });

    thread_new.wire_postwidget();
    canvas.wire_dismissables();

    // Check for hashes
    if (['#remix'].indexOf(document.location.hash) !== -1 || ['#audio_remix'].indexOf(document.location.hash) !== -1) {
        thread_new.remix_from_hash();
    } else if (['#first', '#last', '#current'].indexOf(document.location.hash) !== -1) {
        var anchor = $('a[name="' + document.location.hash.substr(1) + '"]');
        if (anchor.length) {
            thread_new.focus_post(anchor.closest('.thread_comment'));
        }
    } else if  (['#replies'].indexOf(document.location.hash) !== -1){
        thread_new.focus_post($($('#content section.replies .thread_comment')[0]));
    } else if (thread_new.comment_to_expand) {
        thread_new.goto_post(thread_new.comment_to_expand.url);
    }
    // Then remove hashes
    setTimeout(function() {
        // In a timeout because Chrome is dumb about going to the anchor too late.
        window.history.replaceState({}, "", window.location.pathname);
    }, 1);

    // Share thread widget
    thread_new.share_widget = new canvas.ShareThreadWidget(thread_new.nodes.share_thread, thread_new.op_comment.id);

    // Invite remixers button
    thread_new.nodes.share_thread_button.bind("click", thread_new.toggle_share_thread);

    // Postwidget signup prompt when logged out
    if (!current.logged_in) {
        $('#postwidget').click(function() {
            canvas.encourage_signup('reply_widget');
            return false
        });
    }

    $('body')

        // Replied links
        .delegate("a.replied_link", "mouseover", function() {
            var target_link = $(this);
            var comment_rendered = target_link.parents(".thread_comment");
            var comment = canvas.getComment(comment_rendered.data("comment_id"));
            if (!comment.replied_comment) {
                return false;
            }
            var replied_comment = canvas.getComment(comment.replied_comment.id);
            var replied_comment_rendered = $('<div id="replied_comment"></div>');
            var sticker_theme = (replied_comment.sorted_sticker_counts && replied_comment.sorted_sticker_counts.length) ? replied_comment.sorted_sticker_counts[0].name : "";

            $("#replied_comment").remove();
            replied_comment_rendered.prependTo(comment_rendered.find(".post > .wrapper"));
            thread_new.render_and_append_comment(replied_comment, replied_comment_rendered, {image_type: 'column', template: 'comment_replied', sticker_theme: sticker_theme});
            replied_comment_rendered.css({
                left: target_link.position().left + target_link.width() + 40,
                top: target_link.offset().top - comment_rendered.offset().top + (target_link.height()/2) - (replied_comment_rendered.height()/2) - 5,
            });
            // Prevent replied comment from going offscreen vertically
            var top_of_screen = $(window).scrollTop() + $("#header .top_bar > .wrapper").outerHeight() + 10;
            var bottom_of_screen = $(window).scrollTop() + $(window).height() - replied_comment_rendered.outerHeight() - 10;
            if (replied_comment_rendered.offset().top < top_of_screen) {
                replied_comment_rendered.css("top", top_of_screen - comment_rendered.offset().top);
            } else if (replied_comment_rendered.offset().top > bottom_of_screen) {
                replied_comment_rendered.css("top", bottom_of_screen - comment_rendered.offset().top);
            }
            var arrow = $(".arrow", replied_comment_rendered);
            arrow.css("top", Math.min(replied_comment_rendered.outerHeight() - arrow.height() + 8, Math.max(0, target_link.offset().top - replied_comment_rendered.offset().top - (arrow.height()/2) + (target_link.height()/2))));

            // If the image isn't visible, check to see if the user made it visible and then show it
            if (replied_comment.isCollapsed()) {
                if (!$(".post_" + replied_comment.id).hasClass("collapsed")) {
                    // Make this a little more elegant in CSS
                    replied_comment_rendered.children(".image_tile").removeClass("collapsed");
                    replied_comment_rendered.find(".replied_collapsed_text").addClass("hidden");
                }
            }

            // Now fade it in
            replied_comment_rendered.animate({opacity:1}, 300);
        })
        .delegate("a.replied_link", "mouseout", function() {
            $("#replied_comment").stop().animate({opacity:0}, 100, function () {
                $(this).remove();
            });
        })

        // Check for local links
        // If the link is on this page, jump to it, otherwise change document location
        .delegate('#content a.js_check_for_local_link', "click", function (e) {
            if (e.button == 0) {
                var location = $(this).attr("href");
                thread_new.goto_post(location);
                return false;
            }
        })

        // Keyboard shortcuts
        .bind("keydown", function (e) {
            if (thread_new.keyboard_shortcuts_disabled) {
                return;
            }
            if (e.keyCode == 74 || e.keyCode == 75) {
                //e.preventDefault();
            }
        })
        .bind("keyup", function (e) {
            if (thread_new.keyboard_shortcuts_disabled) {
                return;
            }
            if (e.keyCode == 75) {
                e.preventDefault();
                thread_new.focus_on_next("prev");
            } else if (e.keyCode == 74) {
                e.preventDefault();
                thread_new.focus_on_next("next");
            }
        })
        .delegate("input[type=text], textarea", "focus", function() {
            thread_new.keyboard_shortcuts_disabled = true;
        })
        .delegate("input[type=text], textarea", "blur", function() {
            thread_new.keyboard_shortcuts_disabled = false;
        })

        // Collapsed/hidden post behavior
        .delegate(".thread_comment.collapsed", "click", function() {
            var self = $(this);
            self.removeClass("collapsed");
            $('p.collapsed_text', self).remove();
            canvas.wire_lazy_images($(this));
        })

        // Click behavior for images
        .delegate(".image_link", "click", function() {
            var self = $(this);
            var comment = canvas.getComment(self.parents(".thread_comment").data("comment_id"));
            if (comment.reply_content.original.animated) {
                return true;
            }
            window.open(self.attr('data-footer_url'), "_blank");
            return false;
        })
    ;
};

thread_new.on_load = function () {
    // Only subscribe to new posts on last page
    if (thread_new.page_current < thread_new.page_last) {
        return;
    }
    var replies_channel = thread_new.replies_channel;
    realtime.subscribe(replies_channel, function (messages) {
        if (thread_new.realtime_is_disabled) {
            return;
        }
        $.each(messages, function (i, reply) {
            if (!thread_new.replies_on_page[reply.comment_id] && !thread_new.realtime_replies[reply.comment_id]) {
                thread_new.realtime_replies[reply.comment_id] = true;
                if (reply.timestamp > replies_channel.timestamp) {
                    // Ignore ghost messages, maybe from a moderated comment.
                    thread_new.unread += 1;
                }
            }
        });
        if (thread_new.unread) {
            var more = thread_new.nodes.more_posts_button;
            var text = "Click to show " + thread_new.unread + " new " + "post".pluralize(thread_new.unread, null, false);
            if (!more.hasClass("visible")) {
                // Fade in if it's not already visible
                more.css("opacity", 0).addClass("visible");
                more.animate({"opacity":1}, 1500);
            }
            more.text(text);
            document.title = "(" + thread_new.unread + ") Canvas";
        }
    });
};
