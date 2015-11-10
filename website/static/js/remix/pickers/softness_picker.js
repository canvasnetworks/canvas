remix.pickers.SoftnessPicker = remix.pickers.BoundedNumericPicker.createSubclass();

remix.pickers.SoftnessPicker.prototype.init = function (root, default_value) {
    remix.pickers.SoftnessPicker.__super__.init.apply(this, [root, default_value, 0, 100]);

    this._wire_buttons();
    this._wire_input();
    this.set_preview(default_value);
    this.is_inverted = true;
};

remix.pickers.SoftnessPicker.prototype.get_softness = function () {
    return this.get_value()/100;
};

remix.pickers.SoftnessPicker.prototype._wire_buttons = function () {
    var preview = this.scoped('.selected_softness');
    var self = this;

    this.scoped('ul.choices li').click(function () {
        var opacity = parseInt($(this).data('value'));
        self.set_preview(opacity);
        self.input.val(opacity);
    });
};

remix.pickers.SoftnessPicker.prototype._wire_input = function () {
    this.input.change($.proxy(function () {
        var v = this.get_value();
        this.set_preview(v);
    }, this));
};

remix.pickers.SoftnessPicker.prototype.set_preview = function(softness) {
    var selected_brush = this.scoped('.selected_softness');
    softness = 100 - softness*3;
    selected_brush.css("background", "-webkit-radial-gradient(center center, 20px 20px, rgba(0,0,0, 1) " + softness + "%, rgba(0,0,0, 0) 100%)");
    selected_brush.css("background", "-moz-radial-gradient(center center 0deg, circle closest-side, rgba(34,34,34, 1) " + softness + "%, rgba(34,34,34, 0) 100%)");
    selected_brush.css("background", "-o-radial-gradient(center center, circle closest-side, rgba(34,34,34, 1) " + softness + "%, rgba(34,34,34, 0) 100%)");
    selected_brush.css("background", "-ms-radial-gradient(center center, circle closest-side, rgba(34,34,34, 1) " + softness + "%, rgba(34,34,34, 0) 100%)");
};