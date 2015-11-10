remix.panels.ClonePanel = remix.BasePanel.createSubclass();

remix.panels.ClonePanel.prototype.init = function () {
    remix.panels.ClonePanel.__super__.init.apply(this, arguments);
    this.size_picker = new remix.pickers.SizePicker(this.scoped('.size_picker'), [30, 12, 6], 1, 100, 6);
    this.opacity_picker = new remix.pickers.OpacityPicker(this.scoped('.opacity_picker'), 215);
    this.softness_picker = new remix.pickers.SoftnessPicker(this.scoped('.softness_picker'), 0);
};

remix.panels.ClonePanel.prototype.get_params = function () {
    var size = this.size_picker.get_size();
    var alpha = this.opacity_picker.get_alpha();
    var color = new remix.Color([255,255,255, alpha]);
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
        'color': color,
        'line_width': size,
        'shadow_blur': softness,
        'alpha': alpha,
    }
};
