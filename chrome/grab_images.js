
var images_to_send = [];

var send_images = function () {
    chrome.extension.sendRequest({
        action: 'add_images',
        image_urls: images_to_send,
    });
};

var add_image = function (image_url) {
    if (typeof image_url === 'undefined' || !image_url || !$.trim(image_url)) {
        return;
    }
    images_to_send.push(image_url);
};

var get_url_from_background_image = function (el) {
    el = $(el);
    var url = el.css('background-image');
    if (url === 'none' || !url.match(/^url\s*\(/)) {
        return;
    }

    function check_position (pos) {
        // Checks that there's no offset.
        return pos.match(/^0\s*\D*$/);
    }
    if (!check_position(el.css('background-position-x')) || !check_position(el.css('background-position-y'))) {
        return;
    }
    return url.replace(/^url\s*\(["']?/, '').replace(/["']?\)$/, '');
};


$(function () {
    // Image tags.
    $('img:visible').each(function (_, img) {
        add_image($(img).get(0).src);
    });

    // Background images.
    $('*:visible').each(function (_, el) {
        var url = get_url_from_background_image(el);
        add_image(url);
    });

    send_images();
});

