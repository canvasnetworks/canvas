
canvas.validate = function (element, options) {
    return $(element).validate($.extend({
        errorClass: 'invalid',
        errorElement: 'span',
        errorPlacement: function (label, element) {
            element = $(element);
            if (element.next().is('input[type=submit]')) {
                label.insertAfter(element.next());
            } else {
                label.insertAfter(element);
            }
        },
    }, options));
};

