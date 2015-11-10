remix.panels.FillPanel = remix.BasePanel.createSubclass();

remix.panels.FillPanel.prototype.init = function (easel) {
    remix.panels.FillPanel.__super__.init.apply(this, arguments);
    this.easel = easel;
    this.color_picker = new remix.pickers.ColorPicker(this.scoped('.color_picker'), [238,51,136], easel);
    this.opacity_picker = new remix.pickers.OpacityPicker(this.scoped('.opacity_picker'), 100);
    this.tolerance_picker = new remix.pickers.TolerancePicker(this.scoped('.tolerance_picker'), 'medium');
};

remix.panels.FillPanel.prototype.get_params = function () {
    return {
        color: this.color_picker.get_color(),
        tolerance: this.tolerance_picker.get_tolerance(),
        alpha: this.opacity_picker.get_alpha(),
        knockout: this.scoped('input[name=erase]').attr('checked'),
    };
};

