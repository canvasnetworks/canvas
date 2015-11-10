remix.panels.EraserPanel = remix.BasePanel.createSubclass();

remix.panels.EraserPanel.prototype.init = function (root, easel) {
    remix.panels.EraserPanel.__super__.init.apply(this, arguments);
    this.size_picker = new remix.pickers.SizePicker(this.scoped('.size_picker'), [30, 12, 6], 1, 100, 12, easel);
    this.opacity_picker = new remix.pickers.OpacityPicker(this.scoped('.opacity_picker'), 255);
    this.softness_picker = new remix.pickers.SoftnessPicker(this.scoped('.softness_picker'), 0);

    var self = this;
    this.scoped('input[name=square]').bind('change', function () {
        self.easel.update_brush();
    });
};

remix.panels.EraserPanel.prototype.get_params = function () {
    var size = this.size_picker.get_size();
    var alpha = this.opacity_picker.get_alpha();
    var color = new remix.Color([255,255,255, alpha]);
    var softness = this.softness_picker.get_softness();
    var original_size = size;
    size -= size*softness/2;
    softness *= original_size*1.25;

    return {
        color: color,
        line_width: size,
        shadow_blur: softness,
        square: this.scoped('input[name=square]').attr('checked'),
    }
};
