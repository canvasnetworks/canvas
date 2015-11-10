remix.pickers.OpacityPicker = remix.pickers.BoundedNumericPicker.createSubclass();

remix.pickers.OpacityPicker.prototype.init = function (root, default_value, easel) {
    remix.pickers.OpacityPicker.__super__.init.apply(this, [root, default_value, 0, 100]);

    this.easel = easel;

    this._wire_buttons();
    this._wire_input();
    this.set_preview(default_value);
};

remix.pickers.OpacityPicker.prototype.get_alpha = function () {
    var p = this.get_value();
    return (p / 100) * 255;
};

remix.pickers.OpacityPicker.prototype._wire_buttons = function () {
    var preview = this.scoped('.selected_opacity');
    var self = this;

    this.scoped('.choices li').click(function () {
        var opacity = parseInt($(this).data('value'));
        self.input.val(opacity);
        self.set_preview(opacity);
    });
};

remix.pickers.OpacityPicker.prototype._wire_input = function () {
    this.input.change($.proxy(function () {
        var v = this.get_value();
        this.set_preview(v);
    }, this));
};

remix.pickers.OpacityPicker.prototype.set_preview = function (percent) {
    var v = percent / 100.0;
    var opacity_preview = this.scoped('.selected_opacity .preview');
    opacity_preview.css('opacity', v);
    if (this.easel && this.easel.renderer) {
        this.easel.renderer.render();
    }
};
