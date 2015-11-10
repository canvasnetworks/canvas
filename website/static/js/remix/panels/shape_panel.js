remix.panels.ShapePanel = remix.BasePanel.createSubclass();

remix.panels.ShapePanel.prototype.init = function (easel) {
    remix.panels.ShapePanel.__super__.init.apply(this, arguments);
    this.easel = easel;
    this.shape_picker = new remix.pickers.ShapePicker(this.scoped('.shape_picker'), "rectangle");
    this.color_picker = new remix.pickers.ColorPicker(this.scoped('.color_picker'), [238,51,136], easel);
    this.opacity_picker = new remix.pickers.OpacityPicker(this.scoped('.opacity_picker'), 100);
    this.size_picker = new remix.pickers.SizePicker(this.scoped('.size_picker'), [30, 12, 6], 6, easel);
};

remix.panels.ShapePanel.prototype.get_params = function () {
    var color = this.color_picker.get_color();
    var alpha = this.opacity_picker.get_alpha();

    color.set_alpha(alpha);

    return {
        'color': color,
        'shape': this.shape_picker.get_shape(),
        'line_width': this.size_picker.get_size(),
    };
};

