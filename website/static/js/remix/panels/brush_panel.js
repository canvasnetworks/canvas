remix.panels.BrushPanel = remix.BasePanel.createSubclass();

remix.panels.BrushPanel.prototype.init = function (root, easel) {
    remix.panels.BrushPanel.__super__.init.apply(this, arguments);
    this.easel = easel;
    this.color_picker = new remix.pickers.ColorPicker(this.scoped('.color_picker'), [238,51,136], easel);
    this.size_picker = new remix.pickers.SizePicker(this.scoped('.size_picker'), [30, 12, 6], 1, 100, 6, easel);
    this.opacity_picker = new remix.pickers.OpacityPicker(this.scoped('.opacity_picker'), 100);
    this.softness_picker = new remix.pickers.SoftnessPicker(this.scoped('.softness_picker'), 0);

    var self = this;
    this.scoped('input[name=square]').bind('change', function () {
        self.easel.update_brush();
    });
};

remix.panels.BrushPanel.prototype.get_params = function () {
    var size = this.size_picker.get_size();
    var color = this.color_picker.get_color();
    var alpha = this.opacity_picker.get_alpha();
    var softness = this.softness_picker.get_softness();
    var original_size = size;
    size -= size*softness/2;
    softness *= original_size*1.25;

    color.set_alpha(alpha);

    if (size < 1.0 && softness > 0.0) {
        size = 1.0;
        softness = 0.0;
    }

    return {
        color: color,
        line_width: size,
        shadow_blur: softness,
        square: this.scoped('input[name=square]').attr('checked'),
    };
};

