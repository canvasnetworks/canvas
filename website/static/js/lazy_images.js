canvas.wire_lazy_images = function (base_selector) {
    if (typeof base_selector == 'undefined') {
        var base_selector = $(document);
    }
    base_selector.find('img.lazy').lazyload({
        threshold: 170,
        effect: 'fadeIn',
        effect_speed: 200,
        failure_limit: 10,
    }).removeClass('lazy');
};

