var canvas_effects = {};

// A +1 animation that rises and fades from a point
canvas_effects.give_bonus = function(num, start_x, start_y, reverse) {
    var bonus = $("<span>+"+num+"</span>");
    bonus.appendTo("body");
    
    var distance = 60
    start_x = start_x - (bonus.width()/2) - 5;
    start_y = start_y - (bonus.height()/2) - 10;
    var animate_to = (!reverse) ? "-="+distance+"" : "+="+distance+"";
    var opacity_to = (!reverse) ? 0 : 1;
    if (reverse) {
        start_y = start_y - distance;
        bonus.css("opacity", 0);
    }
    bonus.css({
        position:"absolute",
        left:start_x,
        top:start_y,
        color:"#feca2c",
        textShadow:"1px 1px 0 #773800",
        fontSize:"2.4em",
        fontWeight:"bold",
        zIndex:5,
    }).animate({top:animate_to, opacity:opacity_to}, 500, "linear", function() {
        $(this).remove();
    });
    return bonus;
};

canvas_effects.bounce = function(dir, target, times, speed, amplitude) {
    times = times || -1;
    speed = speed || 50;
    amplitude = amplitude || 50;
    var left = target.css("left");
    var top = target.css("top");
    var position = target.css("position");
    left = (left === "auto") ? 0 : parseInt(left, 10);
    top = (top === "auto") ? 0 : parseInt(top, 10);
    if (target.css("position") == "static") {
        target.css({
            position : "relative",
        });
    }
    var css_to = {};
    var css_from = {};
    if (dir == "left") {
        css_to = {
            left: left - amplitude
        };
        css_from = {
            left: left + amplitude
        };
    } else if (dir == "top") {
        css_to = {
            top: top - amplitude
        };
        css_from = {
            top: top + amplitude
        };
    }

    var animate = function(callback) {
        target
            .animate(css_to, speed, "linear")
            .animate(css_from, speed, "linear", function() {
                callback();
            })
        ;
        times--;
    };

    var animate_loop = function() {
        animate(function() {
            if (times > 0 || times < 0) {
                animate_loop();
            }
        });
    };

    // Move it to the top of it's amplitude first
    target.animate(css_from, speed/2, "linear", function() {
        // Then get things kicked off
        animate_loop();
    });
}

canvas_effects.bob = function(target, times, speed, amplitude) {
    canvas_effects.bounce("top", target, times, speed, amplitude);
};

canvas_effects.wiggle = function(target, times, speed, amplitude) {
    canvas_effects.bounce("left", target, times, speed, amplitude);
};

// Text fades in / floats up, pauses, then continues on / fades out
canvas_effects.short_message = function(msg, x, y, delay) {
    var message = $("<span>"+msg+"</span>");
    message.appendTo("body");
    message.css("opacity", 0);
    
    var distance = 30
    x = x - (message.outerWidth(true)/2);
    start_y = y + distance;
    message.css({
        position:"absolute",
        left:x,
        top:start_y,
        color:"#feca2c",
        textShadow:"1px 1px 0 #773800",
        fontSize:"2.4em",
        fontWeight:"bold",
        zIndex:5,
    }).animate({top:"-="+distance, opacity:1}, 250, "linear", function() {
        $(this).delay(delay).animate({top:"-="+distance, opacity:0}, 250, "linear", function() {
            $(this).remove();
        });
    });
    return message;
};

// Animate subject to object, can add curve and callback
canvas_effects.animate_to = function (subject, object, speed) {
    var curve;
    var callback;
    var clone;
    if (typeof arguments[3] === "function") {
        curve = 0;
        callback = arguments[3];
    } else if (typeof arguments[3] === "boolean") {
        curve = (arguments[3]) ? "easeInCubic" : "";
        callback = arguments[4];
    }
    object = $($(object)[0]); // Accept selectors, only use the first element

    if (!subject.length) {
        console.log("Bad jQuery selector for subject.");
        callback();
    } else if (!object.length) {
        console.log("Bad selector for object");
        callback();
    } else {
        var this_subject;
        var this_clone;
        for (var i = 0; i < subject.length; i++) {
            this_subject = $(subject[i]);

            var object_offset = object.offset();
            var subject_pos = this_subject.position();
            var subject_offset = this_subject.offset();

            this_subject.css({
                position    : "absolute",
                left        : subject_pos.left,
                top         : subject_pos.top,
            });

            var left_target = object_offset.left - subject_offset.left + subject_pos.left + (object.outerWidth()/2) - (this_subject.outerWidth()/2);
            var top_target = object_offset.top - subject_offset.top + subject_pos.top + (object.outerHeight()/2) - (this_subject.outerHeight()/2);

            this_subject.animate({
                left: left_target,
                top: [top_target, curve]
            }, speed, function () {
                if (typeof callback === 'function') {
                    callback.apply(subject);
                }
            });
        }
    }
};

canvas_effects.sheen = function(settings) {
    defaults = {
        target          : null,
        color           : "ffffff",
        opacity         : 0.5,
        speed           : 1000,
        delay           : 2000,
        repeat_delay    : 2000,
    }
    settings = $.extend(defaults, settings);
    canvas_effects.add_sheen(settings.target, settings.color, settings.opacity, settings.speed, settings.delay, settings.repeat_delay);
}

// Add a metallic sheen to an object's background, target must be non-static positioned
canvas_effects.add_sheen = function (target, color, opacity, speed, delay, repeat_delay) {
    this.target = target;
    color = color || "ffffff";
    opacity = opacity || 0.5;
    speed = speed || 1000;
    delay = (delay !== undefined && delay !== null) ? delay : 2000;
    repeat_delay = (repeat_delay !== undefined && repeat_delay !== null) ? repeat_delay : delay;
    
    // Put everything inside a wrapper so it goes above the sheen
    this.contents_wrapper = $('<div></div>');
    this.contents_wrapper.css({
        position    : "relative",
        zIndex      : 1,
    });
    target.children().appendTo(this.contents_wrapper);
    this.contents_wrapper.appendTo(target);

    // Create our sheen
    this.sheen_wrapper = $('<div></div>');
    this.sheen_wrapper.css({
        position    : "absolute",
        width       : "100%",
        height      : "100%",
        left        : 0,
        top         : 0,
        overflow    : "hidden",
    }).prependTo(target);
    
    var hexToRGB = function(hex, alpha) {
        var r = parseInt(hex.substr(0,2), 16);
        var g = parseInt(hex.substr(2,2), 16);
        var b = parseInt(hex.substr(4,2), 16);
        return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
    }
    var clear_color = hexToRGB(color, 0);
    var opaque_color = hexToRGB(color, opacity);
    
    this.sheen_div = $('<div class="sheen_effect" style="\
        background: -moz-linear-gradient(left, ' + clear_color + ' 0%, ' + opaque_color + ' 50%, ' + clear_color + ' 100%);\
        background: -webkit-gradient(linear, left top, right top, color-stop(0%,' + clear_color + '), color-stop(50%,' + opaque_color + '), color-stop(100%,' + clear_color + '));\
        background: -webkit-linear-gradient(left, ' + clear_color + ' 0%,' + opaque_color + ' 50%,' + clear_color + ' 100%);\
        background: -o-linear-gradient(left, ' + clear_color + ' 0%,' + opaque_color + ' 50%,' + clear_color + ' 100%);\
        background: -ms-linear-gradient(left, ' + clear_color + ' 0%,' + opaque_color + ' 50%,' + clear_color + ' 100%);\
        background: linear-gradient(left, ' + clear_color + ' 0%,' + opaque_color + ' 50%,' + clear_color + ' 100%);\
        -moz-transform: rotate(15deg);-o-transform: rotate(15deg);-webkit-transform: rotate(15deg);\
        -ms-transform: rotate(15deg);transform: rotate(15deg);\
        filter: progid:DXImageTransform.Microsoft.Matrix(\
            M11=0.9659258262890683, M12=-0.25881904510252074, M21=0.25881904510252074, M22=0.9659258262890683, sizingMethod=\'auto expand\'\
        );zoom: 1;">\
        </div>');
        
    this.sheen_div.css({
        position    : "absolute",
        width       : 80,
        height      : "200%",
        top         : "-25%",
        right       : -150,
    }).appendTo(this.sheen_wrapper);
    
    // Now let's animate this thing
    var that = this;
    this.shine = function() {
        that.sheen_div.animate({
            right : 150 + that.sheen_wrapper.outerWidth(),
        }, speed, "linear", function() {
            that.sheen_div.css("right", -150);
            if (repeat_delay > -1) {
                that.sheen_timer = setTimeout(that.shine, repeat_delay);
            }
        });
    }
    this.sheen_timer = setTimeout(this.shine, delay);
};

    canvas_effects.add_sheen.prototype.remove = function() {
        clearTimeout(this.sheen_timer);
        this.sheen_wrapper.remove();
        this.contents_wrapper.children().appendTo(this.target);
        this.contents_wrapper.remove();
    };

canvas_effects.apng = function(node, width, height, speed) {
    var img_url, apng, test_image;
    img_url = node.attr("src");
    apng = $('<div class="apng"></div>');
    apng.css({
        position: node.css("position"),
        left: node.css("left"),
        right: node.css("right"),
        top: node.css("top"),
        bottom: node.css("bottom"),
        width: width,
        height: height,
        zIndex: node.css("z-index"),
        backgroundImage: "url(" + img_url + ")",
        backgroundPosition: "0px 0px",
    });
    apng.addClass(node.attr("class"));
    node.replaceWith(apng);
    this._width = width;
    this._speed = speed;
    this._apng = apng;
    this.animate();
};

canvas_effects.apng.prototype.animate = function() {
    var i = 0;
    var that = this;
    var next_frame = function() {
        if (!that._apng.length) {
            return;
        }
        that._timeout = setTimeout(function() {
            if (!that._apng.length) {
                return;
            }
            i++;
            if (i >= that._speed.length) {
                i = 0;
            }
            that._apng.css({
                backgroundPosition: (-i*that._width) + "px 0px",
            });
            if (that._speed[i] > -1) {
                next_frame();
            }
        }, that._speed[i]);
    }
    next_frame();
};

canvas_effects.apng.prototype.stop = function() {
    clearTimeout(this._timeout);
};

canvas_effects.apng.prototype.remove = function() {
    this.stop();
    this._apng.fadeOut(300, function() {
        $(this).remove();
    });
};

canvas_effects.drop_fade = function (element, angle) {
    var clone = element.clone();
    var pos = element.offset();
    angle = (angle === undefined) ? Math.PI : angle;
    clone.appendTo('body');

    clone.css({
        position: 'absolute',
        left: pos.left,
        top: pos.top,
        zIndex: 105
    });
    clone.animate(
        {
            top: "+=" + Math.cos(angle) * -100,
            left: "+=" + Math.sin(angle) * 100,
            opacity: 0
        }, 
        {
            duration: 500,
            specialEasing: {
                opacity: "easeInOutSine"
            },
            complete: function () {
                $(this).remove();
            }
        }
    );

    return clone;
};

canvas_effects.make_it_rain = function (target, count, on_drop, on_finish) {
    var angles = [1, 1.05, 0.95, 1.1, 0.9];
    var speed = (count <= 15) ? 100 : 2000.0 / count;
    var i = 0;

    var count_down = function () {
        i++;
        if (i == count) {
            on_finish();
        } else {
            on_drop(i);
            canvas_effects.drop_fade(target, angles[i%angles.length] * Math.PI);
            setTimeout(count_down, speed);
        }
    }

    count_down();
};

canvas_effects.create_sticker = function(x, y, type_id, sticker_size) {
    x = x || 0;
    y = y || 0;
    type_id = type_id || 7;
    sticker_size = sticker_size || "medium";

    var sticker = $(tmpl.sticker(type_id, sticker_size));
    sticker.css({
        position    : "absolute",
        left        : x,
        top         : y,
    }).addClass(sticker_size);
    sticker.appendTo("body");
    return sticker;
};

canvas_effects.spit_out_sticker = function(x, y, hori_speed, type_id, sticker_size) {
    // Makes a sticker pop out in direction,
    // left or right depending on horizontal speed being positive or negative,
    // and fade as falls.
    hori_speed = hori_speed || 100;
    var sticker = canvas_effects.create_sticker(x, y, type_id, sticker_size);

    // Now animate it
    var time = 800;
    sticker.animate({
        opacity     : 0,
        left        : [x + hori_speed, 'easeOutQuad'],
        top         : [y + 300, 'easeInQuad'],
    }, time, 'linear', function() {
        sticker.remove();
    });
};

canvas_effects.sticker_grow_then_fade = function(x, y, type_id, sticker_size, growth_factor, speed) {
    // Makes a sticker appear then grow and fade.
    // Used to draw attention to a sticker.

    sticker_size = sticker_size || "large";
    growth_factor = growth_factor || 1.5;
    speed = speed || 250;
    var sticker = canvas_effects.create_sticker(x, y, type_id, sticker_size);

    var old_width = sticker.width();
    var new_width = old_width * growth_factor;
    var old_height = sticker.height();
    var new_height = old_height * growth_factor;
    sticker.animate({
        opacity : 0,
        left    : x - (new_width - old_width)/2,
        top     : y - (new_height - old_height)/2,
        width   : new_width,
        height  : new_height,
    }, speed, 'swing', function() {
        sticker.remove();
    });
};
