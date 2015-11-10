remix.pickers.SizePicker = remix.pickers.BoundedNumericPicker.createSubclass();

remix.pickers.SizePicker.prototype.init = function (root, values, min, max, default_value, easel) {
    remix.pickers.SizePicker.__super__.init.apply(this, [root, default_value, min, max]);

    this.selected_preview = this.scoped('.selected_brush .preview');
    this.values = values;
    this.default_value = default_value;
    this.easel = easel;

    this._wire_buttons();
    this._wire_input();
    this.set_preview(default_value);
};

remix.pickers.SizePicker.prototype.get_size = function () {
    return this.get_value();
};

remix.pickers.SizePicker.prototype._wire_buttons = function () {
    var preview = this.scoped('.selected_brush');
    var popout = this.scoped('.size_picker_popout');
    var ul = this.scoped('ul.choices');
    var self = this;

    $.each(this.values, function(index) {
        var size = self.values[index];
        var choice = $('<li></li>');
        choice.data('value', size);
        var preview = $('<div class="preview"></div>');
        self.set_size(preview, size);
        ul.append(choice);
        choice.append(preview);
    });


    this.scoped('ul.choices li').click(function () {
        var size = parseInt($(this).data('value'));
        self.input.val(size);
        self.set_preview(size);
    });
};

remix.pickers.SizePicker.prototype._wire_input = function () {
    this.input.change($.proxy(function () {
        var v = this.get_value();
        this.set_preview(v);
    }, this));
};

remix.pickers.SizePicker.prototype.set_preview = function (size) {
    this.set_size(this.selected_preview, size);
    if (this.easel && this.easel.renderer) {
        this.easel.renderer.render();
        this.easel.update_brush();
    }
};

remix.pickers.SizePicker.prototype.set_size = function(ele, size) {
    var wrapper_height = 40;
    var wrapper_width = 40
    ele.css({
        top     : (wrapper_height - size)/2,
        left    : (wrapper_width - size)/2,
        width   : size,
        height  : size,
    });
};