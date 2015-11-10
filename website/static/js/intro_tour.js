var intro_tour = {};

intro_tour.wire = function() {
    intro_tour.steps = [
        {
            target  : $('#page.feed #content'),
            message : "This is your Personal Feed. Here's where you'll see remixes\
                from people you follow, as well as remixes that get promoted by people you follow.",
        },
        {
            target  : $('#sidebar nav li:nth-child(2)'),
            message : "Everyone's doing the Monster Mash! Team up with a friend to\
                create a monster — you draw one half, and your friend draws the other half.",
        },
        {
            target  : $('#sidebar nav li:nth-child(3)'),
            message : "Click Explore to check out what people are remixing on Canvas right now.",
        },
        {
            target  : $('#sidebar .tag_search'),
            message : "Search and follow tags to keep track of topics you care about!",
        },
        {
            target  : $('#sticker_pack .fixed_wrapper'),
            message : "Show some love to Canvas members by dragging Stickers onto\
                their remixes! Buy Epic Stickers with #1 Coins to promote remixes to your followers. ",
        },
        {
            target  : $('#header .progress_bar'),
            message : "Level up by getting your posts stickered and remixed.",
        },
        {
            target  : $('#header .new_thread > a'),
            message : "Got a neat idea or image? Start a thread and invite other people to remix!",
        },
    ];

    // Wait to start tour until we've preloaded the images.
    var preload_images = [
        '/static/img/intro_bubble_top.png',
        '/static/img/intro_bubble_bottom.png',
        '/static/img/intro_bubble_left.png',
        '/static/img/intro_bubble_right.png',
    ];
    var count = 0;
    for (var i = 0; i < preload_images.length; i++) {
        (function(i) {
            var image = $('<img src="' + preload_images[i] + '">');
            image.load(function() {
                count++;
                if (count == preload_images.length) {
                    intro_tour.start_tour();
                }
            });
        })(i)
    }
};

intro_tour.start_tour = function() {
    intro_tour.fade_page();
    intro_tour.do_tour_step(0);
};

intro_tour.fade_page = function() {
    var scrim = $('<div class="tour_scrim"></div>');
    $('body').prepend(scrim);
    return scrim;
};

intro_tour.unfade_page = function() {
    var scrim = $('body > .tour_scrim');
    scrim.remove();
}

intro_tour.create_bubble = function(index) {
    var next_step_text = (index < intro_tour.steps.length - 1) ? "Next Step »" : "That's it!";
    var bubble = $('\
        <div class="tour_hint">\
            <p class="bubble">\
                ' + intro_tour.steps[index].message + '\
            </p>\
            <footer>\
                <p class="next">\
                    ' + (index + 1) + '/' + intro_tour.steps.length + '\
                    <a>' + next_step_text + '</a>\
                </p>\
                <a class="skip">skip tour</a>\
            </footer>\
        </div>\
    ');
    intro_tour.steps[index].bubble = bubble;
    return bubble;
};

intro_tour.place_bubble = function(bubble, index) {
    var target = intro_tour.steps[index].target;

    // Positioning is based on where the target is located
    var target_offset = target.offset();
    var target_width = target.outerWidth();
    var target_height = target.outerHeight();
    $('body').prepend(bubble);
    var bubble_margin = 5;
    var bubble_width = bubble.outerWidth();
    var bubble_height = bubble.outerHeight();
    var bubble_bottom_height = $('footer', bubble).outerHeight();
    var window_width = $(window).width();
    var window_height = $(window).height();
    var window_top = $(window).scrollTop();

    // Only check left, right, and above if we're not too close to the top
    var left = 0;
    var top = 0;
    var arrow_dir = "";
    if (target_offset.top >= 40) {
        // Check that we're not too close to the bottom of the screen
        if (target_offset.top + 40 < window_top + window_height) {
            // Is there room to the left of it
            if (target_offset.left > bubble_width + bubble_margin*2) {
                left = target_offset.left - bubble_width - bubble_margin;
                top = Math.max(bubble_margin, target_offset.top + (Math.min(window_height, target_height))/2 - bubble_height/2);
                arrow_dir = "right";
            }
            // Is there room to the right of it
            else if (window_width - (target_offset.left + target_width) > bubble_width + bubble_margin*2) {
                left = target_offset.left + target_width + bubble_margin;
                top = Math.max(bubble_margin, target_offset.top + (Math.min(window_height, target_height))/2 - bubble_height/2);
                arrow_dir = "left";
            } else {
                // Fallback for large things
                left = bubble_margin;
                top = bubble_margin;
                arrow_dir = "right";
            }
        }
        // Is there room above it
        else if (target_offset.top > bubble_height + bubble_margin*2) {
            left = Math.min(window_width - bubble_width - bubble_margin, Math.max(bubble_margin, target_offset.left + target_width/2 - bubble_width/2));
            top = target_offset.top - bubble_height - bubble_margin;
            arrow_dir = "down";
        }
    } else {
        // Fallback case is below it
        left = Math.min(window_width - bubble_width - bubble_margin, Math.max(bubble_margin, target_offset.left + target_width/2 - bubble_width/2));
        top = target_offset.top + target_height + bubble_margin;
        arrow_dir = "up";
    }

    bubble.css({
        left    : left,
        top     : top,
    }).addClass("arrow_" + arrow_dir);

    return arrow_dir;
};

intro_tour.bind_bubble = function(bubble, index) {
    $('.bubble', bubble).click(function() {
        intro_tour.next_tour_step(index);
    });
    $('.next a', bubble).click(function() {
        intro_tour.next_tour_step(index);
    });
    $('.skip', bubble).click(function() {
        intro_tour.remove_hint(index);
        intro_tour.end_tour();
    });
};

intro_tour.add_highlight = function(index) {
    var node = intro_tour.steps[index].target;
    node.addClass("tour_highlight");
};

intro_tour.remove_highlight = function(index) {
    var node = intro_tour.steps[index].target;
    node.removeClass("tour_highlight");
};

intro_tour.do_tour_step = function(index) {
    var bubble = intro_tour.create_bubble(index);
    intro_tour.bind_bubble(bubble, index);
    var dir = intro_tour.place_bubble(bubble, index);
    var bounce_target = $('.bubble', bubble);
    if (dir == "left" || dir == "right") {
        //canvas_effects.wiggle(bounce_target, -1, 400, 2);
    } else if (dir == "up" || dir == "down") {
        //canvas_effects.bob(bounce_target, -1, 400, 2);
    }
    intro_tour.add_highlight(index);
};

intro_tour.remove_hint = function(index) {
    intro_tour.remove_highlight(index);
    intro_tour.steps[index].bubble.remove();
};

intro_tour.next_tour_step = function(index) {
    intro_tour.remove_hint(index);
    index++;
    if (index >= intro_tour.steps.length) {
        return intro_tour.end_tour();
    }
    intro_tour.do_tour_step(index);
};

intro_tour.end_tour = function() {
    intro_tour.unfade_page();
};
