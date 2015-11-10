remix.pickers.TolerancePicker = remix.pickers.BoundedNumericPicker.createSubclass();

remix.pickers.TolerancePicker.prototype.init = function (root, default_value) {
    var default_value = $(root).find('ul.choices li[data-tolerance="' + default_value + '"]').data('value');
    remix.pickers.TolerancePicker.__super__.init.apply(this, [root, default_value, 1, 100]);

    this._wire_buttons();
    this._wire_input();
    this.set_preview(default_value);
    this.is_inverted = true;
};

remix.pickers.TolerancePicker.prototype.get_tolerance = function() {
    var tolerance_cap = 256*3;
    return Math.round(this.get_value()*tolerance_cap/100);
};

remix.pickers.TolerancePicker.prototype._wire_buttons = function () {
    var that = this;

    var set_tolerance = function (size_name, value) {
        that.set_preview(value);
        that.input.val(value);
    };

    this.scoped('ul.choices li').click(function () {
        set_tolerance($(this).data('tolerance'), $(this).data('value'));
    });
};

remix.pickers.TolerancePicker.prototype._wire_input = function () {

    this.input.change($.proxy(function () {
        var v = this.get_value();
        this.set_preview(v);
    }, this));
};

remix.pickers.TolerancePicker.prototype.set_preview = function (size) {
    var tolerance = "full";
    if (size <= 7) {
        tolerance = "low";
    } else if (size <= 20) {
        tolerance = "medium";
    } else if (size <= 50) {
        tolerance = "high";
    }
    var preview = this.scoped('.selected_tolerance');
    preview.attr("class", "selected_tolerance " + tolerance + "_tolerance");
    preview.data('size', size);
};

