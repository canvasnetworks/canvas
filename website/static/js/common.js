/*
 * jQuery UI Autocomplete HTML Extension
 *
 * Copyright 2010, Scott González (http://scottgonzalez.com)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 *
 * http://github.com/scottgonzalez/jquery-ui-extensions
 */

if ($.ui) {
    (function ($) {
        var proto = $.ui.autocomplete.prototype,
        initSource = proto._initSource;

        function filter (array, term) {
            var matcher = new RegExp($.ui.autocomplete.escapeRegex(term), 'i');
            return $.grep(array, function (value) {
                return matcher.test( $('<div>').html(value.label || value.value || value).text());
            });
        };

        $.extend(proto, {
            _initSource: function () {
                if (this.options.html && $.isArray(this.options.source)) {
                    this.source = function (request, response) {
                        response(filter(this.options.source, request.term));
                    };
                } else {
                    initSource.call(this);
                }
            },
            _renderItem: function (ul, item) {
                return $('<li></li>')
                .data('item.autocomplete', item)
                .append($('<a></a>')[this.options.html ? 'html' : 'text'](item.label))
                .appendTo(ul);
            }
        });
    })(jQuery);
}

/* via http://stackoverflow.com/questions/1595611/how-to-properly-create-a-custom-object-in-javascript#159807 */

Function.prototype.createSubclass = function () {
    function Class () {
        if (!(this instanceof Class)) {
            throw('Constructor called without "new"');
        }
        this.init.apply(this, arguments);
    }
    Function.prototype.createSubclass.nonconstructor.prototype = this.prototype;
    Class.prototype = new Function.prototype.createSubclass.nonconstructor();
    Class.__super__ = this.prototype;
    if (!('init' in Class.prototype)) {
        Class.prototype.init = function () {};
    }
    return Class;
};

Function.prototype.createSubclass.nonconstructor= function () {};

Function.prototype.partial = function (){
    var fn = this, args = Array.prototype.slice.call(arguments);
    return function () {
        return fn.apply(this, args.concat(Array.prototype.slice.call(arguments)));
    };
};

Function.prototype.bind = function (self) {
    var fun = this;
    return function () {
        return fun.apply(self, arguments);
    }
};

String.prototype.strip = function () {
    return this.replace(/^\s+|\s+$/g,"");
};

String.prototype.pluralize = function (count, plural, prepend_number) {
    if (!plural) {
        plural = this + 's';
    }
    var result = count == 1 ? this : plural;
    if (prepend_number !== false) {
        result = count + ' ' + result;
    }
    return result;
};

RegExp.escape = function (text) {
    return text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&");
};

Number.range = function (a,b,c) {
    var start, stop, step;

    if (c !== undefined) {
        start = a; stop = b; step = c;
    } else if (b !== undefined) {
        start = a; stop = b; step = 1;
    } else if (a !== undefined) {
        start = 0; stop = a; step = 1;
    } else {
        throw new Error("Bad Range");
    }

    var results = [];
    for (var i = start; i < stop; i += step) {
        results.push(i);
    }
    return results;
};

$.fn.reverse = function () {
    return this.pushStack(this.get().reverse(), arguments);
};

/* .tmpl() silently fails if the locator doesn't match, that's no good. */
$.fn.tmpl_orig = $.fn.tmpl;
$.fn.tmpl = function () {
    if (this.size() != 1) {
        throw new Error('Template did not match exactly one element, bailing.');
    }
    return $.fn.tmpl_orig.apply(this, arguments);
};

$.fn.bottom = function () {
    return this.position().top + this.height();
};

$.fn.right = function () {
    return this.position().left + this.width();
};

$.fn.bindContent = function (content) {
    if (!content) return;
    var cid = (content.id) ? content.id : content;
    $(this)
        .data("content_id", cid)
        .bind("dragstart", function (evt) {
            evt.originalEvent.dataTransfer.setData("text/plain", "content://" + $(this).data("_id"));
        });
};

$.fn.center = function () {
    this.css("position","absolute");
    this.css("top", ( $(window).height() - this.height() ) / 2+$(window).scrollTop() + "px");
    this.css("left", ( $(window).width() - this.width() ) / 2+$(window).scrollLeft() + "px");
    return this;
};

$.fn.ctx = function () {
    return this[0].getContext('2d');
};

$.fn.getDataURL = function () {
    return this[0].toDataURL('image/png');
};

$.fn.ultimate_parent = function () {
    var element = this.parent();
    var last = element;

    while (element.length) {
        last = element;
        element = element.parent();
    }

    return last;
};

// Via http://stackoverflow.com/a/4702086/348119
$.fn.toggleDisabled = function(toggle_to) {
    return this.each(function() {
        var $this = $(this);
        if (toggle_to === undefined) {
            toggle_to = !$this.attr('disabled');
        }

        if (toggle_to) {
            $this.attr('disabled', 'disabled');
        } else {
            $this.removeAttr('disabled');
        }

        return $this;
    });
};

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Via http://docs.djangoproject.com/en/1.2/ref/contrib/csrf/#csrf-ajax
$('html').ajaxSend(function (event, xhr, settings) {
    if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
        // Only send the token to relative URLs i.e. locally.
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});

var Mode = {};

Mode.delegates = function (prototype /*, ...fun names */) {
    var funs = Array.prototype.slice.call(arguments, 1);
    $.each(funs, function (i, fun) {
        prototype[fun] = function () {
            Mode.delegate(this, fun, arguments);
        }
    });
}

Mode.delegate = function (self, fn, args) {
    if (self.mode === undefined) {
        self.mode = 'start';
    }
    var fun = self.modes[self.mode][fn];
    if (!fun) return;
    var next_mode = fun.apply(self, args);
    if (!next_mode) return;
    self.mode = next_mode;
};

Mode.transition = function (next) {
    return function () { return next; };
};

var Binding = function (name) {
    this.event_class = ".binding_" + Binding.current_id++;
};

Binding.current_id = 1;

Binding.prototype.bind = function (selector, event_name, handler) {
    $(selector)
        .bind(event_name + this.event_class, handler)
        .addClass(this.event_class);

};

Binding.prototype.unbind = function () {
    $(this.event_class)
        .unbind(this.event_class)
        .removeClass(this.event_class);
};

var util = {};

util.fitInside = function (fitw, fith, c) {
    var rw = c.width / fitw;
    var rh = c.height / fith;
    var ratio = Math.max(1, rw, rh);
    return { width: c.width / ratio, height: c.height / ratio };
};

util.fitHeight = function (fith, c) {
    var ratio = fith / c.height;
    return { width: c.width * ratio, height: c.height * ratio };
};

util.fitWidth = function (fitw, c) {
    var ratio = fitw / c.width;
    return { width: c.width * ratio, height: c.height * ratio };
};

util.all = function (array) {
    for (var i = 0; i < array.length; ++i) {
        if (!array[i]) return false;
    }
    return true;
};

util.scatterGather = function (array, each_callback, done_callback) {
    var gather = [];
    $.each(array, function (index, element) {
        gather.push(false);

        var gather_fun = function () {
            if (gather[index]) {
                throw "Done callback called more than once.";
            } else {
                gather[index] = Array.prototype.slice.call(arguments);
                if (util.all(gather)) {
                    done_callback(gather);
                }
            }
        }

        each_callback(index, element, gather_fun);
    });
};

var canvas = {};

canvas.pending_scrolls = [];

// Deprecated (so you just have the crappy array wrapped version)
canvas.log = function () {
    console.log(arguments);
};

if (!window.console) {
    window.console = {};
};

if (!window.console.log) {
    window.console.log = function () {};
};

/*
 * Provide a default value for a textarea/input.
 * It will be gray, disappear when focused, and reappear if left empty on blur.
 */
canvas.init_default_value = function (selector, text) {
    selector.focus(function () {
        if (this.value == text) {
            this.value = "";
            $(this).removeClass("default-value");
        }
    })
    $(selector).blur(function () {
        if (this.value == "" || this.value == text) {
            this.value = text;
            $(this).addClass("default-value");
        }
    })
    $(selector).val(text).addClass("default-value");
};

canvas.scrollToAndHighlight = function (selector, skip_scroll, force_scroll) {
    var this_scroll = function () {
        skip_scroll = true;
        var desired = $(selector);
        var previous_color = desired.css('background-color');

        if (!desired.length) {
            // Skip bad hashtag links, or links to moderated children.
            return;
        }

        function highlightDesired() {
            $(".drop_target_border", desired).addClass("highlight").css({opacity:0}).animate({opacity:1}, 300, 'linear', function () {
                $(this).animate({opacity:0}, 200, 'linear', function () {
                    $(this).removeClass("highlight").css({opacity:1});
                });
            });
        }

        // If the element is on screen, highlight it, otherwise scroll to it.
        if (!force_scroll && desired.offset().top > $(window).scrollTop() + $("#header .top_bar").outerHeight(true) && desired.offset().top + desired.height() < $(window).scrollTop() + $(window).height()) {
            highlightDesired();
        } else {
            var speed = skip_scroll ? 0 : Math.min(2000, Math.abs((desired.offset().top - $(window).scrollTop())/2));
            var offset = -10 -$("#header .top_bar").outerHeight(true);
            $.scrollTo(desired, speed, {'offset': offset, 'onAfter': function () {
                highlightDesired();
            }});
        }
    };

    this_scroll();

    canvas.pending_scrolls.push(this_scroll);

};

canvas.render = function (template, data, options) {
    template = (template[0] == '#') ? template : '#' + template;
    return $(template).tmpl(data, options);
};

canvas._comments = {};

canvas.getComment = function (id) {
    return canvas._comments[id];
};

canvas.base_wires = function () {
    canvas.parse_user_agent();

    // Only wire stickers and header if they exist
    if ($('#sticker_pack').length) {
        sticker_pack.wire();
    }
    if ($("#header").length) {
        header.wire();
    }

    $("body").delegate(".ezselect", "click", function () {
        $(this).select();
    });

    // Auto tooltip stuff
    canvas.loadTooltips();
    $(window).bind("mouseleave mouseoff", function () {
        $(".tooltip").remove();
    });

    // Collapsed posts logic
    $('body').delegate(".collapsed", "click", function () {
        canvas.unhide_collapsed_post($(this));
    });

    // Lazy-loaded content.
    canvas.wire_lazy_images();

    canvas.content_context_menu();

    // This is for changing the favicon, on pageload we grab the default favicon and page title
    canvas.favicon_node = $("head link[rel='shortcut icon']");
    canvas.title_node = $("head title");

    // Sidebar
    sidebar.wire();

    // Always check for sticker animations
    stickers.check_page_for_animations();
};

canvas.base_onload = function () {
    // Must be on load to prevent browser-forever-spinning bugs.
    realtime.subscribe_channels();
    realtime.start();

    setInterval(function () {
        $('span.rel-timestamp').each(function (i, span) {
            var $span = $(span);
            $span.text(canvas.formatDateRelative($span.attr('data-timestamp')));
        })
    }, 60 * 1000);
};

canvas.loadTooltips = function (elm){
    var elements;
    if (elm){
        elements = $(".tooltipped", elm);
    } else {
        elements = $(".tooltipped");
    }
    elements.tooltip();
};

canvas.jsonPOST = function (url, data, success, timeout) {
    args = {
        type: "POST",
        contentType: 'application/json',
        data: JSON.stringify(data),
        url: url,
        timeout: timeout,
    }
    if (success) {
        args.success = success;
    }
    return jQuery.ajax(args);
};

canvas.json_or_null = function (string) {
    try {
        return $.parseJSON(string);
    } catch (err) {
        return null;
    }
}

canvas.on_api_fail = function (data, resp) {
    // Handle forbidden API calls.
    if (resp.status == 403) {
        var data = canvas.json_or_null(resp.responseText);
        if (data && (data.reason == "deactivated" || data.reason == "staff_only")) {
            return;
        }

        canvas.encourage_signup("403", {api_url: url, data: data});
    };
}

canvas.apiPOST = function (url, data, success) {
    /* Deprecated. use canvas_api.js */
    return canvas.jsonPOST('/api' + url, data, success).fail(canvas.on_api_fail.partial(data));
};

canvas.track = function (cat, type, opts) {
    _gaq.push(['_trackEvent', cat, type]);
};

canvas.escape_html = function (value) {
    return $('<div></div>').text(value).html();
};

canvas.base36encode = function (number) {
    // python canvas.util.base36encode

    var alphabet = '0123456789abcdefghijklmnopqrstuvwxyz';
    var checksum = 0

    var base36 = '';
    while (number != 0) {
        i = number % 36;
        number = Math.floor(number / 36);
        checksum += i * 19;
        base36 = alphabet[i] + base36
    }

    return base36 + alphabet[checksum % 36]
};

canvas.unixtime = function () {
    return (new Date()).getTime() / 1000; // Convert ms to seconds.
};

canvas.formatDateRelative = function (timestamp) {
    var now = canvas.unixtime();
    var secondsOff = now - timestamp;
    var val = '';
    var aMinute = 60,
        anHour = 60*60,
        aDay = 60*60*24,
        aWeek = 60*60*24*7,
        aMonth = 60*60*24*30,
        aYear = 60*60*24*365;

    var represent = function (unit, name) {
        var val = Math.floor(secondsOff / unit);
        return name.pluralize(val) + " ago";
    };

    if (secondsOff < aMinute) {
        val = "a moment ago";
    } else if (secondsOff < anHour) {
        val = represent(aMinute, "minute");
    } else if (secondsOff < aDay) {
        val = represent(anHour, "hour");
    } else if (secondsOff < aWeek) {
        val = represent(aDay, "day");
    } else if (secondsOff < aMonth){
        val = represent(aWeek, "week");
    } else if (secondsOff < aYear) {
        val = represent(aMonth, "month");
    } else {
        val = represent(aYear, "year");
    }
    return val;
};

canvas.preload_image = function (image_url, callback) {
    var image = new Image();
    image.onload = function (evt) {
        setTimeout(callback.partial(image), 0);
    };
    image.src = image_url;
};

canvas.parse_curi = function (uri) {
    var matches = String(uri).match("^content://(.*)$");
    if (!matches) {
        return null;
    } else {
        return matches[1];
    }
};

canvas.Image = function (attrs) {
    if (attrs) {
        this.width = attrs.width;
        this.height = attrs.height;
        if (attrs.name !== undefined) {
            this.name = attrs.name;
            var prefix = this.name.substr(0,4);
            if (prefix == "http" || prefix == "/ugc") {
                this.url = this.name;
            } else {
                this.url = "/ugc/" + this.name;
            }
        } else {
            this.url = attrs.url;
        }
        this.kb = attrs.kb;
        this.animated = attrs.animated;
    }
};

canvas.Content = function (content) {
    this.id = content.id;
    this.remix_of_giant_url = content.remix_of_giant_url;
    this.timestamp = content.timestamp;
    for (var i = 0; i < canvas.Content.types.length; ++i) {
        var type = canvas.Content.types[i];
        if (content[type]) {
            this[type] = new canvas.Image(content[type]);
        }
    }
    if (!content.ugc_original && content.original) {
        content.ugc_original = content.original;
    }
    this.remix_text = content.remix_text;
    this.stamps_used_url = "/stamps_used/" + content.id;
};

canvas.Content.types = ['original', 'tiny_square', 'small_square', 'medium_square', 'thumbnail', 'stream', 'square', 'big_square', 'small_column', 'explore_column', 'column', 'giant', 'footer', 'jpeg_column', 'jpeg_stream', 'ugc_original', 'homepage_mobile', 'homepage_small', 'homepage_large', 'homepage_giant', 'gallery', 'homepage_featured', 'archive', 'activity'];

canvas.Content.prototype.bindToImage = function (element, view) {
    var info = this[view];
    var prefix = info.name.substr(0,4);
    var url = info.name;
    if (prefix != "http" && prefix != "/ugc") {
        url = "/ugc/" + info.name;
    }
    $(element).attr('width', info.width);
    $(element).attr('height', info.height);
    $(element).attr('src', url);
    $(element).bindContent(this);
};

canvas.Content.prototype.getUrl = function (view) {
    var name = this[view].name;
    return '/ugc/' + name;
};

canvas._contentCache = {};

canvas.storeContent = function (data) {
    if (data) {
        var content = new canvas.Content(data);
        if (canvas._contentCache[content.id]) {
            return canvas._contentCache[content.id];
        }
        canvas._contentCache[content.id] = content;
        return content;
    }
    return null;
};

canvas.getContent = function (id) {
    return canvas._contentCache[id];
};

canvas.lastUID = 0;
canvas.getUID = function () {
    return canvas.lastUID++;
};

var tmpl = {};

tmpl.sizeAttrs = function (content, a, b, css) {
    if (a === undefined && b === undefined) {
      // Do nothing
    } else if (b === undefined || b === 'height') {
        content = util.fitHeight(a, content);
    } else if (b === 'width') {
        content = util.fitWidth(a, content);
    } else if (a !== undefined) {
        content = util.fitInside(a, b, content);
    }

    if (css) {
        return "width: " + content.width + "px; height:" + content.height + "px;";
    } else {
        return 'width="' + content.width + '" height="' + content.height +  '"';
    }
};

tmpl.content = function (content_id, stream, a, b) {
    var content = canvas.getContent(content_id);
    if (!content) return "";
    var info = content[stream];
    return "<img src='" + info.name + "' " + tmpl.sizeAttrs(info, a, b) + " >";
};

tmpl.sticker = function (type_id) {
    return '<span class="sticker_container ' + current.stickers[type_id].name + ' shadow" data-type_id="' + type_id + '"></span>';
};

//TODO delete
tmpl.remix_js_link = function (comment) {
    return "javascript:action.remix('" + comment.getContent().id + "', 'thread_footer_link'); if (thread && thread.pw) { thread.pw.remix_started(); }";
};

tmpl.range = function (count) {
    var array = [];
    for (var i=0; i < count; i++) {
        array.push(i);
    }
    return array;
};

_ugc_text_count = 0;


/**
 * Performs common/desired manipulations to ugc text
 * @returns text/html
 */
tmpl.ugc_text = function (text, max_length, should_oembed, should_not_linkify) {
    max_length = (max_length === undefined) ? 140 : max_length;
    // Truncate the text if necessary, adding an ellipsis.
    if (text.length > max_length) {
        text = text.slice(0, max_length) + '…';
    }

    // Escape <tag> <shenanigans/>
    text = $('<div/>').text(text).html();
    // Enter means newline bitch
    text = text.replace(/\n/g, "<br/>");
    // Make http://google.com be a link
    var found_oembed = false;

    var ugc_text_id = "ugc_text_" + (_ugc_text_count++);
    var html = '<span id="' + ugc_text_id + '" class="ugc_text">';


    // Replace all #foobar forms with http://example.com/x/foobar, but not '#', '#1', '#1-ocle', et cetera.
    text = text.replace(/\B\#(\w{3,})/g, window.location.host+'/x/$1');

    linkifyOptions = {callback: function (text, href) {
        // Replace the text of http://example.com/x/foobar links with #foobar
        var grouplink = text.match(RegExp.escape(window.location.host+'/x/')+'(\\w{3,})');
        if (grouplink) {
            text = "#" + grouplink[1];
        }

        // Make sure to encodeURI here, otherwise http://xss.com/"onmouseover=alert('XSS');// is total XSS.
        return href ? '<a href="' + encodeURI(href) + '" title="' + encodeURI(href) + '" target="_blank" rel="nofollow">' + text + '</a>' : text;
    }};
    html += (should_not_linkify) ? text : linkify(text, linkifyOptions);
    html += '</span>'
    return html;
};

tmpl.relative_timestamp = function (timestamp) {
    human_time = canvas.formatDateRelative(timestamp);
    return "<span class='rel-timestamp' data-timestamp='" + timestamp + "'>" + human_time + "</span>";
};

var local = {};

local.events = {};

local.bind = function (key, handler) {
    $(local.events).bind(key, function (evt, value, change) { handler(value, change); });
};

local.one = function (key, handler) {
    $(local.events).bind(key, function (evt, value, change) {
        if (!change) {
            handler(value, change);
        }
    });
};

local.trigger = function (key, value, change) {
    if (typeof change === 'undefined') {
        change = true;
    }
    $(local.events).trigger(key, [value, change]);
};

local.get = function (key, def) {
    return $.jStorage.get(key, def);
};

local.set = function (key, value) {
    if (local.get(key) != value) {
        local._set(key, value, true);
    }
};

local._set = function (key, value, change) {
    $.jStorage.set(key, value);
    local.trigger(key, value, change);
};

local.toggle = function (key) {
    local.set(key, !local.get(key, false));
};

local.init = function (defaults) {
    $.each(defaults, function (key, def) {
        local._set(key, local.get(key, def), false);
    });
};

local.wire = function () {
    local.init({
        'drawer-query': 'puppies',
    });
};

var action = {};

canvas.ForeignContent = function (thumburl, tw, th, src) {
    this.thumbnail = new canvas.Image({
        url: thumburl,
        width: tw,
        height: th
    });
    this.original = new canvas.Image({
        url: src
    });
    this.foreign = true;
};

canvas._stashedImages = {};

canvas.getStashedImage = function (id) {
    return canvas._stashedImages[id];
};

canvas.loadStashedImage = function (data) {
    var sc = new canvas.StashedImage(data);
    canvas._stashedImages[sc.id] = sc;
    return sc;
};

canvas.StashedImage = function (obj) {
    for (var key in obj) {
        this[key] = obj[key];
    }
};

canvas.StashedImage.prototype.removeFromStash = function () {
    canvas.apiPOST(
        '/stash/' + this.id.toString() + '/delete',
        {},
        function (result) {
            jQuery.publish("stash.refresh");
        }
    );
};

canvas.animateGif = function (content_id, image_container, image_type) {
    if ($(".animated_hint", image_container).is(".pause")) {
        // Pause gif
        image_container.addClass("loading");
        var static_url = canvas.getContent(content_id)[image_type].url;
        // Preload static image
        $('<img />').attr('src', static_url).load(function (){
            if (image_container.is(".loading")) {
                $("img", image_container).attr("src", static_url).data("original", static_url);
                image_container.removeClass("loading");
                $(".animated_hint", image_container).removeClass("pause");
            }
        });
    } else if (image_container.is(".loading")) {
        // Cancel and go back to whatever it was
        image_container.removeClass("loading");
        var desired_url = ($(".animated_hint", image_container).is(".pause")) ? canvas.getContent(content_id).ugc_original.url : canvas.getContent(content_id)[image_type].url;
        $("img", image_container).attr("src", desired_url);
    } else {
        // Animate gif
        image_container.addClass("loading");
        var gif_url = canvas.getContent(content_id).ugc_original.url;
        // Preload animation
        $('<img />').attr('src', gif_url).load(function (){
            if (image_container.is(".loading")) {
                $("img", image_container).attr("src", gif_url).data("original", gif_url);
                image_container.removeClass("loading");
                $(".animated_hint", image_container).addClass("pause");
            }
        });
    }
};

canvas.ensure_facebook = function (fun) {
    if (window.FB === undefined || window.FB.login === undefined) {
        alert("Unable to communicate with Facebook. Please disable any Facebook blocking plugins or extensions and then refresh the page.");
    } else {
        fun();
    }
};

canvas.record_metric = function (name, info) {
    info = info || {};
    if (info.url) {
        throw "Can't pass a `url` field inside `info` when recording a metric, since it gets overridden.";
    }
    info.url = window.location.href;
    canvas.apiPOST(
        '/metric/record',
        { name: name, info: info }
    );
};

canvas.record_fact = function (type, info) {
    info = info || {};
    if (info.url) {
        throw "Can't pass a `url` field inside `info` when recording a fact, since it gets overridden.";
    }
    info.url = window.location.href;
    canvas.apiPOST(
        '/fact/record',
        { type: type, info: info }
    );
};

canvas.get_meta_key_name = function () {
    return navigator.platform.match("^Mac") ? 'cmd' : 'ctrl';
};

canvas.level_up = function () {
    canvas.apiPOST('user/level_up', {}, function (response) {});
};

canvas.keycode_is_valid = function (keycode) {
    var unwanted_codes = [9, 13, 16, 17, 37, 38, 39, 40, 91, 224];
    for (var i = 0; i < unwanted_codes.length; i++) {
        if (keycode == unwanted_codes[i]) {
            return false;
        }
    }
    return true;
};

canvas.bind_label_to_input = function (input) {
    var label = input.parent().children("label");
    input.bind("keyup", function (e) {
        var self = $(this);
        if (!self.val()) {
            self.parent().children("label").removeClass("hidden");
        }
    })
    .bind("keydown", function (e) {
        if (canvas.keycode_is_valid(e.keyCode)) {
            $(this).parent().children("label").addClass("hidden");
        }
    })
    .bind("focus", function () {
        $(this).parent().children("label").addClass("active");
    })
    .bind("blur", function () {
        // Check if clicking a submit button has cleared the field
        // We have to set a timeout because the blur is triggered first :/
        var self = $(this);
        self.parent().children("label").removeClass("active");
        setTimeout(function() {
            self.trigger("keyup");
        }, 100);
    });

    label.bind("click", function() {
        $(this).parent().children("input").focus();
    });
    
    var check_if_inputs_have_value = function() {
        input.each(function(_, node) {
            node = $(node);
            if (node.val()) {
                node.parent().children("label").addClass("hidden");
            }
        });
    };
    // Immediate check if we have a value
    check_if_inputs_have_value();

    // Chrome isn't perfect :/
    // Check to see if we need to hide the labels because of autofill
    $(window).load(function(){
        setTimeout(check_if_inputs_have_value, 500);
    });
};

canvas.trigger_scroll = function () {
    $(window).triggerHandler("scroll");
};

canvas.remove_context_menus = function() {
    $("body").undelegate(".image_container", "contextmenu");
};

canvas.content_context_menu = function () {
    $("body").delegate(".image_container", "contextmenu", function (e) {
        var downloadify_url = function (ugc_url) {
            return ugc_url.replace('/ugc/','/ugc_download/');
        };

        var container = $(this);
        var parent_node = container.parents(".reply");
        var context_type = "reply";
        if (!parent_node.length) {
            parent_node = container.parents(".image_tile");
            var context_type = "image_tile";
        }
        if (!parent_node.length) {
            parent_node = container.parents(".explore_tile");
            var context_type = "explore_tile";
        }
        if (!parent_node.length) {
            parent_node = container.parents(".thread_comment");
            var context_type = "thread_comment";
        }
        if (!parent_node.length) return true;
        var comment_id = parent_node.data("comment_id");
        var content_id = container.attr("id") || container.data("content-id") || container.data("content_id");
        var comment = canvas.getComment(comment_id);
        var content = canvas.getContent(content_id);
        var new_context = (canvas.user_agent.browser_name == "Safari") ? "Window" : "Tab";
        var footered_url = (typeof content.footer !== 'undefined' && content.footer) ? content.footer.name : content.ugc_original.url;
        var menu_options = [
            {
                text    : "Open Image in New " + new_context,
                action  : function () {
                    window.open(footered_url, '_blank');
                }
            },
            {
                text    : "Save Image...",
                action  : function () {
                    if (content.footer) {
                        window.open(downloadify_url(content.footer.name), "_blank");
                    } else {
                        window.open(downloadify_url(content.ugc_original.name), "_blank");
                    }
                }
            },
            {
                text    : "Copy Image URL",
                action  : function () {},
                copy    : function () {
                    return footered_url;
                },
            },
            {
                text    : "Search Google with this Image",
                action  : function () {
                    window.open("http://www.google.com/searchbyimage?image_url=" + content.ugc_original.url, "_blank");
                }
            },
            {
                text    : "Remix Image",
                action  : (function () {
                    if (action.remix) {
                        return function () {
                            action.remix(content_id, 'context_menu');
                            if (window.thread && thread.pw) {
                                thread.pw.remix_started();
                            }
                            if (window.thread_new && thread_new.pw) {
                                thread_new.pw.remix_started();
                            }
                        }
                    } else {
                        return function () {
                            location.href=comment.getCommentURL() + "#remix";
                        }
                    }
                })(),
            },
            {
                text    : "Audio Remix",
                action  : (function() {
                    if (action.audio_remix) {
                        return function() {
                            action.audio_remix(comment_id, content_id, 'context_menu');
                            if (window.thread && thread.pw) {
                                thread.pw.remix_started();
                            }
                            if (window.thread_new && thread_new.pw) {
                                thread_new.pw.remix_started();
                            }
                        }
                    } else {
                        return function() {
                            location.href=comment.getCommentURL() + "#audio_remix";
                        }
                    }
                })(),
            },
        ];
        if (current.userinfo.is_staff) {
            menu_options.push({
                text    : "Show Stamps",
                action  : function () {
                    window.open(content.stamps_used_url, '_blank');
                }
            });
        }
        // Open thread option on right click for browse.
        if (parent_node.hasClass("image_tile") || parent_node.hasClass("explore_tile")) {
            menu_options.unshift({
                text    : "Open Thread in New " + new_context,
                action  : function () {
                    var url = $(".content_link", parent_node).attr("href");
                    if (!url) {
                        url = comment.getCommentURL();
                    }
                    window.open(url, "_blank");
                }
            });
        }


        return canvas.show_context_menu(e, menu_options);
    });
};

canvas.show_context_menu = function (e, menu_options) {
    if (e.shiftKey) {
        return true;
    }
    var menu = $('<div class="context_menu"><span class="hint">shift + right click for default menu</span></div>');
    var modal = $('<div class="modal_container"></div>');

    var fade_menu = function () {
        modal.remove();
        menu.animate({opacity: 0}, 200, function () {
            $(this).remove();
        });
    };

    var choose_menu_item = function (i) {
        menu_options[i].action();
        fade_menu();
    };

    modal.appendTo(document.body)
        .css({
            zIndex: 100,
            background: "transparent",
        });

    menu.appendTo(document.body)
        .css({
            left: e.pageX,
            top: e.pageY,
            zIndex: 101,
        })
        .bind("mousedown", function () {
            $(this).unbind("mouseup");
        })
        .bind("contextmenu click", function (e) {
            var target = $(e.target);
            if (target.is("li")) {
                choose_menu_item(target.data("menu-num"));
            } else {
                fade_menu();
            }
            return false;
        })
        .bind("mouseup", function (e) {
            var target = $(e.target);
            if (target.is("li")) {
                choose_menu_item(target.data("menu-num"));
            }
        });

    modal.one("click contextmenu", function () {
        fade_menu();
        return false;
    });

    var ul = $('<ul></ul>');

    $.each(menu_options, function (i, menu_option) {
        if (menu_option.copy && !swfobject.hasFlashPlayerVersion('8')) {
            return true;
        }

        var li = $('<li class="menu_option_' + i + '" data-menu-num="' + i + '">' + menu_option.text + '</li>');
        li.appendTo(ul);

        if (menu_option.copy) {
            setTimeout(function () {
                li.zclip({
                    copy: function () {
                        return menu_option.copy();
                    },
                });
            }, 10);
        }
    });
    ul.prependTo(menu);

    return false;
};

canvas.change_favicon = function (url, title) {
    $("head link[rel='shortcut icon']").remove();
    $('<link rel="shortcut icon" type="image/png" href="' + url + '">').appendTo("head");

    if (title) {
        $("head title").remove();
        $('<title>' + title + '</title>').appendTo("head");
    }
};

canvas.reset_favicon = function () {
    $("head link[rel='shortcut icon']").remove();
    $("head title").remove();
    canvas.favicon_node.appendTo("head");
    canvas.title_node.appendTo("head");
};

canvas.get_content_formatting = function (container, options) {
    var formatting = {}
    var target_image = container.children("img");
    var img_width = "auto";
    var img_height = "auto";
    if (target_image.length) {
        var img_width = (options.img_width) ? options.img_width : target_image[0].getAttribute("width");
        var img_height = (options.img_height) ? options.img_height : target_image[0].getAttribute("height");
    }
    var container_width = (options.container_width) ? options.container_width : container.width();
    if (!container_width && options.image_type) {
        switch (options.image_type) {
            case "giant":
                container_width = 600;
                break;
            case "column":
                container_width = 250;
                break;
            case "small_column":
                container_width = 150;
                break;
            default:
                container_width = 250;
                break;
        }
    }
    var size_threshold = (options.threshold) ? options.threshold : container_width/5;
    // If the image is larger than the container, reformat it
    if (img_width > container_width) {
        formatting.img_width = container_width;
        formatting.img_height = img_height/(img_width/container_width);
        formatting.container_padding = 0;
    // If it's too small to strech, center the image vertically by padding
    } else if (img_width < container_width) {
        formatting.img_width = img_width;
        formatting.img_height = img_height;
        formatting.container_padding = Math.min((container_width - img_width)/2, size_threshold/2);
    } else {
        formatting.img_width = img_width;
        formatting.img_height = img_height;
        formatting.container_padding = 0;
    }
    return formatting
};

canvas.format_comment_content = function (rendered_comment, image_type) {
    var container = $(".image_container", rendered_comment);
var formatting = canvas.get_content_formatting(container, {"image_type": image_type}),
        target_image = container.children("img");

    container.css({
        paddingTop: formatting.container_padding,
        paddingBottom: formatting.container_padding,
    });
    target_image.css({
        width: formatting.img_width,
        height: formatting.img_height,
    });
    if (formatting.container_padding) {
        target_image.addClass("small_image");
    }
};

canvas.wire_invite_remixers = function () {
    var widgets = $('.invite_remixers'); // Expect multiple of these
    if (widgets.length == 0) {
        return false;
    }
    canvas.bind_label_to_input($('.internal input', widgets));
    var url_input = $('.invite_remixers .arbitrary input.invite_url');
    var copy_buttons = $('.invite_remixers .arbitrary .copy_text');
    var hidden_containers = copy_buttons.closest('.hidden');
    hidden_containers.removeClass('hidden');
    copy_buttons.zclip({
        copy: function () {
            return url_input.val();
        },
    });
    hidden_containers.addClass('hidden');

    $('header', widgets).click(function() {
        $('.invite_options', widgets).toggle();
        widgets.toggleClass("collapsed");
    });
};

/*
 * Title Caps
 *
 * Ported to JavaScript By John Resig - http://ejohn.org/ - 21 May 2008
 * Original by John Gruber - http://daringfireball.net/ - 10 May 2008
 * License: http://www.opensource.org/licenses/mit-license.php
 */

(function () {
    var small = "(a|an|and|as|at|but|by|en|for|if|in|of|on|or|the|to|v[.]?|via|vs[.]?)";
    var punct = "([!\"#$%&'()*+,./:;<=>?@[\\\\\\]^_`{|}~-]*)";

    this.titleCaps = function (title) {
        var parts = [], split = /[:.;?!] |(?: |^)["Ò]/g, index = 0;

        while (true) {
            var m = split.exec(title);

            parts.push( title.substring(index, m ? m.index : title.length)
                .replace(/\b([A-Za-z][a-z.'Õ]*)\b/g, function (all) {
                    return /[A-Za-z]\.[A-Za-z]/.test(all) ? all : upper(all);
                })
                .replace(RegExp("\\b" + small + "\\b", "ig"), lower)
                .replace(RegExp("^" + punct + small + "\\b", "ig"), function (all, punct, word) {
                    return punct + upper(word);
                })
                .replace(RegExp("\\b" + small + punct + "$", "ig"), upper));

            index = split.lastIndex;

            if ( m ) parts.push( m[0] );
            else break;
        }

        return parts.join("").replace(/ V(s?)\. /ig, " v$1. ")
            .replace(/(['Õ])S\b/ig, "$1s")
            .replace(/\b(AT&T|Q&A)\b/ig, function (all) {
                return all.toUpperCase();
            });
    };

    function lower (word) {
        return word.toLowerCase();
    }

    function upper (word) {
      return word.substr(0,1).toUpperCase() + word.substr(1);
    }
})();

/**
 * A way to fire custom global events on the document body.
 * @param event
 * @param data
 */
canvas.fire = function (event, data){
    $(document.body).trigger(event, data);
};

/**
 * Listens for custom global evnets on the document body.
 *
 */
canvas.listen = function (event, handler){
    return $(document.body).bind(event, handler);
};

// Text input character counter
canvas.CharCounter = function () {
    this.settings = {
        counter             : $(),
        deficit_class       : "charcount_deficit",
        surplus_class       : "charcount_surplus",
        valid_class         : "charcount_valid",
        validated_event     : "charcount_validated",
        invalidated_event   : "charcount_invalidated",
    }
};

canvas.CharCounter.prototype.init = function (settings) {
    /* Settings object to pass in:
    settings = {
        min: minimum number of characters,
        max: maximum number of characters,
        input_field: textfield element as jQuery object,
        counter: jQuery object to update with count,
        deficit_class: class name to give to counter that has too few characters,
        valid_class: class name to give to counter with valid number of characters,
        surplus_class: class name to give to counter with too many characters,
        invalidated_event: event name triggered when the input becomes invalid,
        validated_event: event name triggered when the input becomes valid,
        count_down: if true, it will display characters remaining instead,
    }
    */
    this.settings = $.extend({}, this.settings, settings);

    // Set the class of the counter
    if (this.char_count < this.settings.min) {
        this.settings.counter.addClass(this.settings.deficit_class);
    } else if (this.char_count > this.settings.max) {
        this.settings.counter.addClass(this.settings.surplus_class);
    } else {
        this.settings.counter.addClass(this.settings.valid_class);
    }
    this.char_count = this.settings.input_field.val().length;
    this.update_counter();

    // Bind keyup to check character count
    var that = this;
    this.settings.input_field.bind("keypress keyup", function (e) {
        that.get_char_count(e);
    });
};

canvas.CharCounter.prototype.get_char_count = function (e) {
    this.char_count = this.settings.input_field.val().length;
    this.update_counter();
};

canvas.CharCounter.prototype.update_counter = function () {
    if (!this.settings.count_down) {
        this.settings.counter.text(this.char_count);
    } else {
        this.settings.counter.text(this.settings.max - this.char_count);
    }
    if (this.char_count < this.settings.min) {
        this.settings.counter
            .addClass(this.settings.deficit_class)
            .removeClass(this.settings.valid_class + " " + this.settings.surplus_class);
        this.settings.input_field.trigger(this.settings.invalidated_event);
    } else if (this.char_count > this.settings.max) {
        this.settings.counter
            .addClass(this.settings.surplus_class)
            .removeClass(this.settings.deficit_class + " " + this.settings.valid_class);
        this.settings.input_field.trigger(this.settings.invalidated_event);
    } else if (this.char_count >= this.settings.min && this.char_count <= this.settings.max){
        this.settings.counter
            .addClass(this.settings.valid_class)
            .removeClass(this.settings.deficit_class + " " + this.settings.surplus_class);
        this.settings.input_field.trigger(this.settings.validated_event);
    }
};

canvas.toggle_share_options = function (target) {
    target = $(target);
    var sharing_wrapper = target.parents(".reply_sharing");
    var extras_wrapper = $('.extra_options', sharing_wrapper);

    var show = function () {
        extras_wrapper.fadeIn(100);
        target.addClass("active");
        setTimeout(function () {
            $("body").one("click", hide);
        }, 1);
        sharing_wrapper.addClass("active");
    };
    var hide = function () {
        extras_wrapper.fadeOut(100);
        target.removeClass("active");
        sharing_wrapper.removeClass("active");
    };
    if (target.hasClass("active")) {
        hide();
    } else {
        show();
    }
};

canvas.unhide_collapsed_post = function (target) {
    if (target.hasClass("reply") && target.hasClass("collapsed")) {
        target.removeClass('collapsed');
        // Special case to reset remix slider for hidden OP
        if (rendered_comment.is(".comment_op")) {
            thread.setupRemixSlider($("#op .slider_handle"));
        }
    } else if (target.hasClass("image_tile")) {
        target.removeClass("collapsed downvoted");
    }
};

canvas.remove_line_breaks = function (string) {
    return string.replace(/(\r\n|\n|\r)/gm,"");
};

canvas.share_url = function (type_id, share_url) {
    var name = current.stickers[type_id].name;
    var prefix = "http://example.com";
    share_url = prefix + share_url;
    canvas.record_metric('share', { 'is_expanded': false, 'share_url':share_url });
    canvas.record_metric(name, { 'is_expanded': false, 'share_url':share_url });

    if (name == 'facebook') {
        var facebook_url = share_url
        window.open('http://www.facebook.com/sharer.php?u=' + encodeURIComponent(facebook_url), "facebook_share", "width=600, height=300");
    } else if (name == 'twitter') {
        var message = "I just posted to Canvas!"
        message = message + " " + share_url;
        window.open('http://twitter.com/intent/tweet?text=' + encodeURIComponent(message), "twitter_share", "width=600, height=400");
    }
};

canvas.prevent_scroll_bubbling = function (selector) {
    /* Via http://stackoverflow.com/questions/5802467/prevent-scrolling-of-parent-element */
    $(selector).bind('mousewheel', function (e, d) {
        if (d > 0 && $(this).scrollTop() == 0) {
            e.preventDefault()
        } else if (d < 0 &&  $(this).scrollTop() == $(this).get(0).scrollHeight - $(this).innerHeight()) {
            e.preventDefault()
        }
    });
};

canvas.prevent_scroll_propagation = function(node) {
    node = $(node);
    node.bind('mousewheel DOMMouseScroll', function (e) {
        if (parseInt($(this).outerHeight()) >= parseInt($(this).css("max-height"))) {
            var delta = e.wheelDelta || -e.detail;
            this.scrollTop += ( delta < 0 ? 1 : -1 ) * 40;
            e.preventDefault();
        }
    });
};

canvas.parse_user_agent = function () {
    var agent = {};

    agent.init = function () {
        agent.browser = agent.search_string(agent.data_browser) || "An unknown browser";
        agent.version = agent.search_version(navigator.userAgent) ||
                        agent.search_version(navigator.appVersion) ||
                        "an unknown version";
        agent.os = agent.search_string(agent.data_os) || "and unknown OS";
    };

    agent.search_string = function (data) {
        for (var i=0; i < data.length; i++) {
            var data_string = data[i].string;
            var data_prop = data[i].prop;
            var data_identity = data[i].identity;
            var data_version_search = data[i].version_search;
            var data_sub_string = data[i].sub_string;
            agent.version_search_string = data_version_search || data_identity;
            if (data_string) {
                if (data_string.indexOf(data_sub_string) != -1) {
                    return data_identity;
                }
            } else if (data_prop) {
                return data_identity;
            }
        }
    };

    agent.search_version = function (data_string) {
        var index = data_string.indexOf(agent.version_search_string);
        if (index == -1) {
            return;
        }
        return parseFloat(data_string.substring(index+agent.version_search_string.length + 1));
    };

    agent.data_browser = [
        {
            string: navigator.userAgent,
            sub_string: "Chrome",
            identity: "Chrome"
        },
        {   string: navigator.userAgent,
            sub_string: "OmniWeb",
            versionSearch: "OmniWeb/",
            identity: "OmniWeb"
        },
        {
            string: navigator.vendor,
            sub_string: "Apple",
            identity: "Safari",
            versionSearch: "Version"
        },
        {
            prop: window.opera,
            identity: "Opera",
            versionSearch: "Version"
        },
        {
            string: navigator.vendor,
            sub_string: "iCab",
            identity: "iCab"
        },
        {
            string: navigator.vendor,
            sub_string: "KDE",
            identity: "Konqueror"
        },
        {
            string: navigator.userAgent,
            sub_string: "Firefox",
            identity: "Firefox"
        },
        {
            string: navigator.vendor,
            sub_string: "Camino",
            identity: "Camino"
        },
        {   // for newer Netscapes (6+)
            string: navigator.userAgent,
            sub_string: "Netscape",
            identity: "Netscape"
        },
        {
            string: navigator.userAgent,
            sub_string: "MSIE",
            identity: "Explorer",
            versionSearch: "MSIE"
        },
        {
            string: navigator.userAgent,
            sub_string: "Gecko",
            identity: "Mozilla",
            versionSearch: "rv"
        },
        {       // for older Netscapes (4-)
            string: navigator.userAgent,
            sub_string: "Mozilla",
            identity: "Netscape",
            versionSearch: "Mozilla"
        },
    ];
    agent.data_os = [
        {
            string: navigator.platform,
            sub_string: "Win",
            identity: "Windows"
        },
        {
            string: navigator.platform,
            sub_string: "Mac",
            identity: "Mac"
        },
        {
            string: navigator.userAgent,
            sub_string: "iPhone",
            identity: "iPhone/iPod"
        },
        {
            string: navigator.platform,
            sub_string: "Linux",
            identity: "Linux"
        },
    ];

    agent.init();
    canvas.user_agent = {
        os              : agent.os,
        browser_name    : agent.browser,
        browser_version : agent.version,
    };
};

canvas.compare_arrays = function (arr1, arr2) {
    return $(arr1).not(arr2).get().length == 0 && $(arr2).not(arr1).get().length == 0;
};

canvas.is_chrome = function () {
    return /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
};

canvas.encourage_signup = function(reason, info) {
    this.info = info || {};
    this.info.reason = reason;
    canvas.record_metric('login_wall', info);

    // TODO: We should put this somewhere else, re-think dialog.js
    var signup_form_node = $('#signup_prompt');
    signup_form_node.show().css("z-index", 4);

    // We have to bind this up manually since we're not using dialog.js
    var modal = $('.modal', signup_form_node);
    modal.show();
    var modal_w = modal.outerWidth();
    var modal_h = modal.outerHeight();
    var window_w = $(window).width();
    var window_h = $(window).height();
    modal.css({
        left    : (window_w - modal_w)/2 + "px",
        top     : (window_h - modal_h)/2 + "px",
    });
    signup_form_node.bind("click", function(e) {
        if (!$(e.target).parents('.modal').length || $(e.target).hasClass("close") || $(e.target).parents(".close").length) {
            signup_form_node.hide();
            signup_form_node.unbind("click");
        }
    });

    var signup_form = signup_new.wire(signup_form_node);
    return signup_form_node;
};
