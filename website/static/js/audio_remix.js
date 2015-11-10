audio_remix = {
    inputs          : {
        image_url   : $("#image_url"),
        audio_url   : $("#audio_url"),
        start_time  : $("#audio_start"),
        end_time    : $("#audio_end"),
        image_upload: $("#image_upload"),
    },
    image_upload_wrapper    : $("#audio_remix .image_upload_wrapper"),
    audio_upload_wrapper    : $("#audio_remix .audio_upload_wrapper"),
    youtube_code_wrapper    : $("#audio_remix .youtube_code_wrapper"),
    audio_edit_wrapper      : $("#audio_remix .audio_edit_wrapper"),
    audio_embed_wrapper     : $("#audio_remix .audio_embed_wrapper"),
    image_wrapper           : $("#audio_remix .image_wrapper"),
    image_node      : $("#audio_remix .image_wrapper img"),
    status_node     : $("#audio_remix .loading_status"),
    length_node     : $("#audio_remix .loop_length"),
    ytid_node       : $("#audio_remix .youtube_code"),
    close_image_node: $("#audio_remix .image_close"),
    close_audio_node: $("#audio_remix .audio_close"),
    cancel_node     : $("#audio_remix .cancel_remix"),
    remix_switch    : $("#audio_remix .remix_switch"),
    audio_loading_node  : $("#audio_remix .loading_spinner"),
    preview_button  : $("#audio_remix .editor button.preview_audio_remix"),
    loop_slider     : $("#loop_slider .canvas_slider"),
    listener        : $("#audio_remix"),
    max_audio_length: 30,
    handle_buffer   : 10,
};

audio_remix.wire = function(pw) {
    audio_remix.pw = pw;
    action.audio_remix = function (comment_id, content_id) {
        audio_remix.load(comment_id, content_id);
        pw.showAudioRemix();
        audio_remix.wire_image_uploads();
    }
    
    // Set up input binds
    audio_remix.inputs.image_url.bind("change", function() {
        if ($(this).val()) {
            audio_remix.upload_image_from_url();
        }
    });
    audio_remix.inputs.audio_url.bind("change", function() {
        if ($(this).val()) {
            audio_remix.load_audio_from_url();
        }
    });
    audio_remix.inputs.start_time.bind("change", function() {
        audio_remix.parse_start_time();
    });
    audio_remix.inputs.end_time.bind("change", function() {
        audio_remix.parse_end_time();
    });
    audio_remix.cancel_node.bind("click", function() {
        pw.hideAudioRemix();
    });
    audio_remix.close_image_node.bind("click", audio_remix.unload_image);
    audio_remix.close_audio_node.bind("click", audio_remix.unload_audio);
    
    $("#audio_remix .input_wrapper input")
    .bind("keyup change", function() {
        if (!$(this).val()) {
            $(this).parent().children("label").removeClass("hidden");
        }
        $(this).parent().siblings(".error_alert").slideUp(100, function() {
            $(this).children("span").text("");
        });
    })
    .bind("keydown", function() {
        $(this).parent().children("label").addClass("hidden");
    })
    .bind("focus", function() { $(this).parent().children("label").addClass("active"); })
    .bind("blur", function() { $(this).parent().children("label").removeClass("active"); });
    
    // Tooltips
    $("#audio_remix .image_close").tooltip({
        content : "Replace image",
        delegate: $("body"),
    });
    $("#audio_remix .audio_close").tooltip({
        content : "Replace audio",
        delegate: $("body"),
    });
    
    pw.attachAudioRemix($('#audio_remix'));
}

audio_remix.switch_to_remix = function() {
    action.remix(audio_remix.pw.content.id, 'audio_remix');
}

audio_remix.toggle = function() {
    // This will either play or pause, and change button text appropriately
    // For now just play
    if (audio_remix_player.is_playing) {
        audio_remix.preview_button.text("Play");
        audio_remix.pause();
    } else {
        audio_remix.preview_button.text("Pause");
        audio_remix.play();
    }
}

audio_remix.play = function() {
    if (audio_remix.pw.content) {
        audio_remix.image_node.attr("src", audio_remix.pw.content.original.url);
    }
    if (audio_remix.ytid) {
        audio_remix.current_time_handle.show();
        audio_remix_player.play_audio(function(time) {
            // Function to run on every run of the loop check
            // Move the audio scrubbing handle
            if (!audio_remix.current_time_handle.hasClass("dragging")) {
                audio_remix.current_time_handle.css("left", (((time/audio_remix_player.currently_playing.duration)*audio_remix.loop_slider.width() - audio_remix.handle_buffer) + "px"));
            }
        }, true);
    }
    audio_remix_player.is_playing = true;
}

audio_remix.pause = function() {
    if (audio_remix.ytid) {
        audio_remix_player.swf.pauseVideo();
    }
    if (audio_remix.pw.content) {
        audio_remix.image_node.attr("src", audio_remix.pw.content.giant.url);
    }
    if (audio_remix.current_time_handle) {
        audio_remix.current_time_handle.hide();
    }
    audio_remix_player.is_playing = false;
}

audio_remix.load = function(comment_id, content_id) {
    var comment = canvas.getComment(comment_id);
    var content = (comment) ? comment.reply_content : null;
    if (content) {
        audio_remix.load_image(content);
    } else if (content_id) {
        audio_remix.load_image(canvas.getContent(content_id));
    } else if (audio_remix.pw.content) {
        // If we weren't supplied with a comment id, check if the pw has content already
        audio_remix.load_image(audio_remix.pw.content);
    }
    var audio_content = (comment) ? comment.external_content[0] : null; // Assume the first one is what we want for now
    if (audio_content) {
        audio_remix.load_audio(audio_content, comment_id);
    }
}

audio_remix.load_image = function(content) {
    audio_remix.remix_switch.show();
    audio_remix.image_upload_wrapper.addClass("invisible absolute");
    audio_remix.close_image_node.show();
    audio_remix.pw.content = content;
    audio_remix.image_node.attr("src", content.giant.url);
    var formatting = canvas.get_content_formatting(audio_remix.image_wrapper, {
        container_width : 600,
        threshold       : 0,
        img_width       : content.original.width,
        img_height      : content.original.height,
    });
    audio_remix.image_node.css({
        width   : formatting.img_width,
        height  : formatting.img_height,
    });
    audio_remix.image_wrapper.css({
        paddingTop      : formatting.container_padding,
        paddingBottom   : formatting.container_padding,
    })
    audio_remix.update_preview_button();
}

audio_remix.upload_image_from_url = function() {
    var image_url = audio_remix.inputs.image_url.val();
    audio_remix.inputs.image_url.val("");
    canvas.upload_url(image_url, audio_remix.image_node);
}

audio_remix.unload_image = function() {
    audio_remix.remix_switch.hide();
    audio_remix.pw.content = null;
    audio_remix.image_node.attr("src", "/static/img/0.gif");
    audio_remix.image_node.css({
        width: 0,
        height: 0,
    });
    audio_remix.image_wrapper.css({
        paddingTop: 0,
        paddingBottom: 0,
    });
    audio_remix.image_upload_wrapper.removeClass("invisible absolute");
    audio_remix.close_image_node.hide();
    audio_remix.update_preview_button();
}

audio_remix.load_audio_from_url = function() {
    audio_remix.ytid = null;
    
    // Get youtube code from URL
    var audio_url = audio_remix.inputs.audio_url.val();
    var youtube_code;
    if (audio_url.indexOf("?") !== -1) {
        audio_url_queries = audio_url.split("?")[1].split("&");
        for (var i = 0; i < audio_url_queries.length; i++) {
            var q = audio_url_queries[i].split("=");
            if (q[0] === "v") {
                youtube_code = q[1];
                break;
            }
        }
    }
    if (!youtube_code) {
        if (audio_url.indexOf("/") !== -1) {
            audio_url_pathname = audio_url.split("/");
            audio_url_pathname = audio_url_pathname[audio_url_pathname.length - 1];
            audio_url_pathname = audio_url_pathname.split("?")[0];
            youtube_code = audio_url_pathname;
        } else {
            youtube_code = audio_url;
        }
    }
    
    audio_remix.load_audio({
        source_url  : youtube_code,
        start_time  : 0,
        end_time    : 30,
        type        : "yt",
    });
}

audio_remix.load_audio = function(audio_content, comment_id) {
    audio_remix.audio_upload_wrapper.addClass("invisible");
    audio_remix.audio_loading_node.show();
    audio_remix.audio_embed_wrapper.show();
    
    var yt_timeout = setTimeout(function() {
        audio_remix.audio_upload_wrapper.removeClass("invisible");
        audio_remix.audio_loading_node.hide();
        audio_remix.throw_error("Error or timeout loading URL.", audio_remix.inputs.audio_url);
    }, 5000);
    
    // Set up the player vars
    audio_remix_player.currently_playing = {
        node        : $("#audio_remix"),
        comment     : canvas.getComment(comment_id),
        commend_id  : comment_id,
        audio_id    : "audio_embed",
    }
    
    // Call the audio player to load in the SWF
    audio_remix_player.load_audio("audio_embed", audio_content, function() {
        clearTimeout(yt_timeout);
        audio_remix.audio_upload_wrapper.removeClass("invisible");
        audio_remix.audio_loading_node.hide();
        audio_remix.inputs.audio_url.val("");
        audio_remix.ytid = audio_content.source_url;
        audio_remix.ytid_node.text(audio_content.source_url);
        audio_remix.ytid_node.attr("href", "http://youtu.be/" + audio_content.source_url);
        audio_remix.audio_upload_wrapper.hide();
        audio_remix.audio_edit_wrapper.show();
        audio_remix.update_preview_button();
        
        audio_remix.wire_sliders();
        
        audio_remix.parse_start_time(audio_content.start_time);
        audio_remix.parse_end_time(audio_content.end_time);
    }, true);
}

audio_remix.unload_audio = function() {
    audio_remix.ytid = null;
    clearInterval(audio_remix.loop_interval);
    audio_remix.audio_upload_wrapper.show();
    audio_remix.audio_edit_wrapper.hide();
    audio_remix.audio_embed_wrapper.hide();
    audio_remix.update_preview_button();
}

audio_remix.update_preview_button = function() {
    if (audio_remix.ytid || (audio_remix.pw.content && audio_remix.pw.content.original.animated)) {
        audio_remix.preview_button.attr("disabled", false);
    } else {
        audio_remix.preview_button.attr("disabled", true);
    }
}

audio_remix.parse_start_time = function(default_time) {
    var time = (default_time !== undefined) ? default_time : audio_remix.inputs.start_time.val();
    audio_remix_player.start_time = (time >= 0 && time < audio_remix_player.currently_playing.duration) ? time : 0;
    audio_remix.inputs.start_time.val(audio_remix_player.start_time);
    // Adjust appropriate handle
    audio_remix.start_handle.css("left", (((audio_remix_player.start_time/audio_remix_player.currently_playing.duration)*audio_remix.loop_slider.width() - audio_remix.handle_buffer) + "px"));
    audio_remix.update_loop_length();
}

audio_remix.parse_end_time = function(default_time) {
    var time = (default_time !== undefined) ? default_time : audio_remix.inputs.end_time.val();
    audio_remix_player.end_time = (time < audio_remix_player.currently_playing.duration && time > 0) ? time : audio_remix_player.currently_playing.duration;
    audio_remix.inputs.end_time.val(audio_remix_player.end_time);
    // Adjust appropriate handle
    audio_remix.end_handle.css("left", (((audio_remix_player.end_time/audio_remix_player.currently_playing.duration)*audio_remix.loop_slider.width() - audio_remix.handle_buffer) + "px"));
    audio_remix.update_loop_length();
}

audio_remix.update_loop_length = function() {
    var length = audio_remix_player.end_time - audio_remix_player.start_time;
    length = Math.round(length*10)/10;
    audio_remix.length_node.text(length);
    audio_remix.loop_length = length;
    if (length > audio_remix.max_audio_length || audio_remix_player.end_time <= audio_remix_player.start_time) {
        audio_remix.length_node.addClass("invalid");
        // Disable submit
    } else {
        audio_remix.length_node.removeClass("invalid");
        // Enable submit
    }
}

audio_remix.wire_sliders = function() {
    audio_remix.start_handle = $(".canvas_slider_handle:first-child", audio_remix.loop_slider);
    audio_remix.end_handle = $(".canvas_slider_handle:last-child", audio_remix.loop_slider);
    audio_remix.current_time_handle = $(".canvas_slider_handle.current_time", audio_remix.loop_slider);
    audio_remix.start_handle.mobileDrag({
        easyDrag: false,
        constrainX: [0, audio_remix.start_handle.parent().width()],
        constrainY: [0, 0],
        move: function() {
            // Update start time
            var time = Math.round((((parseInt(audio_remix.start_handle.css("left"), 10) + audio_remix.handle_buffer)/audio_remix.loop_slider.width())*audio_remix_player.currently_playing.duration) * 10)/10; // To nearest decimal
            audio_remix_player.start_time = time;
            audio_remix.inputs.start_time.val(time);
            audio_remix.update_loop_length();
        }
    });
    audio_remix.end_handle.mobileDrag({
        easyDrag: false,
        constrainX: [0, audio_remix.end_handle.parent().width()],
        constrainY: [0, 0],
        move: function() {
            // Update end time
            var time = Math.round((((parseInt(audio_remix.end_handle.css("left"), 10) + audio_remix.handle_buffer)/audio_remix.loop_slider.width())*audio_remix_player.currently_playing.duration) * 10)/10; // To nearest decimal
            audio_remix_player.end_time = time;
            audio_remix.inputs.end_time.val(time);
            audio_remix.update_loop_length();
        }
    });
    audio_remix.current_time_handle.mobileDrag({
        easyDrag: false,
        constrainX: [0, audio_remix.current_time_handle.parent().width()],
        constrainY: [0, 0],
        move: function() {
            // Seek to in video
            var time = Math.round((((parseInt(audio_remix.current_time_handle.css("left"), 10) + audio_remix.handle_buffer)/audio_remix.loop_slider.width())*audio_remix_player.currently_playing.duration) * 10)/10; // To nearest decimal
            audio_remix_player.swf.seekTo(time);
        }
    });
    audio_remix.current_time_handle.hide();
}

audio_remix.wire_image_uploads = function() {
    // Make sure to only do this once
    if (!audio_remix.uploadify_is_bound) {
        canvas.uploadify(audio_remix.inputs.image_upload, audio_remix.listener);
        audio_remix.uploadify_is_bound = true;
    }
    
    audio_remix.listener
    .bind('uploadend', function (e, content, response) {
        audio_remix.image_upload_wrapper.removeClass("invisible");
        audio_remix.status_node.hide();
        audio_remix.load_image(content);
    })
    .bind('uploadprogress', function (e, progress) {
        audio_remix.status_node.html('Loading: '+progress.percentage+'%');
    })
    .bind('uploadfail', function (e, message) {
        audio_remix.throw_error("Invalid URL. Please try again.", audio_remix.inputs.image_url);
        audio_remix.status_node.hide();
        audio_remix.image_upload_wrapper.removeClass("invisible");
        // Do something about this
    })
    .bind('uploadstart', function (e, meta) {
        audio_remix.image_upload_wrapper.addClass("invisible");
        audio_remix.status_node.html('Loading: 0%');
        audio_remix.status_node.show();
    })
}

audio_remix.throw_error = function(error_message, input) {
    input.parent().siblings(".error_alert")
        .children("span").text(error_message)
        .end().slideDown(100);
}
