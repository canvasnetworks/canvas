remix.pickers.BasePicker = canvas.BaseWidget.createSubclass();

remix.pickers.BasePicker.prototype.init = function (root) {
    remix.pickers.BasePicker.__super__.init.apply(this, arguments);

    this.button = $(this.root).children('button');

    this.popout = new remix.Popout(this.scoped('.popout').first(), { button: this.button });

    this.button.bind('click', $.proxy(function () {
        if (this.popout.is_visible()) {
            this.popout.hide();
        } else if (!this._is_dragging) {
            this.popout.show_right_of(this.button);
        }
    }, this));

    if (this.root.hasClass('draggable')) {
        this._bind_drag();
    }
};


remix.pickers.BoundedNumericPicker = remix.pickers.BasePicker.createSubclass();

remix.pickers.BoundedNumericPicker.prototype.init = function (root, default_value, min, max) {
    remix.pickers.BoundedNumericPicker.__super__.init.apply(this, arguments);
    this.min = min;
    this.max = max;
    this.input = this.scoped('input');
    this.input.val(default_value);
};

remix.pickers.BoundedNumericPicker.prototype.get_value = function () {
    var val = parseFloat(this.input.val());
    val = Math.max(Math.min(val, this.max), this.min);
    this.input.val(val);
    return val;
};

remix.pickers.BoundedNumericPicker.prototype._bind_drag = function() {
    var threshold = 5;
    var distance = 100; // This is the max distance from the center in both directions until max/min.
    this.button.bind('mousedown', $.proxy(function(event) {
        if (event.which !== 1) {
            return;
        }
        this._is_dragging = false;
        var start_y = event.pageY;
        var start_value = parseInt(this.input.val());
        var threshold_broken = false;
        $('body').bind('mousemove.tool_slider', $.proxy(function(event) {
            var difference = event.pageY - start_y;
            var abs_difference = Math.abs(difference);
            if (abs_difference > distance) {
                this.root.addClass("capped_out");
            }
            this.root.removeClass("capped_out");
            if (threshold_broken) {
                this._is_dragging = true;
                var scaler = (this.max - this.min)/(distance);
                var new_value = start_value;
                if (this.is_inverted) {
                    new_value += difference*scaler;
                } else {
                    new_value -= difference*scaler;
                }
                new_value = Math.min(this.max, new_value);
                new_value = Math.max(this.min, new_value);
                new_value = Math.round(new_value);
                if (new_value == this.max || new_value == this.min) {
                    this.root.addClass("capped_out");
                }
                this.input.val(new_value);
                this.set_preview(new_value);
            } else if (abs_difference > threshold) {
                threshold_broken = true;
                start_y = event.pageY;
            }
        }, this));

        $('body').one('mouseup', $.proxy(function(event) {
            $('body').unbind('mousemove.tool_slider');
            this.root.removeClass("capped_out");
            if (threshold_broken) {
                this.popout.hide();
            }
        }, this));
    }, this));
};

