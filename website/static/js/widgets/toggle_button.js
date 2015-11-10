canvas.ToggleButton = Object.createSubclass();

canvas.ToggleButton.prototype.init = function (node, params) {
    // params.toggle_callback can return a $.Deferred instance. It receives a boolean of the button's state.
    // params.initial_state is a boolean.

    var that = this;
    this.node = node = $(node).first();

    this.params = {
        'on_text'           : 'On',
        'off_text'          : 'Off',
        'off_action_text'   : 'Turn off',
        'on_class'          : null,
        'off_class'         : null,
        'off_action_class'  : null,
    };
    $.extend(this.params, params);

    if (params.initial_state) {
        node.addClass('on');
    } else {
        node.removeClass('on');
    }
    this._set_visual_state();

    node.click(function (event) {
        event.preventDefault();

        if (that.params.toggle_callback) {
            var def = that.params.toggle_callback(node.hasClass('on'));
            if (def && typeof def.done != 'undefined') {
                def.done(function () {
                    that.toggle();
                });
            } else {
                that.toggle();
            }
        } else {
            that.toggle();
        }
    }).hover(function () {
        that._set_visual_state(true);
    }, function () {
        that._set_visual_state();
    });
};

canvas.ToggleButton.prototype.toggle = function () {
    this.node.toggleClass('on');
    this._set_visual_state();
    var action = (this.node.hasClass('on')) ? 'on' : 'off';
    this.node.trigger(action);
};

canvas.ToggleButton.prototype._set_visual_state = function (hovering) {
    this.node.text('');

    if (this.node.hasClass('on')) {
        if (hovering) {
            if (this.params.off_action_text) {
                this.node.text(this.params.off_action_text);
            }
            this._change_style(this.params.off_action_class);
        } else {
            if (this.params.on_text) {
                this.node.text(this.params.on_text);
            }
            this._change_style(this.params.on_class);
        }
    } else {
        if (this.params.off_text) {
            this.node.text(this.params.off_text);
        }
        this._change_style(this.params.off_class);
    }
};

canvas.ToggleButton.prototype._change_style = function (style) {
    // Remove all other stylings, then see if we're adding a new one
    var styles = [this.params.on_class, this.params.off_class, this.params.off_action_class];
    for (var i = 0; i < styles.length; i++) {
        this.node.removeClass(styles[i]);
    }
    if (style) {
        this.node.addClass(style);
    }
};

