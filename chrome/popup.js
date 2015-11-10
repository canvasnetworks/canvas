var MIN_WIDTH  = 50;
var MIN_HEIGHT = 50;
var MIN_AREA   = MIN_WIDTH * MIN_HEIGHT * 2;
var MAX_RATIO  = 4;

var existing_image_urls = [];


var validate_image = function (image_url) {
    var def = $.Deferred();

    if (existing_image_urls.indexOf(image_url) !== -1) {
        def.reject();
    }
    existing_image_urls.push(image_url);

    var image = $('<img>').attr('src', image_url);

    image.imagesLoaded().done(function (image) {
        if (typeof image === 'undefined') {
            def.reject();
        }

        image = $(image);
        if (!image.length) {
            def.reject();
        }

        var width = image.get(0).width, height = image.get(0).height;
        if (width  < MIN_WIDTH           ||
            height < MIN_HEIGHT          ||
            width  * height < MIN_AREA   ||
            width  / height > MAX_RATIO  ||
            height / width  > MAX_RATIO) {
            def.reject();
        }

        def.resolve(image);
    }).fail(function () {
        def.reject();
    });

    return def;
};

var get_image = function (image_url) {
    var def = $.Deferred();

    validate_image(image_url).done(function (image) {
        var width = image.get(0).width;
        var height = image.get(0).height

        def.resolve({
            node: image,
            width: width,
            height: height,
            area: width * height,
        });
    }).fail(function () {
        def.reject();
    });

    return def;
};

var parse_url = function (url) {
    var l = document.createElement("a");
    l.href = url;
    return l;
};

var show_no_images_message = function () {
    $('#loading').hide();
    $('#images').hide();
    $('#no_images').show();
};

var show_repost_message = function (options) {
    if (typeof options === 'undefined') { options = {}; }
    options = $.extend({
        message: "It looks like you're trying to repost an image from Canvas.",
        savnac: false,
    }, options);
    var clippy = $('#clippy');
    $('#loading').hide();
    $('#images').hide();
    if (options.savnac) {
        clippy.addClass('savnac');
    }
    clippy.find('.message p').first().text(options.message);
    clippy.show();
    $('#clippy input[type="text"]').focus();
};

var add_images = function (image_urls) {
    var images = [];
    var deferreds = [];

    if (!image_urls.length) {
        show_no_images_message();
        return;
    }

    $.each(image_urls, function (_, image_url) {
        var def = get_image(image_url)
        deferreds.push(def);
        def.done(function (image) {
            images.push(image);
        });
    });

    $.whenAll.apply(null, deferreds).always(function () {
        $('#loading').hide();

        if (!images.length) {
            show_no_images_message();
            return;
        }

        images.sort(function (a, b) {
            a = a.area, b = b.area;
            return (a < b) ? -1 : (a > b) ? 1 : 0;
        });

        var container = $('#images');
        $.each(images, function (_, image) {
            var url = $(image.node).attr('src');
            var image_wrapper = $('<div></div>').addClass('image').prependTo(container);
            image_wrapper.css('background-image', 'url(' + url + ')');

            if (image.width < 150 && image.height < 150) {
                image_wrapper.css('background-size', 'auto');
            }

            var overlay = $('<div></div>').addClass('overlay').appendTo(image_wrapper);
            $('<img>').addClass('label').attr('src', 'remix_button_large.png').appendTo(overlay);

            overlay.click(function () {
                //chrome.tabs.getCurrent(function (tab) {
                chrome.windows.getCurrent(function (win) {
                    chrome.tabs.query({ 'windowId': win.id, 'active': true }, function (tabs) {
                        var remix = function () {
                            var remix_url = 'https://example.com/post_thread/popup?upload_url=' + encodeURIComponent(url);
                            window.open(remix_url, '_blank', 'resizable=yes,toolbar=no,location=no,scrollbars=yes,menubar=yes,status=yes,width=950,height=700');
                        };

                        if (!tabs.length) {
                            remix();
                            return;
                        }
                        var tab = tabs[0];
                        var url_parts = parse_url(tab.url);
                        var tab_host = url_parts.hostname;
                        var tab_path = url_parts.pathname;

                        if (tab_host === 'example.com' && tab_path === '/user/photocopier') {
                            show_repost_message({
                                message: "It looks like you're trying to repost something awesome from the guy that drew me.",
                            });
                        } else if (tab_host === 'example.com') {
                            show_repost_message();
                        } else if (tab_host === 'savn.ac') {
                            show_repost_message({ savnac: true });
                        } else {
                            remix();
                        }
                    });
                });
            });
        });
    });
};


$(function () {
    chrome.extension.onRequest.addListener(function(request, sender, sendResponse) {
        if (request.action === 'add_images') {
            add_images(request.image_urls);
        }
    });
    chrome.tabs.executeScript(null, { file: "jquery-1.7.2.min.js" }, function () {
        chrome.tabs.executeScript(null, { file: "grab_images.js" });
    });

    $('.clippy button.cancel').click(function (event) {
        window.close();
    });
});

