canvas.AudioRemixWidget = canvas.BaseWidget.createSubclass();

canvas.AudioRemixWidget.prototype.init = function(pw, root) {
    canvas.AudioRemixWidget.__super__.init.call(this, root);

    this.closed = true;
    this.is_playing = false;
    this.root = root;
    this.pw = pw;
    this.image_content = {};
    this.handle_buffer = 10;
    this.max_audio_length = 60;

    // Nodes
    this.loading_mask = this.scoped('.loading');
    this.uploading_mask = this.scoped('.uploading');
    this.upload_percentage = this.scoped('.uploading .fill');
    this.cancel_button = this.scoped('a.cancel_remix');
    this.remove_audio = this.scoped('a.remove_audio');
    this.remove_image = this.scoped('a.remove_image');
    this.image = this.scoped('.image_preview img');
    this.audio_url_input = this.scoped('input.audio_url');
    this.start_time_input = this.scoped('input.start_time');
    this.end_time_input = this.scoped('input.end_time');
    this.length_input = this.scoped('input.length');
    this.current_time_input = this.scoped('input.current_time');
    this.loop_slider = this.scoped(".canvas_slider");
    this.play_toggle_button = this.scoped("button.play");
    this.audio_input_group = this.scoped(".audio_input");
    this.controls_group = this.scoped(".controls");
    this.load_audio_button = this.scoped("button.load_audio");
    this.loading_mask = this.scoped(".loading_mask");

    // Wiring
    this._wire_events();

    // Bindings
    this.bind_window();
    this.bind_inputs();

    this.pw.attachAudioRemix(this);
};

canvas.AudioRemixWidget.prototype.bind_window = function () {
    var self = this;
    // Make sure the user can't leave the page without confirmation while remix is open
    window.onbeforeunload = function () {
        if (!self.closed) {
            return "Are you sure you want to leave? You will lose all progress on your audio remix.";
        }
    };
};

canvas.AudioRemixWidget.prototype.unbind_window = function () {
    window.onbeforeunload = undefined;
};

canvas.AudioRemixWidget.prototype.bind_inputs = function() {
    var self = this;

    this.audio_url_input.bind("keypress", function() {
        if (event.keyCode == 13 && $(this).val()) {
            self.load_audio_from_url();
        }
    });
    this.load_audio_button.bind("click", function() {
        if (self.audio_url_input.val()) {
            self.load_audio_from_url();
        }
    });
    this.start_time_input.bind("change", function() {
        self.parse_start_time();
    });
    this.end_time_input.bind("change", function() {
        self.parse_end_time();
    });
    this.cancel_button.bind("click", function() {
        self.close();
    });
    this.remove_audio.bind("click", function() {
        self.unload_audio();
    });
    this.remove_image.bind("click", function() {
        self.unload_image();
    });
    this.play_toggle_button.bind("click", function() {
        self.toggle_play();
    });
    this.scoped(".input_wrapper input")
        .bind("keyup change", function() {
            var input = $(this);
            if (!input.val()) {
                input.parent().children("label").removeClass("hidden");
            }
            input.parent().siblings(".error_alert").slideUp(100, function() {
                input.children("span").text("");
            });
        })
        .bind("keydown", function() {
            $(this).parent().children("label").addClass("hidden");
        })
        .bind("focus", function() {
            $(this).parnet().children("label").addClass("active");
        })
        .bind("blur", function() {
            $(this).parent().children("label").removeClass("active");
        })
    ;
};

canvas.AudioRemixWidget.prototype._wire_events = function () {
    $(this.root).bind('loading', $.proxy(this.loading, this));
    $(this.root).bind('done_loading', $.proxy(this.done_loading, this));
};

canvas.AudioRemixWidget.prototype.loading = function () {
    this.loading_mask.show()
};

canvas.AudioRemixWidget.prototype.done_loading = function () {
    clearTimeout(this._loading_timeout);
    this.loading_mask.hide();
};

canvas.AudioRemixWidget.prototype._wire_cancel = function () {
    this.cancel_button.click($.proxy(function (event) {
        event.preventDefault();
        new canvas.ConfirmDialog({
            title: "Exit Audio Remix?",
            message: "Are you sure? You have an audio remix open and will lose ALL the progress.",
            cancel_text: "Keep working",
            ok_text: "Exit audio remix",
            success: $.proxy(function () {
                this.close();
            }, this),
            extra_buttons: save_button,
        });
    }, this));
};

canvas.AudioRemixWidget.prototype.open = function() {
    this.root.show();
    this.closed = false;
    this.root.css('opacity', '');
};

canvas.AudioRemixWidget.prototype.close = function () {
    audio_remix_player.pause();
    this.closed = true;

    $(this.pw.container).trigger('audio_remix_closing');

    $(this.root).animate({
        opacity: 0,
    }, 75, $.proxy(function () {
        $(this.root).hide();
    }, this));
};

canvas.AudioRemixWidget.prototype.install_actions = function () {
    var self = this;
    action.audio_remix = function (comment_id, content_id, source) {
        audio_remix_player.pause();
        if (!current.logged_in) {
            canvas.encourage_signup('remix');
            return false;
        }
        var metric_info = {
            source: source || 'thread_footer_link',
        };
        canvas.record_metric('attempted_remix', metric_info);

        var load_audio_remix = function () {
            self.load_image(content_id);
            comment = canvas.getComment(comment_id);
            var audio_content = (comment) ? comment.external_content[0] : null;
            if (audio_content) {
                self.load_audio(audio_content);
            }
            $(self.pw.container).trigger('audio_remix_opening');
            self.open();
            self.scroll_to();
        };

        if (!self.closed) {
            new canvas.ConfirmDialog({
                title: "Start a new Audio Remix?",
                message: "Are you sure? You already have an audio remix open and will lose ALL the progress of that one.",
                cancel_text: "Cancel",
                ok_text: "Start New Audio Remix",
                success: function () {
                    load_audio_remix();
                }
            });
        } else {
            load_audio_remix();
        }
    };
};

canvas.AudioRemixWidget.prototype.pause_image = function () {
    this.image.attr("src", this.image_content.giant.url);
};

canvas.AudioRemixWidget.prototype.play_image = function() {
    this.image.attr("src", this.image_content.original.url);
};

canvas.AudioRemixWidget.prototype.load_image = function (content_id) {
    var content = canvas.getContent(content_id);
    this.image_content = content;
    this.pause_image();
    this.remove_image.show();
};

canvas.AudioRemixWidget.prototype.unload_image = function() {
    this.image_content = {}
    this.image.attr("src", "/static/img/0.gif");
    this.remove_image.hide();
    thread_new.image_chooser.show();
}

canvas.AudioRemixWidget.prototype.load_audio = function(audio_content, comment_id) {
    $(this.root).trigger('loading');
    var self = this;
    var yt_timeout = setTimeout(function() {
        self.throw_error("Error or timeout loading URL.", self.audio_url_input);
    }, 5000);

    // Set up the Player
    audio_remix_player.currently_playing = {
        node        : $('.audio_remix_widget'),
        comment     : canvas.getComment(comment_id),
        comment_id  : comment_id,
        audio_id    : "audio_embed",
    }

    // And prep to play
    audio_remix_player.load_audio("audio_embed", audio_content, function() {
        clearTimeout(yt_timeout);
        self.switch_to_audio_player();
        self.ytid = audio_content.source_url;
        self.parse_start_time(audio_content.start_time);
        self.parse_end_time(audio_content.end_time);
        $(self.root).trigger('done_loading');
    });
};

canvas.AudioRemixWidget.prototype.load_audio_from_url = function() {
    this.ytid = null

    // Get youtube code form URL
    var audio_url = this.audio_url_input.val();
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

    this.load_audio({
        source_url  : youtube_code,
        start_time  : 0,
        end_time    : this.max_audio_length,
        type        : "yt",
    });
};

canvas.AudioRemixWidget.prototype.unload_audio = function() {
    this.pause_audio();
    this.audio_url_input.val("http://www.youtube.com/watch?v=" + this.ytid);
    this.ytid = null
    clearInterval(this.loop_interval);
    this.switch_to_audio_input();
};

canvas.AudioRemixWidget.prototype.switch_to_audio_player = function() {
    this.audio_url_input.val("");
    this.audio_input_group.hide();
    this.controls_group.show();
    this.wire_sliders();
};

canvas.AudioRemixWidget.prototype.switch_to_audio_input = function() {
    this.controls_group.hide();
    this.audio_input_group.show();
};

canvas.AudioRemixWidget.prototype.play_audio = function() {
    var self = this;
    if (this.ytid) {
        this.current_time_handle.show();
        audio_remix_player.is_playing = true;
        audio_remix_player.play_audio(function(time) {
            // Function to run on every run of the loop check
            // Move the audio scrubbing handle
            self.current_time_input.val(Math.round(time*10)/10);
            if (!self.current_time_handle.hasClass("dragging")) {
                self.current_time_handle.css("left", (((time/audio_remix_player.currently_playing.duration)*self.loop_slider.width() - self.handle_buffer) + "px"));
            }
        }, true);
    }
};

canvas.AudioRemixWidget.prototype.pause_audio = function() {
    if (this.ytid) {
        audio_remix_player.is_playing = false;
        audio_remix_player.swf.pauseVideo();
    }
    this.current_time_input.val("");
    this.current_time_handle.hide();
};

canvas.AudioRemixWidget.prototype.parse_start_time = function(default_time) {
    var time = (default_time !== undefined) ? default_time : this.start_time_input.val();
    audio_remix_player.start_time = (time >= 0 && time < audio_remix_player.currently_playing.duration) ? time : 0;
    this.start_time_input.val(audio_remix_player.start_time);
    // Adjust appropriate handle
    this.start_handle.css("left", (((audio_remix_player.start_time/audio_remix_player.currently_playing.duration)*this.loop_slider.width() - this.handle_buffer) + "px"));
    this.update_loop_length();
};

canvas.AudioRemixWidget.prototype.parse_end_time = function(default_time) {
    var time = (default_time !== undefined) ? default_time : this.end_time_input.val();
    audio_remix_player.end_time = (time < audio_remix_player.currently_playing.duration && time > 0) ? time : audio_remix_player.currently_playing.duration;
    this.end_time_input.val(audio_remix_player.end_time);
    // Adjust appropriate handle
    this.end_handle.css("left", (((audio_remix_player.end_time/audio_remix_player.currently_playing.duration)*this.loop_slider.width() - this.handle_buffer) + "px"));
    this.update_loop_length();
};

canvas.AudioRemixWidget.prototype.update_loop_length = function() {
    var length = audio_remix_player.end_time - audio_remix_player.start_time;
    length = Math.round(length);
    this.length_input.val(length);
    this.loop_length = length;
    if (length > this.max_audio_length || length < 1) {
        this.length_input.addClass("invalid");
        this.pw.toggle_submittable(false);
    } else {
        this.length_input.removeClass("invalid");
        this.pw.toggle_submittable(true);
    }
};

canvas.AudioRemixWidget.prototype.wire_sliders = function() {
    this.start_handle = this.loop_slider.find(".canvas_slider_handle:first-child");
    this.end_handle = this.loop_slider.find(".canvas_slider_handle:last-child");
    this.current_time_handle = this.loop_slider.find(".canvas_slider_handle:nth-child(2)");
    var self = this;
    this.start_handle.mobileDrag({
        easyDrag    : false,
        constrainX  : [0, self.start_handle.parent().width()],
        constrainY  : [0, 0],
        move        : function() {
            // Update start time
            var time = Math.round((((parseInt(self.start_handle.css("left"), 10) + self.handle_buffer)/self.loop_slider.width())*audio_remix_player.currently_playing.duration) * 10)/10;
            audio_remix_player.start_time = time;
            self.start_time_input.val(time);
            self.update_loop_length();
        }
    });
    this.end_handle.mobileDrag({
        easyDrag    : false,
        constrainX  : [0, self.end_handle.parent().width()],
        constrainY  : [0, 0],
        move        : function() {
            // Update end time
            var time = Math.round((((parseInt(self.end_handle.css("left"), 10) + self.handle_buffer)/self.loop_slider.width())*audio_remix_player.currently_playing.duration) * 10)/10;
            audio_remix_player.end_time = time;
            self.end_time_input.val(time);
            self.update_loop_length();
        }
    });
    this.current_time_handle.mobileDrag({
        easyDrag    : false,
        constrainX  : [0, self.current_time_handle.parent().width()],
        constrainY  : [0, 0],
        move        : function() {
            // Seek to in video
            var time = Math.round((((parseInt(self.current_time_handle.css("left"), 10) + self.handle_buffer)/self.loop_slider.width())*audio_remix_player.currently_playing.duration) * 10)/10;
            audio_remix_player.swf.seekTo(time);
            self.current_time_input.val(time);
        }
    });
    this.current_time_handle.hide();
};

canvas.AudioRemixWidget.prototype.toggle_play = function() {
    if (this.is_playing) {
        this.pause();
    } else {
        this.play();
    }
};

canvas.AudioRemixWidget.prototype.play = function() {
    this.play_image();
    this.play_audio();
    this.is_playing = true;
    this.play_toggle_button.addClass("playing");
};

canvas.AudioRemixWidget.prototype.pause = function() {
    this.pause_image();
    this.pause_audio();
    this.is_playing = false;
    this.play_toggle_button.removeClass("playing");
};

canvas.AudioRemixWidget.prototype.scroll_to = function () {
    var remixer_top = this.root.offset().top;
    var nav_height = $('#header .top_bar').outerHeight();
    var image_chooser_height = $('.image_chooser').outerHeight();
    if (!$('.image_chooser').is(':visible')) {
        image_chooser_height = 0;
    }
    var top = remixer_top - nav_height - image_chooser_height;
    $('html, body').animate({
        scrollTop: top,
    }, 500, 'swing');
};

canvas.AudioRemixWidget.prototype.throw_error = function(error_message, input) {
    input.parent().siblings(".error_alert")
        .children("span").text(error_message)
        .end().slideDown(100);
};

canvas.AudioRemixWidget.prototype.is_valid = function() {
    if (!this.image_content) {
        new canvas.AlertDialog("Try adding an image. Perhaps an animated gif?");
        return false;
    } else if (this.loop_length > this.max_audio_length) {
        new canvas.AlertDialog("Your audio loop must be " + this.max_audio_length + " seconds or less.");
        return false;
    } else if (this.loop_length < 1) {
        new canvas.AlertDialog("Make your audio loop just a bit longer please.");
        return false;
    } else if (!this.ytid) {
        new canvas.AlertDialog("Try adding audio from a youtube video!");
        return false;
    } else {
        return true;
    }
};
