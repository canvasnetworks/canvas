remix.panels.ImagePanel = remix.BasePanel.createSubclass();

remix.panels.ImagePanel.prototype.init = function (root, easel) {
    remix.panels.ImagePanel.__super__.init.apply(this, arguments);
    this.easel = easel;
    this.opacity_picker = new remix.pickers.OpacityPicker(this.scoped('.opacity_picker'), 100, easel);
};

remix.panels.ImagePanel.prototype.get_params = function () {
    return {
        alpha: this.opacity_picker.get_alpha(),
    };
};

