remix.pickers.ShapePicker = remix.pickers.BasePicker.createSubclass();

remix.pickers.ShapePicker.prototype.init = function (root, default_shape) {
    remix.pickers.ShapePicker.__super__.init.apply(this, arguments);

    this._wire();
    this._pick_shape(default_shape);
};

remix.pickers.ShapePicker.prototype._wire = function () {
    var self = this;

    this.button = this.scoped('button');

    this.root.delegate('ul.choices li', 'click', function () {
        self._pick_shape($(this).data('shape'));
    });
};

remix.pickers.ShapePicker.prototype._pick_shape = function (shape) {
    if (this._current_shape) {
        this.button.removeClass(this._current_shape);
    }

    this._current_shape = shape;
    this.button.addClass(shape).data('shape', shape);
    shape_preview = this.scoped('.selected_shape');
    shape_preview.attr("class", "selected_shape " + shape);
};

remix.pickers.ShapePicker.prototype.get_shape = function () {
    return this._current_shape;
};

