window.logged_out_homepage = {};

logged_out_homepage.animation = {
    node            : $('#intro_animation .animation_window'),
    scribble_node   : $('#intro_animation .frame_2 .scribble'),
    scribble_img    : "/static/img/intro_animation/scribble.gif",
    panning         : false,
    current_frame   : 1,
    frames          : 4,
    _width          : 500,
    _height         : 347,
};

logged_out_homepage.animation.advance = function (event) {
    if (logged_out_homepage.animation.panning) {
        return false;
    }
    current_frame = logged_out_homepage.animation.current_frame;
    current_node = $('.frame_' + current_frame, logged_out_homepage.animation.node);
    ul_node = $('ul', logged_out_homepage.animation.node);
    logged_out_homepage.animation.panning = true;
    logged_out_homepage.animation.pan(ul_node, function() {
        ul_node.append(current_node);
        ul_node.css("top", 0);
        next_frame = current_frame + 1;
        next_frame = (next_frame > logged_out_homepage.animation.frames) ? 1 : next_frame;
        logged_out_homepage.animation.current_frame = next_frame;
        logged_out_homepage.animation.panning = false;

        // Special-case scribble animation
        if (logged_out_homepage.animation.current_frame == 2) {
            var img_node = $('<img src="' + logged_out_homepage.animation.scribble_img + '">');
            img_node.load(function() {
                logged_out_homepage.animation.scribble_node.addClass("play_animation");
            })
            logged_out_homepage.animation.scribble_node.append(img_node);
        }
    });
};

logged_out_homepage.animation.pan = function(node, callback) {
    node.animate({
        top : -logged_out_homepage.animation._height,
    }, 650, function() {
        callback();
    });
};

logged_out_homepage.wire = function() {
    // Wire inputs
    canvas.bind_label_to_input($('#page .signup input'));
    // Binding for intro animation
    logged_out_homepage.animation.node.click(function() {
        clearTimeout(logged_out_homepage.animation.timeout);
        clearInterval(logged_out_homepage.animation.interval);
        logged_out_homepage.animation.advance();
    });

    logged_out_homepage.animation.timeout = setTimeout(function() {
        logged_out_homepage.animation.advance();
        logged_out_homepage.animation.interval = setInterval(logged_out_homepage.animation.advance, 7000);
    }, 4000);
};

