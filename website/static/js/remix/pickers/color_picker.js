remix.pickers.ColorPicker = remix.pickers.BasePicker.createSubclass();

remix.pickers.ColorPicker.prototype.init = function (root, default_value, easel) {
    remix.pickers.ColorPicker.__super__.init.apply(this, arguments);

    this.easel = easel;

    $.each(this.scoped('.swatch'), $.proxy(function (_, swatch) {
        if (canvas.compare_arrays($(swatch).data('color').slice(0, 3), default_value)) {
            this._select_swatch(swatch);
            return false;
        }
    }, this));

    this.input = this.scoped('input');

    this._wire_eye_dropper();
    this._wire_popout();
    this._wire_spectrum();
};

remix.pickers.ColorPicker.prototype._deactiveate_swatches = function () {
    this.scoped('.swatches').find('.active').removeClass('active');
};

remix.pickers.ColorPicker.prototype._select_swatch = function (swatch) {
    swatch = $(swatch);

    var color = new remix.Color(swatch.data('color'));
    this.set_color(color);

    this._deactiveate_swatches();
    this.scoped('.spectrum_container').hide();
    swatch.addClass('active');
};

remix.pickers.ColorPicker.prototype._wire_eye_dropper = function () {
    var self = this;

    var done_picking = function () {
        self.root.trigger('finish_temporary_tool');
        self.popout.persist = false;
    };

    this.scoped('.eye_dropper').bind('click', function () {
        self.popout.persist = true;
        var data = {
            tool: remix.pickers.ColorPicker.tools.EyeDropper,
            args: [$.proxy(self.set_color, self), done_picking],
        };
        self.root.trigger('use_temporary_tool', data);
    });
};

remix.pickers.ColorPicker.prototype._wire_popout = function () {
    this.scoped('.swatch').each($.proxy(function (_, el) {
        el = $(el);

        var color = new remix.Color(el.data('color'));
        el.css('background-color', color.get_css());

        el.click($.proxy(function () {
            this._select_swatch(el);
        }, this));
    }, this));

    this.scoped('.spectrum_toggle').click($.proxy(function () {
        this.scoped('.spectrum_container').toggle();
    }, this));
};

remix.pickers.ColorPicker.prototype._wire_spectrum = function () {
    this.scoped('.hue, .hue_slider').bind('mousedown', $.proxy(function (event) {
        event.preventDefault();

        var slider_parent = this.scoped('.spectrum');

        this._move_hue_slider(event.pageX - slider_parent.offset().left, event.pageY - slider_parent.offset().top);

        var slider_handler = $.proxy(function (event) {
            this._move_hue_slider(event.pageX - slider_parent.offset().left, event.pageY - slider_parent.offset().top);
        }, this);

        $(window).bind('mousemove', slider_handler);

        $(window).one('mouseup', $.proxy(function () {
            $(window).unbind('mousemove', slider_handler);
        }, this));
    }, this));

    $('.hsv_gradient, .hsv_slider').bind('mousedown', $.proxy(function (event) {
        event.preventDefault();

        var slider_parent = this.scoped('.hsv_gradient');

        this._move_sv_slider(event.pageX - slider_parent.offset().left, event.pageY - slider_parent.offset().top);

        var slider_handler = $.proxy(function (event) {
            this._move_sv_slider(event.pageX - slider_parent.offset().left, event.pageY - slider_parent.offset().top);
        }, this);

        $(window).bind('mousemove', slider_handler);

        $(window).one('mouseup', $.proxy(function () {
            $(window).unbind('mousemove', slider_handler);
        }, this));
    }, this));
};

remix.pickers.ColorPicker.prototype._set_color = function (color) {
    // Skips the spectrum color.
    this.active_color = color;
    this.scoped('.preview').css('background-color', color.get_css());
    if (this.easel && this.easel.renderer) {
        this.easel.renderer.render();
    }
};

remix.pickers.ColorPicker.prototype.set_color = function (color) {
    this._set_color(color);
    this._set_spectrum_color(color, false);
};

remix.pickers.ColorPicker.prototype.get_color = function () {
    return this.active_color.copy();
};

remix.pickers.ColorPicker.prototype._set_spectrum_color = function (color, skip_sliders) {
    var hsv = color.get_hsv();

    if (typeof this._spectrum_hsv === 'undefined') {
        this._spectrum_hsv = hsv;
    }

    if (!skip_sliders) {
        this._set_hue_slider(hsv[0]);
        this._set_sv_slider(hsv[1], hsv[2]);
    }

    var hsv_slider_color = (
        hsv[2] < 0.5 ||
        (hsv[1] + (1 - hsv[2]) > 0.8 && (hsv[0] > 0.6 && hsv[0] < 1))
    ) ? 'white' : 'black';

    var hue_slider_color = (hsv[0] > 0.6 && hsv[0] < 1) ? 'white' : 'black';

    var hsv_gradient_color = new remix.Color.from_hsv([hsv[0], 1, 1]);
    this.scoped('.hsv_gradient').css('background', hsv_gradient_color.get_css());

    this.scoped('.hsv_slider').css('border-color', hsv_slider_color);
    this.scoped('.hue_slider').css('border-color', hue_slider_color);

    this._spectrum_hsv = hsv;
};

remix.pickers.ColorPicker.prototype._set_hue_slider = function (hue) {
    var x, y;
    var size = this.scoped('.hsv_gradient').width(),
        max = this.scoped('.spectrum').width(),
        width = this.scoped('.hue_slider').width();

    if (hue == 0 || hue == 1) {
        x = 0; y = 0;
    } else if (hue > 0 && hue < 0.25) {
        x = Math.round((hue * 4) * size) + width*1.25;
        y = 0;
    } else if (hue == 0.25) {
        x = max; y = 0;
    } else if (hue > 0.25 && hue < 0.5) {
        x = max;
        y = Math.round(((hue - 0.25) * 4) * size) + width*1.25;
    } else if (hue == 0.5) {
        x = max; y = max;
    } else if (hue > 0.5 && hue < 0.75) {
        x = Math.round((1 - ((hue - 0.5) * 4)) * size) + width*1.25;
        y = max;
    } else if (hue == 0.75) {
        x = 0; y = max
    } else if (hue > 0.75 && hue < 1) {
        x = 0;
        y = Math.round((1 - ((hue - 0.75) * 4)) * size) + width*1.25;
    }
    this._move_hue_slider(x, y, true);
};

remix.pickers.ColorPicker.prototype._set_color_from_spectrum = function (color) {
    this._deactiveate_swatches();
    this._set_color(color);
    this._set_spectrum_color(color, true);
};

remix.pickers.ColorPicker.prototype._move_hue_slider = function (x, y, passive) {
    var slider = this.scoped('.hue_slider'),
        width = slider.outerWidth(),
        max = this.scoped('.spectrum').innerWidth(),
        x_locked, y_locked;

    x = x - width/2;
    y = y - width/2;

    if (x >= y && x <= max - y) {
        // top quadrant
        x_locked = Math.max(0, Math.min(max - width, x));
        y_locked = (x_locked < max - width) ? 0 : Math.max(0, Math.min(max - width, y));
        hue = Math.max(0, Math.min(1, (x_locked - width/2)/(max - width*2)))/4;
    } else if (x >= y && x >= max - y) {
        // right quardrant
        x_locked = max - width;
        y_locked = Math.max(0, Math.min(max - width, y));
        hue = Math.max(0, Math.min(1, (y_locked - width/2)/(max - width*2)))/4 + 0.25;
    } else if (x <= y && x >= max - y) {
        // bottom quadrant
        x_locked = Math.max(0, Math.min(max - width, x));
        y_locked = max - width;
        hue = Math.max(0, Math.min(1, 1 - (x_locked - width/2)/(max - width*2)))/4 + 0.5;
    } else if (x <= y && x <= max - y) {
        // left quadrant
        y_locked = Math.max(0, Math.min(max - width, y));
        x_locked = (y_locked < max - width) ? 0 : Math.max(0, Math.min(max - width, x));
        hue = Math.max(0, Math.min(1, 1 - (y_locked - width/2)/(max - width*2)))/4 + 0.75;
    }

    if (!passive || !((this._spectrum_hsv[0] == 0 || this._spectrum_hsv[0] == 1) && (this._spectrum_hsv[2] == 0 || this._spectrum_hsv[2] == 1))) {
        slider.css({
            left: x_locked,
            top : y_locked,
        });
    }

    if (!passive) {
        var color = this.get_color();
        var hsv = color.get_hsv();
        color.set_hsv([hue, hsv[1], hsv[2]]);
        this._set_color_from_spectrum(color);
    }
};

remix.pickers.ColorPicker.prototype._set_sv_slider = function (s, v) {
    var size = this.scoped('.hsv_gradient').width();

    this._move_sv_slider(s * size, (1 - v) * size, true);
};

remix.pickers.ColorPicker.prototype._move_sv_slider = function (x, y, passive) {
    var slider = this.scoped('.hsv_slider'),
        width = slider.outerWidth(),
        max = this.scoped('.hsv_gradient').width();

    var x_locked = Math.max(-width / 2, Math.min(max - width / 2, x - width / 2));
    var y_locked = Math.max(-width / 2, Math.min(max - width / 2, y - width / 2));

    var s = Math.max(0, Math.min(1, x / max));
    var v = 1 - Math.max(0, Math.min(1, y / max));

    slider.css({
        left: x_locked,
        top : y_locked,
    });

    if (!passive) {
        var color = this.get_color();
        color.set_hsv([color.get_hsv()[0], s, v]);
        this._set_color_from_spectrum(color);
    }
};


// Eye-dropper tool

remix.pickers.ColorPicker.tools = {};

remix.pickers.ColorPicker.tools.EyeDropper = remix.Tool.createSubclass();

remix.pickers.ColorPicker.tools.EyeDropper.prototype.cursor = "url(/static/img/remix-ui/color-select-cursor.png) 2 20, auto";
remix.pickers.ColorPicker.tools.EyeDropper.prototype.brush_preview = false;

remix.pickers.ColorPicker.tools.EyeDropper.prototype.init = function (renderer, args) {
    remix.pickers.ColorPicker.tools.EyeDropper.__super__.init.apply(this, arguments);
    this.ctx = this.renderer.composite.ctx();
    this._mouse_down = false;

    if (args && args.length) {
        this.pick_color = args[0];
        this.close = args[1];
    }
};

remix.pickers.ColorPicker.tools.EyeDropper.prototype.pick = function (pt) {
    var pixels = this.ctx.getImageData(pt.x,pt.y,1,1).data;
    var color = new remix.Color([pixels[0], pixels[1], pixels[2]]);

    if (this.pick_color) {
        this.pick_color(color);
    }
};

remix.pickers.ColorPicker.tools.EyeDropper.prototype.down = function (pt) {
    this._mouse_down = true;
    this.pick(pt);
};

remix.pickers.ColorPicker.tools.EyeDropper.prototype.move = function (a, b) {
    if(this._mouse_down) {
        this.pick(b);
    }
};

remix.pickers.ColorPicker.tools.EyeDropper.prototype.up = function (pt) {
    this.pick(pt);
    if (this.close) {
        this.close();
    }
};

