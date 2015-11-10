// keycode code based on: https://github.com/flamewave/jquery-ui-numeric/blob/master/jquery-ui-numeric.js

var NumericalInput = Object.createSubclass();

NumericalInput.prototype._clean_boundaries = function () {
    var current = parseInt(this.selector.val(), 10);

    if (isNaN(current)) {
        current = this.default_;
    }

    if (current > this.max) {
        current = this.max;
    } else if (current < this.min) {
        current = this.min;
    }

    return current;
};

NumericalInput.prototype._clean = function() {
    this.selector.val($.trim(this.selector.val()).replace(/[^0-9\.]/g,''));
    this.selector.val(this._clean_boundaries());
};

NumericalInput.prototype.value = function(value) {
    if (typeof value === "undefined") {
        return this._clean_boundaries();
    } else {
        this.selector.val(value);
    }
}

NumericalInput.prototype.init = function (selector, min, max, default_) {
    this.selector = selector;
    this.min = min;
    this.max = max;
    this.default_ = default_;
    
    selector
        .val(this.default_)
        .change($.proxy(this._clean, this))
        .keydown(function (event) {

            function isNumericKey(keyCode) {
                return (keyCode >= 48 && keyCode <= 57) || (keyCode >= 96 && keyCode <= 105);
            }

            function isControlKey(keyCode) {
                return (keyCode <= 47 && keyCode != 32)
                || (keyCode >= 91 && keyCode <= 95)
                || (keyCode >= 112 && [188, 189, 190, 191, 192, 219, 220, 221, 222].indexOf(keyCode) == -1)
            }

            switch (event.which) {
                case 38: // Up Arrow
                case 40: // Down Arrow
                case 33: // Page Up
                case 34: // Page Down
                    return;

                case 65: // A (select all)
                case 67: // C (copy)
                case 86: // V (paste)
                case 88: // X (cut)
                case 89: // Y (redo)
                case 90: // Z (undo)
                    if (event.ctrlKey)
                        return;
                    break;
            }

            if (isControlKey(event.which))
                return;

            if (!isNumericKey(event.which)) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
        });

    return selector;

};
