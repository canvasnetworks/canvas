Postwidget = function (data) {
    var default_val = function (val, def) {
        if (typeof val === 'undefined') {
            return def;
        } else {
            return val;
        }
    };

    this.container = data.container;
    this.is_reply = data.is_reply || false;
    this.skip_to_remix = data.skip_to_remix || false;
    this.bind_type = data.bind_type;
    this.default_text = data.default_text;
    this.default_title = default_val(data.default_title, "Add your remix");
    this.submit_text = data.submit_text;
    this.upload_view = default_val(data.upload_view, {});
    this.content = null;
    this.uploaded_url = null;
    this.remixing = false;
    this.reply_comment_id = null;
    this.pre_submit_callback = data.pre_submit_callback;
    this.post_submit_callback = data.post_submit_callback;
    this.validator = data.validator;
    this.ignore_reposts = data.ignore_reposts || false;
    this.quest_idea = data.quest_idea || false;

    this.show_options_section = default_val(data.show_options_section, true);
    this.show_caption = default_val(data.show_caption, true);

    if (this.is_reply) {
        this.reply_wire(data.parent_comment);
    } else {
        this.wire(data.parent_comment);
    }
};

Postwidget.prototype.scoped = function (selector) {
    return $(selector, this.container);
};

Postwidget.prototype.showState = function (state) {
    this.scoped('#pw_right .tab.selected').removeClass('selected');
    this.scoped(state).addClass('selected');
};

Postwidget.prototype.upload_url = function (url) {
    if (url == "http://" || url == this.uploaded_url) {
        return;
    }
    this.scoped('.pw_urlbar').hide();
    canvas.upload_url(url, this.upload_view);
    this.uploaded_url = url;
};

Postwidget.prototype.toggle_submittable = function (submittable) {
    var inp = this.scoped('.upload_submit_button, .upload_caption_bg input');
    if (inp.prop) {
        inp.prop('disabled', submittable ? '' : 'disabled');
    } else {
        inp.attr('disabled', submittable ? '' : 'disabled');
    }
};

Postwidget.category_description_cache = {};
Postwidget.prototype.show_category_description = function () {
    var that = this;
    setTimeout(function () {
        var details = that.scoped('.category_details'),
            category_name = that.scoped('.category_free_select').val();
        // If category is anything but "uncategorized" show description.
        if (category_name == "") {
            html = "";
        } else if (category_name) {
            var category_description = Postwidget.category_description_cache[category_name];
            if (!category_description) {
                html = '<span class="invalid_category">No group with that name</span>';
            } else {
                html = ('<p class="double_check">Make sure this is the proper group for your post:</p>' +
                '<p><span class="category_name">' + category_name + '</span>: <span class="category_description">' + canvas.escape_html(category_description) + '</span></p>')
            }
        } else {
            html = "";
        }
        details.html(html);
        if (that.scoped(".category_free_select").val()) {
            that.scoped("label[for=category_select_input]").addClass("hidden");
        }
    }, 100);
};

Postwidget.prototype.attachRemix = function (remix) {
    $(remix.base).appendTo(this.scoped('.remix'));
    this.remix = remix;
};

Postwidget.prototype.attachAudioRemix = function (audio_remix) {
    this.audio_remix_widget = audio_remix;
};

// Scrolls the screen to the top of the remix widget.
Postwidget.prototype.scrollToRemix = function(){
    if (!$("#post").length) {
        return false;
    }
    $("html, body").animate({scrollTop: $("#post").offset().top - $("#header .top_bar").outerHeight() - 10}, 500, "swing");
};

Postwidget.prototype.showRemix = function (content_remix_width) {
    // Scroll into view.
    this.remix.base.show();
    this.scrollToRemix();

    // Transform post widget into remix widget.
    this.scoped('.post_wrapper').addClass("remixing");
    //this.scoped(".post_wrapper").css("height", "auto");
    var expanded_width = this.scoped(".toolbar").outerWidth(true) + content_remix_width + 4;
    var post_min_width = parseInt($(".post").css("min-width")) || 0;
    $(".reply_addendum").animate({left: 3}, 200, "swing");
    if (expanded_width > post_min_width) {
        if ($(".post").width() != expanded_width) {
            $(".post").animate({width: expanded_width}, 200, "swing", function() {
                $(this).css({overflowX:"visible", overflowY:"visible"});
            });
            // Hide any related images that might be overlapping
            $(".related_image").each(function() {
                if ($(this).offset().top + $(this).height() > $(".post").offset().top) {
                    $(this).addClass("invisible");
                }
            });
        }
    } else if ($(".post").width() != post_min_width) {
        $(".post").animate({width: post_min_width}, 200, "swing", function() {
            $(this).css({overflowX:"visible", overflowY:"visible"});
        });
    }

    this.remix.bind_keyboard();
    this.remixing = true;
};

Postwidget.prototype.hideRemix = function () {
    var that = this;

    that.scoped('.post_wrapper').removeClass("remixing");
    this.remix.base.hide();

    var post_min_width = parseInt($(".post").css("min-width"));
    var addendum_new_pos = ($("#pw_container_comment .image_well").is(".hidden")) ? 22 : 258;
    $(".reply_addendum").animate({left: addendum_new_pos}, 200, "swing");
    if ($(".post").width() != post_min_width) {
        $(".post").animate({width: post_min_width}, 1000, "swing", function() {
            // Show the related images that had been hidden before.
            $(".related_image.invisible").each(function() {
                $(this).removeClass("invisible");
            });
            $(this).css({overflowX:"visible", overflowY:"visible"});
        });
    }
    this.remix.unbind_keyboard();
    this.remixing = false;

    window.onbeforeunload = null;
};

Postwidget.prototype.text_only = function () {
    var that = this;
    that.scoped(".upload_image_well").addClass("hidden");
    that.scoped(".pw_text").attr("rows", "6");
    that.scoped(".form_details").slideDown(300);
};

// Wiring uploadify is in its own function because it needs to happen when the upload form is visible.
Postwidget.prototype.wire_uploadify = function (){
    var that = this;
    this.scoped('.pw_upload').each(function (i, element) {
        var $element = $(element);
        if (!$element.parents('.remix_widget').length) {
            canvas.uploadify($element, that.upload_view);
        }
    });
};

Postwidget.prototype.reply_wire = function (parent_comment) {
    // Used for thread replies. Calls this.wire and does extra work for thread replies.
    var that = this;

    //TODO kill
    // Listen for changes in the url by dragging an image URL
    $(this.upload_view).bind("uploadurl", function (event, url) {
        that.scoped(".pw_url").attr("value", url);
        that.upload_url(url);
    });

    // Dynamically change the size of the text input
    var prev = {},
        max_rows = 20,
        orig_rows = 0;

    that.scoped("textarea").bind("keyup keydown resize", function () {
        if (!prev.final_rows) {
            prev.final_rows = 0;
            orig_rows = $(this).attr('rows');
        }
        var ta = $(this),
            inferred_rows = prev.final_rows,
            nl_rows = ta.val().split('\n').length;

        while (ta[0].scrollHeight > prev.scrollHeight) {
            if (inferred_rows < orig_rows) {
                inferred_rows = orig_rows;
            }
            inferred_rows += 1;
            prev.scrollHeight += 18;
        }
        var final_rows = Math.max(nl_rows, inferred_rows);

        if (final_rows >= max_rows) {
            ta.css({"overflow": "scroll", "overflowX": "hidden"});
            ta.attr("rows", max_rows);
        } else if (final_rows >= orig_rows) {
            ta.attr("rows", final_rows);
        } else {
            ta.attr("rows", orig_rows);
        }
        prev.scrollHeight = ta[0].scrollHeight;
        prev.final_rows = final_rows;
    });

    // Watch that the character count doesn't go above 2k
    if (current.logged_in && that.show_caption) {
        var warning_node = that.scoped(".charcount_warning");
        var char_counter = new canvas.CharCounter().init({
            min             : 0,
            max             : 2000,
            input_field     : that.scoped("textarea"),
            counter         : $('.charcount', warning_node),
        });
        that.scoped("textarea").bind("charcount_invalidated", function () {
            that.toggle_submittable(false);
            warning_node.css("display", "block");
        }).bind("charcount_validated", function () {
            that.toggle_submittable(true);
            warning_node.css("display", "none");
        });
    }

    // If you click on the reply_addendum it should trigger a textarea click.
    that.scoped(".reply_addendum").bind("click", function (e) {
        that.scoped(".pw_text").focus();
    });

    window.onbeforeunload = function () {
        var reply_text = that.scoped(".pw_text").val();
        if (reply_text && reply_text != that.default_text) {
            return "Are you sure you want to leave? You've typed text in the reply box and will lose it if you leave this page.";
        }
    }

    action.reply = function (comment_id) {
        comment = canvas.getComment(comment_id);
        if (!comment) {
            return;
        }
        that.reply_comment_id = comment_id;
        $.scrollTo(that.container, Math.min(1000, Math.abs(($(that.container).offset().top - $(window).scrollTop())/6)), function () {
            that.scoped(".caption textarea").css("padding-top", "1.6em").focus();
            var addendum = that.scoped('.reply_addendum');
            addendum.css({'opacity': 0});
            addendum.html('@' + comment.author_name + ':');
            addendum.animate({'opacity': 1}, 500);
        });
    };

    // Set up image cancel listeners
    this.scoped(".remove_image").click(function (e) {
        if (that.content) {
            // If there is an image, remove it.
            that.scoped("#pw_thumbnail").css({paddingTop:0, zIndex:-1});
            that.scoped(".pw_thumbnail_img").removeClass("small_image");
            that.scoped(".pw_thumbnail_img").css({marginBottom:0});
            that.scoped('.pw_thumbnail_img').attr({src: "/static/img/0.gif", width:0, height:0});
            that.scoped(".post_wrapper").css("min-height", 0);
            that.scoped(".image_well").css({height: "100%"});
            that.content = null;
            that.scoped("#pw_thumbnail").removeClass("loaded");
        }
    });

    this.wire(parent_comment);
};

Postwidget.prototype.remix_started = function () {
    if (!current.logged_in) {
        return false;
    }
    this.scoped('.image_chooser').hide();
    var submit_button = $('.form_submission input[type=submit]');
    this.toggle_submittable(true);
};

Postwidget.prototype.wire = function (parent_comment) {
    var that = this;

    this.scoped('h1.postwidget_title').text(this.default_title);

    this.identity_select = this.scoped('.identity');
    this.anonymity = false;
    this.scoped('.identity ul').click(function () {
        that.anonymity = !that.anonymity;
        if (that.anonymity) {
            that.scoped('.identity li:first-child', that.identity_select).hide();
            that.scoped('.identity li:last-child', that.identity_select).show();
        } else {
            that.scoped('.identity li:last-child', post_thread.identity_select).hide();
            that.scoped('.identity li:first-child', post_thread.identity_select).show();
        }
    });

    this.fb_share_toggle = this.scoped('.fb_share_toggle');
    var button = that.scoped('button.facebook', that.fb_share_toggle);

    this.show_hide_fb_button = function () {
        if (this.remixing) {
            this.fb_share_toggle.show();
        } else {
            this.fb_share_toggle.hide();
        }
    };

    this.no_fb_session = true;

    this.show_hide_fb_button();

    this.toggle_button = function () {
        if (!(that.no_fb_session && current.enable_timeline_posts)) {
            current.enable_timeline_posts = !current.enable_timeline_posts;
            canvas.api.toggle_sharing();
        }
        if (current.enable_timeline_posts) {
            that.enable_fb_button();
        } else {
            that.disable_fb_button();
        }
        that.set_fb_button_state();
    };

    this.enable_fb_button = function() {
        if (current.enable_timeline_posts) {
            button.removeClass('disabled');
        } else {
            button.addClass('disabled');
        }
    };

    this.disable_fb_button = function() {
        button.addClass('disabled');
    };

    window.fbReady.done(function () {
        FB.getLoginStatus(function(response) {
            if (!response.authResponse) {
                that.disable_fb_button();
            } else {
                that.enable_fb_button();
                that.no_fb_session = false;
            }
        });
    });

    this.set_fb_button_state = function () {
        FB.getLoginStatus(function(response) {
            if (!response.authResponse) {
                FB.login(function(response) {
                    if (response.authResponse) {
                        that.enable_fb_button();
                    }
                },  {scope: 'email,publish_actions'});
            } else {
                that.enable_fb_button();
            }
        });
    }

    this.fb_share_toggle.mousedown(function () {
        that.toggle_button();
    });

    // Set up event handlers for the URL image uploads.
    $(this.upload_view)
        .bind('uploadstart', function (e, meta) {
            that.scoped('.pw_status_message').html('Loading: 0%');
            that.scoped('.pw_error_message').html('');
            that.scoped('.pw_loading').show();
            if (that.scoped(".pw_upload_form").parent().is("#pw_container_header")) {
                that.scoped(".form_details").slideDown(300);
            }
        })
        .bind('uploadend', function (e, content, response) {
            that.uploaded_content_id = content.id;

            var existing_url = response.existing_url;
            that.existing_url = existing_url;

            that.scoped(".remix_link > a").attr('href', '#').click(function(event) {
                event.preventDefault();
                start_remix();
            });

            that.scoped('.pw_loading').hide();
            that.scoped('.pw_status_message').html('');
            that.scoped('.pw_error_message').html('');

            var repost_detected = Boolean(existing_url && !parent_comment);

            var start_remix = function () {
                action.remix(content.id, 'postwidget');
                that.remix_started();
            };

            that.uploaded_content = content;

            var bind_postsize = function (half_size) {
                var bind_type = (content.original.animated) ? "original" : that.bind_type;
                content.bindToImage(that.scoped('.pw_thumbnail_img'), bind_type);
                that.scoped('.pw_thumbnail_img').show();
                if (half_size) {
                    that.scoped('.pw_thumbnail_img').css({height: "50%", width: "50%"});
                }
                that.content = content;
                that.showState('#pw_thumbnail');
                that.scoped("#pw_thumbnail").addClass("loaded");
                that.scoped("#pw_thumbnail").css({zIndex:1});
                that.scoped("#pw_thumbnail").css({zIndex:1});
            };

            if (that.skip_to_remix && (!repost_detected || that.ignore_reposts) && !content.original.animated) {
                start_remix();
            } else {
                if (that.scoped(".pw_upload_form").parent().is("#pw_container_comment")) {
                    // Resize stuff according to height of image in reply post widget.
                    var height_diff = content.column.height + that.scoped(".image_footer").outerHeight() - that.scoped(".post_wrapper").height();
                    if (height_diff > 0) {
                        height_diff = Math.max(height_diff, 0);
                        that.scoped(".post_wrapper").animate({minHeight:(that.scoped(".post_wrapper").height() + height_diff)}, 200, "swing");
                        that.scoped(".image_well").animate({height:(that.scoped(".image_well").height() + height_diff)}, 200, "swing", bind_postsize);
                    } else if (height_diff < 0) {
                        bind_postsize();
                        that.scoped(".pw_thumbnail_img").addClass("small_image");
                    } else {
                        bind_postsize();
                    }
                } else if (that.scoped(".pw_upload_form").parent().is("#pw_container_header")) {
                    bind_postsize();
                    // Resize header image well
                    var size_threshold = 100;
                    var img_width = content[that.bind_type].width;
                    var img_height = content[that.bind_type].height;
                    var container_width = that.scoped(".upload_image_well").width();
                    var container_height = that.scoped(".upload_image_well").height();
                    var growth_ratio = container_width/img_width;

                    that.scoped(".pw_thumbnail_img").css({width:img_width, height:img_height}).removeAttr("width").removeAttr("height");

                    // If the image isn't the same height, resize the image well.
                    if (img_height != container_height && img_width == 400) {
                        //that.scoped(".upload_image_well, .pw_thumbnail_img").css({height:img_height});
                    }
                    else if (img_width >= container_width - size_threshold && img_height == 250) {
                    }
                    else if (img_width == container_width && image_height == container_height) {
                        // If the image is exactly the right size, do nothing.
                    }
                    // Otherwise pad the well to center the image vertically.
                    else {
                        // Padding at most is the size threshold, at least 20.
                        var padding = Math.min(size_threshold, Math.max((container_height - img_height)/2, 20));
                        that.scoped(".pw_thumbnail_img").addClass("small_image");
                    }

                    // Change draw link to remix link
                    that.scoped(".pw_draw_link").attr("href", that.scoped(".pw_draw_link").attr("href") + "&cid=" + content.id).bind("click", function() {
                        // Remove on-unload behavior if we're jumping into remix
                        window.onbeforeunload = null;
                    });

                    that.scoped(".pw_draw span").text("remix this image");
                } else {
                    if (content.original.animated) {
                        var old_remix = action.remix;
                        action.remix = function(content_id, source) {
                           that.scoped('.pw_thumbnail_img').hide();
                           old_remix(content_id, source);
                        };
                        that.scoped('.image_chooser').hide();
                    }
                    bind_postsize(content.original.animated);
                }
            }

            // For the header, if this image was already uploaded and has a public url, encourage a reply or remix instead of repost.
            if (repost_detected && !that.ignore_reposts) {
                that.scoped('.pw_existed').removeClass('hidden').show();
                that.scoped('.upload_image_well').css("min-height", that.scoped('.pw_existed').outerHeight(true)+40);
                that.scoped('#pw_existed_link').attr('href', existing_url).html('example.com'+existing_url);
                that.scoped('#pw_existed_reply').click(function () { window.location = existing_url+"#comments"; });
                that.scoped('#pw_existed_remix').click(function (event) { window.location = existing_url+"#remix_reposted"; event.preventDefault(); });
                that.scoped('#pw_existed_newthread').click(function () {
                    that.scoped('.pw_existed').addClass('hidden').hide();
                    that.toggle_submittable(true);
                    if (!that.content.original.animated) {
                        start_remix();
                        that.scoped('.pw_thumbnail_img').hide();
                    }
                    return false;
                });
                that.scoped('#pw_existed_start_over').click(function () {
                    that.scoped('.pw_existed').addClass('hidden').hide();
                    that.toggle_submittable(true);
                    if (!that.content.original.animated) {
                        start_remix();
                        that.scoped('.pw_thumbnail_img').hide();
                    }
                    return false;
                });

                // Disable the submit button, and make clicking repost hide the UI and allow posting.
                that.toggle_submittable(false);
                $('#pw_existed_repost').click(function() {
                    that.scoped('.pw_existed').addClass('hidden');
                    that.toggle_submittable(true);
                    return false;
                });
            } else {
                that.scoped('.pw_existed').addClass('hidden');
                that.toggle_submittable(true);
                that.scoped('.upload_image_well').css("min-height", 0);
            }
        })
        .bind('uploadfail', function (e, message) {
            that.scoped('.pw_loading').hide();
            console.log('fail', message);
            $(this).trigger('clear');
            var fail_message = message || 'Upload failed :[';
            that.scoped('.pw_status_message').html(fail_message); //TODO delete once we move to new flow
            that.scoped('.pw_error_message').html(fail_message);
        })
        .bind('uploadprogress', function (e, progress) {
            that.scoped('.pw_status_message').html('Loading: '+progress.percentage+'%');
        })
        .bind('clear', function () {
            console.log('clear');
            that.scoped('.pw_status_message').html('');
            that.scoped('.pw_error_message').html('');
            that.content = null;
            that.showState('#pw_image_ui');
        });

    // Bind for text-only OP link
    that.scoped('.text_only').bind("click", function() {
        that.text_only();
    });

    // Click to upload via URL.
    this.scoped('.pw_url_upload').bind('click', function () {
        // Don't attempt an upload when there's nothing in the input.
        var url_val = that.scoped('.pw_url').val()
        if (url_val) {
            that.upload_url(url_val);
        }
    });

    // Pressing enter to upload an image via URL.
    this.scoped('.pw_url').bind('keydown', function(event) {
        var enterKey = 13;
        if (event.keyCode == enterKey) {
            that.scoped('.pw_url_upload').trigger('click');
        }
    });

    // Input losing focus to upload an image via URL.
    this.scoped('.pw_url').bind('blur', function(event) {
        that.scoped('.pw_url_upload').trigger('click');
    });

    // Handle group input with auto-complete.
    var best_group = null;
    // Populate the cache with the group currently browsed, if there is one.
    if (!current.nav_category.special) {
        Postwidget.category_description_cache[current.nav_category.name] = current.nav_category.description;
    }

    var update = that.show_category_description.bind(that);

    $('.ui-autocomplete').bind('click', function () {
        update();
    });
    that.scoped(".category_upload").bind('update-description', update);
    update();

    // Submitting the actual form to submit the image/text.
    this.scoped('input[type=submit]').bind('click', function () {
        that.toggle_submittable(false);

        if (current.share_page) {
            canvas.record_fact('flow_submitted_remix');
        }

        if (that.is_audio_remixing && !that.audio_remix_widget.is_valid()) {
            return false;
        }

        if (that.scoped(".pw_upload_form").parent().is("#pw_container_comment") || that.container == "#postwidget") {
            window.onbeforeunload = null;
        }
        var text = that.scoped('.pw_text').val();
        var title = that.scoped('#post_thread_title').val();
        var anonymous;
        if (that.scoped('.identity').length) {
            anonymous = that.anonymity;
        } else {
            anonymous = that.scoped('.pw_anonymous').is(':checked');
            that.scoped('.pw_anonymous').attr('checked', false);
        }
        var agreed = that.scoped('.pw_conduct').is(':checked');
        if (text == that.default_text) { text = ''; }

        // Send up a category if one was specifically selected. The API will handle the category for replies which
        // don't have a choice.
        var post_category = $.trim((that.scoped('.category_free_select').val() || "")).toLowerCase();

        var tags = [];
        if (that.scoped('.tag_free_select').val()) {
            tags = $.trim(that.scoped('.tag_free_select').val()).toLowerCase().split(/,/);
        }

        if (!post_category || post_category == 'uncategorized') { post_category = null; }

        if (!agreed) {
            new canvas.AlertDialog("If you'd like to post, please consider abiding by the Code of Conduct!");
            return false;
        }

        if (that.validator) {
            if (!that.validator()) {
                return false;
            }
        }

        function send () {
            if (text || that.content) {
                var reply_content_id = that.content ? that.content.id : null;
                var parent_comment_id = parent_comment ? parent_comment.id : null;
                var reply_comment_id = that.reply_comment_id;
                var remix_metadata = that.content && that.content._fact_metadata;

                if (that.pre_submit_callback) {
                    that.pre_submit_callback();
                }
                var post = {
                    anonymous: anonymous,
                    replied_comment: reply_comment_id,
                    reply_text: text,
                    reply_content: reply_content_id,
                    parent_comment: parent_comment_id,
                    category: post_category,
                    fact_metadata: { remix: remix_metadata },
                    title: title,
                    tags: tags,
                };
                if (that.is_audio_remixing && that.audio_remix_widget.is_valid()) {
                    post.external_content = {
                        type        : "yt",
                        source_url  : that.audio_remix_widget.ytid,
                        start_time  : audio_remix_player.start_time,
                        end_time    : audio_remix_player.end_time,
                    }
                }

                // Disable the submit button so we don't send multiple ajax replies.
                that.toggle_submittable(false);

                // If not logged in, send the post data to the signup prompt which will handle submitting it.
                if (!current.logged_in && !that.quest_idea) {
                    canvas.record_metric('logged_out_post', { 'remix': that.remixing });
                    canvas.api.validate_comment(post).done(function (response) {
                        canvas.record_fact("flow_login_wall");
                        if (that.remix.unbind_window) {
                            that.remix.unbind_window();
                        }
                        canvas.encourage_signup('reply', {
                            post   : post,
                            content: that.content,
                            in_flow: current.share_page ? 'yes' : 'no',
                        });
                        that.toggle_submittable(true);
                    }).fail(function (response) {
                        new canvas.AlertDialog(response.reason);
                        that.toggle_submittable(true);
                    });
                    return false;
                }

                var post_done_callback = function (response) {
                    var comment = response.comment;
                    var is_remix = response.comment.reply_content.id;
                    var comment_url = 'http://' + document.domain + comment.url;

                    if (is_remix && current.enable_timeline_posts) {
                        FB.getLoginStatus(function(response) {
                            if (response.authResponse) {
                                var accessToken = response.authResponse.accessToken;
                                canvas.api.share_remix(comment_url, accessToken)
                            }
                        });
                    }

                    that.toggle_submittable(true);

                    if (that.remix.unbind_window) {
                        that.remix.unbind_window();
                    }

                    var propagate = true;
                    if (that.post_submit_callback) {
                        propagate = that.post_submit_callback.call(that, post, response);
                    }

                    // Clear this first so that we don't get the dirty reply field warning on leaving the page.
                    that.scoped('.pw_text').val('');

                    if (propagate) {
                        // Tack on the parent so it is properly URL aware, and then take them to the correct place.
                        response.comment.parent_comment = parent_comment;
                        window.location = (new canvas.Comment(response.comment)).getCommentURL();
                    }
                    $(that.upload_view).trigger('clear');
                };

                var post_comment_def;
                if (that.quest_idea) {
                    // For DrawQuest.
                    post_comment_def = canvas.apiPOST('/submit_quest/post_quest_idea', {
                        title: post.title,
                        content: post.reply_content,
                        name: that.scoped('#post_thread_name').val(),
                        email: that.scoped('#post_thread_email').val(),
                    }, post_done_callback);
                } else {
                    post_comment_def = canvas.api.post_comment(post).done(post_done_callback);
                }

                post_comment_def.fail(function (response) {
                    new canvas.AlertDialog(response.reason);
                    that.toggle_submittable(true);
                });
            }
        };

        if (that.remixing) {
            that.remix.easel.renderer.finish_current_tool()
            if (that.uploaded_content_id && !that.remix.remix_has_changes()) {
                that.content = that.uploaded_content;
                send();
            } else {
                that.remix.upload(function (content) {
                    that.content = content;
                    that.content._fact_metadata = that.remix.get_metadata();
                    send();
                });
            }
        } else if (that.is_audio_remixing) {
            that.content = that.audio_remix_widget.image_content;
            send();
        } else {
            send();
        }
        return false;
    });

    // Populate the submit button text and the default textarea message.
    if (this.submit_text) {
        this.scoped('.upload_submit_button').attr('value', this.submit_text);
    }
    canvas.init_default_value(this.scoped('.pw_text'), this.default_text);
    canvas.init_default_value(this.scoped('.pw_url'), 'http://');

    // Now hide the image_well and put the button there in reply widget
    if (that.scoped(".pw_upload_form").parent().is("#pw_container_comment")) {
        this.scoped('.image_well_button').removeClass("hidden").bind("click", function () {
            $(this).animate({width:0}, 100, "swing", function () {
                $(this).addClass("hidden");
            });
            that.scoped(".pw_text").animate({width:325}, 200, "swing", function () {
                $(this).removeClass("wide");
            });
            that.scoped(".image_well").css({width:0, overflow:"hidden"}).removeClass("hidden").animate({width:250}, 200, "swing");
            that.scoped(".reply_addendum").animate({left:258}, 200, "swing");
            that.wire_uploadify();
        });
        this.scoped(".image_well_close").bind("click", function() {
            that.scoped(".image_well").animate({width:0}, 200, "swing", function() {
                $(this).css({width:0, overflow:"hidden"}).addClass("hidden");
            });
            that.scoped(".pw_text").animate({width:561}, 200, "swing", function() {
                $(this).addClass("wide");
            });
            that.scoped(".image_well_button").css({width:0, overflow:"hidden"}).removeClass("hidden").animate({width:22}, 100, "swing");
            that.scoped(".reply_addendum").animate({left:22}, 200, "swing");
        });
        this.scoped('.image_well').addClass("hidden");
        this.scoped(".pw_text").addClass("wide");
    }

    if (!this.show_options_section) {
        this.scoped("div.options").hide();
    }

    if (!this.show_caption) {
        this.scoped("div.post_caption").hide();
    }

    $(this.container)
        .bind('opening', function () {
            that.remixing = true;
            that.show_hide_fb_button();
            if (that.is_audio_remixing) {
                that.audio_remix_widget.close();
            }
        })
        .bind('closing', function () {
            that.remixing = false;
            that.show_hide_fb_button();
        })
        .bind('audio_remix_opening', function() {
            that.is_audio_remixing = true;
            that.show_hide_fb_button();
            if (that.remixing) {
                that.remix.close();
            }
        })
        .bind('audio_remix_closing', function() {
            that.is_audio_remixing = false;
            that.show_hide_fb_button();
        });
};

