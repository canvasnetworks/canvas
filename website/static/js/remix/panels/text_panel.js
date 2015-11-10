remix.panels.TextPanel = remix.BasePanel.createSubclass();

remix.panels.TextPanel.prototype.init = function (root, easel) {
    remix.panels.TextPanel.__super__.init.apply(this, arguments);
    this.easel = easel;
    this.text = "";
    this.color_picker = new remix.pickers.ColorPicker(this.scoped('.color_picker'), [255,255,255], easel);
    this.font_picker = new remix.pickers.FontPicker(this.scoped('.font_picker'), easel);
    this.size_picker = new remix.pickers.SizePicker(this.scoped('.size_picker'), [48, 32, 16], 12, 148, 32, easel);
    this.opacity_picker = new remix.pickers.OpacityPicker(this.scoped('.opacity_picker'), 100, easel);
};

remix.panels.TextPanel.prototype.get_params = function () {
    var inner_color = this.color_picker.get_color();
    var alpha = this.opacity_picker.get_alpha();
    var text_has_outline = inner_color.equals(new remix.Color([255,255,255]));
    inner_color.set_alpha(alpha);

    var outline = new remix.Color([0,0,0]);
    if (text_has_outline) {
        outline.set_alpha(alpha);
    }

    return {
        text: this.text,
        text_alignment: "center",
        font_name: this.font_picker.get_font(),
        font_size: this.size_picker.get_size(),
        text_inner_color: inner_color,
        text_has_outline: text_has_outline,
        text_outline_color: outline,
    }
};

