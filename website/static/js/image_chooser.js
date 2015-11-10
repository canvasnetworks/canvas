canvas.ImageChooser = canvas.BaseWidget.createSubclass();

canvas.ImageChooser.prototype.init = function () {
    canvas.ImageChooser.__super__.init.apply(this, arguments);

    this.url_input = this.scoped('.start_from_url');
    this.url_input_button = this.scoped('button');
    this.url_input_field = this.scoped('input');
    this.start_from = {
        url : this.scoped('.from_url'),
        disk: this.scoped('.from_disk .uploadify_input'),
        draw: this.scoped('.from_scratch'),
    };

    this.start_options = this.scoped('ul');

    this._wire();
};

canvas.ImageChooser.prototype._wire = function () {
    var self = this;

    this.start_from.url.click($.proxy(this.show_url_input, this));

    this.scoped('.clear a').bind('click', function () { 
        self.cancel_url_input();
    });

    this.url_input_field.keydown(function (event) {
        if (event.keyCode == $.ui.keyCode.ENTER) {
            self.url_input_button.trigger('click');
        }
    });
};

canvas.ImageChooser.prototype.cancel_url_input = function () {
    this.start_options.show();
    this.url_input.hide();
};

canvas.ImageChooser.prototype.start_over = function () {
    this.cancel_url_input();
};

canvas.ImageChooser.prototype.show_url_input = function () {
    this.url_input.show();
    this.start_options.hide();
    this.url_input_field.focus();
};

