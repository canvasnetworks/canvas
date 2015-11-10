remix.Tool = Object.createSubclass();
remix.Tool.prototype.init = function (renderer, parameter_provider) {
    this.renderer = renderer;
    this.get_params = parameter_provider;
};

remix.Tool.prototype.finalize = function (pt) {};

remix.Tool.prototype.bufferCompositeOperation = "source-over";
remix.Tool.prototype.down = function (pt) {};
remix.Tool.prototype.up = function (pt) {};
remix.Tool.prototype.move = function (mdown, pt_from, pt_to) {};
remix.Tool.prototype.enter = function (mdown, pt) {};
remix.Tool.prototype.leave = function (mdown, pt) {};
remix.Tool.prototype.keydown = function (key) {};
remix.Tool.prototype.keyup = function (key) {};
remix.Tool.prototype.render = function (ctx) {};
remix.Tool.prototype.preview = function () {};
remix.Tool.prototype.alt_down = function () {};
remix.Tool.prototype.alt_up = function () {};
remix.Tool.prototype.shift_down = function () {};
remix.Tool.prototype.shift_up = function () {};

remix.Tool.prototype.get_cursor_method = function () {
    if (this.easel) {
        return $.proxy(this.easel.cursor, this.easel);
    }
};
