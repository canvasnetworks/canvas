remix.pickers.FontPicker = remix.pickers.BasePicker.createSubclass();

remix.pickers.FontPicker.fonts = [
    'Impact, sans-serif',
    'Times New Roman, serif',
    'Comic Sans MS, cursive',
    'Courier New, monospace',
    'Arial, sans-serif'
];

remix.pickers.FontPicker.prototype.init = function (root, easel) {
    remix.pickers.FontPicker.__super__.init.apply(this, arguments);
    this.easel = easel;
    this.preview = this.scoped('.selected_font');

    this._wire_buttons();
    this.set_preview(remix.pickers.FontPicker.fonts[0]);
};

remix.pickers.FontPicker.prototype.get_font = function () {
    return this.preview.css('font-family');
};

remix.pickers.FontPicker.prototype._wire_buttons = function () {
    var popout = this.scoped('.font_picker_popout');
    var ul = this.scoped('ul.choices');
    var self = this;

    $.each(remix.pickers.FontPicker.fonts, function(index) {
        var font = remix.pickers.FontPicker.fonts[index];
        var choice = $('<li>Aa</li>');
        choice.data('value', font).css('font-family', font);
        ul.append(choice);
    });

    this.scoped('ul.choices li').click(function () {
        var font = $(this).data('value');
        self.set_preview(font);
    });
};

remix.pickers.FontPicker.prototype.set_preview = function(font) {
    this.preview.css('font-family', font);
    this.easel.renderer.render();
};