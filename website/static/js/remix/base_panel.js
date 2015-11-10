remix.BasePanel = canvas.BaseWidget.createSubclass();

remix.BasePanel.prototype.enter = function () {
    this.root.show();
};

remix.BasePanel.prototype.leave = function () {
    this.root.hide();
};