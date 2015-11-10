canvas.BaseWidget = Object.createSubclass();

canvas.BaseWidget.prototype.init = function (root) {
    this.root = root;
};

canvas.BaseWidget.prototype.scoped = function (selector) {
    return this.root.find(selector);
};

canvas.BaseWidget.prototype.trigger = function (event, params) {
    return $(this.root).trigger(event, params);
};

canvas.BaseWidget.prototype.show = function () {
    this.root.show();
};

canvas.BaseWidget.prototype.hide = function () {
    this.root.hide();
};