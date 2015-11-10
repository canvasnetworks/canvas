smooth_scroll = {};

smooth_scroll.detach_item = function(item) {
    item.stub = $('<div class="stub ' + smooth_scroll.settings.selector + '" style="height:' + item.height + 'px;"></div>');
    item.stub.insertAfter(item.node);
    item.node.detach();
    item.loaded = false;
};

smooth_scroll.reattach_item = function(item) {
    item.node.insertAfter(item.stub);
    item.stub.remove();
    item.stub = null;
    item.loaded = true;
};

smooth_scroll.check_for_unload_or_load = function() {
    var top_threshold = smooth_scroll.settings.top_threshold;
    var bottom_threshold = smooth_scroll.settings.bottom_threshold;
    var window_top = $(window).scrollTop();
    var window_bottom = window_top + $(window).height();
    for (var i = 0; i < smooth_scroll.collection.length; i ++) {
        var item = smooth_scroll.collection[i];
        var above = window_top - (item.top + item.height);
        var below = item.top - window_bottom;

        // Check if we detach
        if (item.loaded && (above > top_threshold || below > bottom_threshold)) {
            smooth_scroll.detach_item(item);
        }
        // Check if we reattach
        else if (!item.loaded && above < top_threshold && below < bottom_threshold) {
            smooth_scroll.reattach_item(item);
        }
    }
};

smooth_scroll.add_items = function(collection) {
    for (var i = 0; i < collection.length; i++) {
        var node = $(collection[i]);
        smooth_scroll.collection.push({
            node    : node,
            top     : node.offset().top,
            height  : node.outerHeight(),
            stub    : null,
            loaded  : true,
        });
    }
};

smooth_scroll.get_item_from_node = function(node) {
    for (var i = 0; i < smooth_scroll.collection.length; i++) {
        var item = smooth_scroll.collection[i];
        if (node[0] === item.node[0]) {
            return item;
        }
    }
    return false
};

smooth_scroll.recalculate_height = function(node) {
    var item = smooth_scroll.get_item_from_node(node);
    item.height = item.node.outerHeight();
};

smooth_scroll.wire = function(params) {
    var default_settings = {
        selector            : "",
        top_threshold       : 1000,
        bottom_threshold    : 1500,
        scroll_timeout      : 200,
    }
    smooth_scroll.settings = $.extend({}, default_settings, params);
    smooth_scroll.collection = [];

    if (smooth_scroll.settings.selector.length) {
        smooth_scroll.add_items($('.' + smooth_scroll.settings.selector));
    }

    $(window).bind("scroll", function() {
        if (smooth_scroll.scroll_timer) {
            clearTimeout(smooth_scroll.scroll_timer);
        }
        smooth_scroll.scroll_timer = setTimeout(smooth_scroll.check_for_unload_or_load, smooth_scroll.settings.scroll_timeout);
    });
    $("body").delegate("." + smooth_scroll.settings.selector, "sticker_resize", function() {
        smooth_scroll.recalculate_height($(this));
    });
};
