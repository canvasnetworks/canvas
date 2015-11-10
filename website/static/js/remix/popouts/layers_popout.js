remix.LayersPopout = remix.Popout.createSubclass();

remix.LayersPopout.prototype.init = function (root, params) {
    remix.LayersPopout.__super__.init.apply(this, arguments);
    this._wired = false;
    this.easel = params.easel;

    this.root.bind('done_loading', $.proxy(function () { this.scale_canvases(); }, this));
};

remix.LayersPopout.prototype.show_right_of = function (target) {
    this.scale_canvases();
    remix.LayersPopout.__super__.show_right_of.apply(this, arguments);
    if (!this._wired) {
        this._wire();
        this._wired = true;
    }
};

remix.LayersPopout.prototype.scale_canvases = function () {
    var max_width = 60;
    var max_height = 40;

    var fg = this.scoped('canvas.foreground');
    var bg = this.scoped('canvas.background');

    var height = fg.attr('height');
    var width = fg.attr('width');
    var new_height = height, new_width = width;
    var ratio = width / height;

    if (ratio > 1.0)  {
        // wide image
        new_width = max_width;
        new_height = max_width / ratio;
    } else {
        // tall image
        new_width = max_height * ratio;
        new_height = max_height;
    }

    fg.css('height', new_height).css('width', new_width);
    bg.css('height', new_height).css('width', new_width);

    var height_offset = new_height / -1.5;
    var width_offset = new_width / 3.0;

    this.scoped('.bottom_layer')
        .css('top', height_offset)
        .css('left', width_offset)
        .css('margin-bottom', height_offset);
};

remix.LayersPopout.prototype._wire = function () {
    var blend_modes = {
        normal: {text: "Normal", val: "normal"},
        // Lighter!
        screen: {text: "Screen", val: "screen"},
        lighten: {text: "Lighten", val: "lighten"},
        color_dodge: {text: "Color Dodge", val: "color_dodge"},
        lighter_color: {text: "Lighter Color", val: "lighter_color"},
        // Darker!
        multiply: {text: "Multiply", val: "multiply"},
        darketn: {text: "Darken", val: "darken"},
        color_burn: {text: "Color Burn", val: "color_burn"},
        darker_color: {text: "Darker Color", val: "darker_color"},
        // Subtraction (crazy)
        difference: {text: "Difference", val: "difference"},
        exclusion: {text: "Exclusion", val: "exclusion"},
    };

    var self = this;

    this.scoped('.swap').click($.proxy(function (e) {
        self.easel.swap(true);
    }, this));

    this.scoped('.merge').click($.proxy(function (e) {
        self.easel.merge(true);
    }, this));

    this.scoped('.rotate_cw').click($.proxy(function (e) {
        self.easel.rotate('cw');
        self.scale_canvases();
    }, this));

    this.scoped('.rotate_ccw').click($.proxy(function (e) {
        self.easel.rotate('ccw');
        self.scale_canvases();
    }, this));

    this.scoped('.flip_vert').click($.proxy(function (e) {
        self.easel.flip('v');
        self.scale_canvases();
    }, this));

    this.scoped('.flip_horiz').click($.proxy(function (e) {
        self.easel.flip('h');
        self.scale_canvases();
    }, this));

    this.scoped('.filters button').click(function () {
        self.easel.merge(false);
        remix.filters[$(this).parent().children('select').val()](self.easel.renderer);
    });

    var options = self.scoped('.blend');
    $.each(blend_modes, function () {
        options.append($("<option/>").val(this.val).text(this.text));
    });

    options.change(function (ev) {
        self.scoped('.blend option:selected').each(function () {
            self.easel.renderer.choose_method($(this).val());
        });
    });
};

