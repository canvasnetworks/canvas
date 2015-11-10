/*
    Only one audio remix can be playing at a time.
    Use this to play audio remixes and for the
    audio remix editor.
*/

/*
    Thoughts: we need to be able to:
    -pause the current gif and audio
    -play any audio remix
    -play any audio content
    
    We can't put the audio player in the nav because
    we need to be able to tell people to install Flash
*/

audio_remix_player = {
    currently_playing : {
        node        : null, // The wrapping node of the reply or image tile object
        comment     : null, // The canvas.Comment object
        comment_id  : null, // The comment's ID
        audio_id    : null, // The ID string of the audio_embed node
        duration    : null, // Duration of the currently playing song
    },
    is_playing  : false,
    icon        : $("#sticker_widget .audio_playing_icon"),
    start_time  : 0,
    end_time    : 0,
};

canvas.play_audio_remix = function(comment) {
    // Usage:
    //     `comment` can be a Comment instance or a comment ID.
    if (!isNaN(comment)) {
        comment = canvas.getComment(comment);
    }

    // Check for flash first
    if (swfobject.hasFlashPlayerVersion("8")) {
        // Make sure the remix editor isn't open
        var audio_remix_node = $("#audio_remix");
        if (typeof thread_new !== 'undefined' && thread_new.pw.is_audio_remixing) {
            new canvas.AlertDialog("Sorry, you can't play this audio while the audio remix editor is open.");
            return false;
        }
        var post = $("[data-comment_id=" + comment.id + "]");
        // Either pause or play
        if (!audio_remix_player.is_playing || comment.id !== audio_remix_player.currently_playing.comment_id) {
            audio_remix_player.play(post);
        } else if (post.hasClass("loading")) {
            audio_remix_player.cancel_loading();
        } else {
            audio_remix_player.pause();
        }
    } else {
        new canvas.AlertDialog("Flash is required for audio remixes.");
        return false;
    }
};

audio_remix_player.unload = function() {
    if (audio_remix_player.swf) {
        audio_remix_player.pause();
        audio_remix_player.unload_audio();
    }
};

audio_remix_player.pause = function(image_type) {
    canvas.reset_favicon();
    var target = audio_remix_player.currently_playing.node;
    if (audio_remix_player.is_playing) {
        audio_remix_player.is_playing = false;

        // Pause gif
        audio_remix_player.pause_gif();

        // Pause the audio
        if (audio_remix_player.swf) {
            audio_remix_player.swf.pauseVideo();
            clearInterval(audio_remix_player.loop_interval);
        }
        
        $(".audio_hint", target).removeClass("pause");

        // Shrink reply if appropriate
        if (target && target.hasClass("reply") && target.hasClass("expanded")) {
            thread.toggle_reply_content_size(target, true);
        }
    }
    audio_remix_player.icon.hide();
};

audio_remix_player.pause_gif = function(image_type) {
    if (audio_remix_player.currently_playing.comment) {
        image_type = image_type || "column";
        var content = audio_remix_player.currently_playing.comment.reply_content;
        if (content.original.animated) {
            $(".image_container img", audio_remix_player.currently_playing.node).attr("src", content[image_type].url);
        }
    }
};

audio_remix_player.play = function(post) {
    // Unload any other videos
    var last_post = audio_remix_player.currently_playing.node;
    if (!post) {
        post = last_post;
    }
    if (!last_post || post[0] !== last_post[0]) {
        if (last_post && last_post.hasClass("loading")) {
            audio_remix_player.cancel_loading();
        } else {
            audio_remix_player.pause();
            audio_remix_player.unload_audio();
        }
    }
    // Set the currently_playing variables
    var comment_id = post.data("comment_id");
    var comment = canvas.getComment(comment_id);
    var embed_node = $(".audio_embed", post);
    if (!embed_node.length) {
        embed_node = $(".image_container object", post);
    }
    var id_string = embed_node.attr("id");
    console.log("STUFF", post, comment_id, comment);
    audio_remix_player.currently_playing = {
        node        : post,
        comment     : comment,
        comment_id  : comment_id,
        audio_id    : id_string,
    }
    
    // Expand reply if appropriate
    if (post.hasClass("reply") && !post.hasClass("expanded")) {
        thread.toggle_reply_content_size(post, true);
    }
    
    // Play the gif is needed
    var content = audio_remix_player.currently_playing.comment.reply_content;
    if (content.original.animated) {
        $(".image_container img", post).attr("src", content.ugc_original.url);
    }
    
    // Load and play or just play if already loaded
    if (!last_post || post[0] !== last_post[0]) {
        audio_remix_player.load_audio(audio_remix_player.currently_playing.audio_id, comment.external_content[0], function() {
            audio_remix_player.play_audio();
        });
    } else {
        if (audio_remix_player.swf) {
            audio_remix_player.play_audio();
        }
    }
    
    $(".audio_hint", post).addClass("pause");
    
    audio_remix_player.is_playing = true;
};

audio_remix_player.play_audio = function(loop_fun, is_remix_editor) {
    var comment = audio_remix_player.currently_playing.comment;
    if (!is_remix_editor) {
        audio_remix_player.start_time = comment.external_content[0].start_time;
        audio_remix_player.end_time = comment.external_content[0].end_time;
    }
    if (audio_remix_player.swf) {
        audio_remix_player.swf.seekTo(audio_remix_player.start_time);
        audio_remix_player.swf.playVideo();
    }
    
    // Set up the audio loop
    clearInterval(audio_remix_player.loop_interval);
    var last_time;
    audio_remix_player.loop_interval = setInterval(function() {
        if (audio_remix_player.is_playing && audio_remix_player.swf && audio_remix_player.swf.getCurrentTime) {
            var time = audio_remix_player.swf.getCurrentTime();
            if (time >= audio_remix_player.end_time) {
                audio_remix_player.swf.seekTo(audio_remix_player.start_time);
            }
            if (typeof loop_fun === "function") {
                loop_fun(time);
            }
            last_time = time; // Youtube stops before it reaches the end.
        }
    }, 100);
    
    // Change favicon and page title
    canvas.change_favicon("/static/img/favicons/audio_playing.ico", "Audio playing");
};

audio_remix_player.show_spinner = function() {
    if (audio_remix_player.currently_playing.node) {
        $('<div class="animated_spinner"></div>').prependTo($(".image_container", audio_remix_player.currently_playing.node));
        $(".image_container", audio_remix_player.currently_playing.node).css("opacity", 0.5);
    } else {
        // For the remix editor
        $('<div class="animated_spinner"></div>').prependTo($("#audio_remix .editor"));
    }
};

audio_remix_player.hide_spinner = function() {
    if (audio_remix_player.currently_playing.node) {
        $(".animated_spinner", audio_remix_player.currently_playing.node).remove();
        $(".image_container", audio_remix_player.currently_playing.node).css("opacity", 1);
    } else {
        // For the remix editor
        $("#audio_remix .editor .animated_spinner").remove();
    }
};

audio_remix_player.cancel_loading = function() {
    // This makes sure a post supeficially reverts to normal
    clearTimeout(audio_remix_player.youtube_timeout);
    if (audio_remix_player.currently_playing.node) {
        audio_remix_player.hide_spinner();
        if (audio_remix_player.currently_playing.node.hasClass("reply") && audio_remix_player.currently_playing.node.hasClass("expanded")) {
            thread.toggle_reply_content_size(audio_remix_player.currently_playing.node, true);
        }
        audio_remix_player.pause_gif();
        audio_remix_player.currently_playing.node.removeClass("loading");
        audio_remix_player.currently_playing.node.unbind("one.audio_remix");
        $(".audio_hint", audio_remix_player.currently_playing.node).removeClass("pause");
        audio_remix_player.currently_playing = {};
    }
};

audio_remix_player.load_audio = function(id_string, audio_content, callback, is_remix) {
    var params = {
        allowScriptAccess   : "always",
    }
    var atts = {
        id  : id_string,
    }
    swfobject.embedSWF(
        "//www.youtube.com/e/" + audio_content.source_url + "?enablejsapi=1&playerapiid=ytplayer&theme=light&version=3",
        id_string,
        "1", "1",
        "8",
        null, null, params, atts
    );
    audio_remix_player.currently_playing.node.addClass("loading");
    audio_remix_player.youtube_timeout = setTimeout(function() {
        audio_remix_player.cancel_loading();
        new canvas.AlertDialog("Timeout while trying to load audio.");
    }, 8000);
    audio_remix_player.currently_playing.node.bind("one.audio_remix", function() {
        audio_remix_player.cancel_loading();
    });
    audio_remix_player.show_spinner();
    window.onYouTubePlayerReady = function() {
        try {
            clearTimeout(audio_remix_player.youtube_timeout);
            audio_remix_player.currently_playing.node.removeClass("loading");
            audio_remix_player.hide_spinner();
            audio_remix_player.currently_playing.node.unbind("one.audio_remix");
            audio_remix_player.swf = document.getElementById(id_string);
            audio_remix_player.swf.addEventListener("onStateChange", "youtube_state_change");
            audio_remix_player.swf.addEventListener("onError", "youtube_error");
            audio_remix_player.currently_playing.duration = audio_remix_player.swf.getDuration();
            // Show icon
            audio_remix_player.icon.show().bind("click", audio_remix_player.pause);

            // Before we callback, make sure we have a duration by playing video muted.
            if (!audio_remix_player.currently_playing.duration) {
                audio_remix_player.swf.mute();
                audio_remix_player.swf.playVideo();
                var check_duration = setInterval(function() {
                    var duration = audio_remix_player.swf.getDuration();
                    if (duration) {
                        clearInterval(check_duration);
                        audio_remix_player.swf.stopVideo();
                        audio_remix_player.swf.unMute();
                        audio_remix_player.currently_playing.duration = duration;
                        if (typeof callback === "function") {
                            callback();
                        }
                    }
                }, 100);
            } else if (typeof callback === "function") {
                callback();
            }
        } catch (err) {
            console.log("YOUTUBE CALLBACK ERROR:", err.message, err.lineNumber, err.fileName);
        }
    }
}

// Events listeners for Youtube
// THESE HAVE TO BE IN GLOBAL SCOPE :?

window.youtube_state_change = function(state) {
    // Loop if the video is ended
    if (state === 0) {
        if (audio_remix_player.swf) {
            audio_remix_player.swf.seekTo(audio_remix_player.start_time);
        }
    }
}

window.youtube_error = function(error_num) {
    if (error_num === 2) {
        new canvas.AlertDialog("Invalid Youtube video ID.");
    } else if (error_num === 100) {
        new canvas.AlertDialog("Requested Youtube audio could not be found or is private.");
    } else if (error_num === 101 || error_num === 150) {
        new canvas.AlertDialog("Requested Youtube audio is not available for embed or not available in your country.");
    }
};

audio_remix_player.unload_audio = function() {
    if (audio_remix_player.swf) {
        // When we unload the swf we need to recreate our placeholder node
        var id = $(audio_remix_player.swf).attr("id");
        var embed_node = $('<div class="audio_embed" id="' + id + '"></div>');
        embed_node.insertAfter(audio_remix_player.swf);
        audio_remix_player.swf = null;
        swfobject.removeSWF(audio_remix_player.currently_playing.audio_id);
        $(".audio_hint", audio_remix_player.currently_playing.node).removeClass("pause");
        // Special case shrinking thread replies
        if (audio_remix_player.currently_playing.node.hasClass("reply") && audio_remix_player.currently_playing.node.hasClass("expanded")) {
            thread.toggle_reply_content_size(audio_remix_player.currently_playing.node, true);
        }
        // Clear out currently playing
        audio_remix_player.currently_playing = {};
    }
};

