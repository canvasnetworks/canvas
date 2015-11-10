remix.Popout = canvas.BaseWidget.createSubclass();

remix.Popout.prototype.init = function (root, params) {
    params = $.extend({
        click_away_to_dismiss: true,
        button: null,
    }, params || {});
    remix.Popout.__super__.init.apply(this, arguments);

    this.click_away_to_dismiss = params.click_away_to_dismiss;
    this.button = params.button;

    this.root.prepend("<div class='tail'>◀</div>");
    this.tail = this.scoped('.tail');
};

remix.Popout.prototype.show_right_of = function (target) {
    this._show();

    var tpos = $(target).position();
    var left_bar = $(target).parents('.left_bar');

    var pos = {
        left: left_bar.position().left + left_bar.outerWidth(),
        top: tpos.top + $(target).outerHeight() / 2 - this.root.outerHeight() / 2,
    };

    var bias = 0;
    if (pos.top < 0) {
        bias = -pos.top;
        pos.top = 0;
    }

    this.tail.css('top', this.root.outerHeight() / 2 - this.tail.outerHeight() / 2 - bias);

    this.root.css(pos);
};

remix.Popout.prototype._show = function () {
    this.root.addClass('popped');

    if (!this.click_away_to_dismiss) {
        return;
    }

    var self = this;

    var handler = function (event) {
        if (!self.click_away_to_dismiss) {
            return;
        }
        var self_el = self.root.get(0);
        var click_on_canvas_container = $(event.target).parents('.canvas_container').length;
        var click_on_self_parent = self.button && ($(event.target).parents('button').get(0) == self.button.get(0) || event.target == self.button.get(0));
        var ignore = click_on_self_parent || (self.persist && click_on_canvas_container);
        var contained = $.contains(self_el, event.target) || self_el == event.target;

        if (!contained && !ignore) {
            self.persist = false;
            $(window).unbind('mousedown', handler);
            self.hide();
        }
    };

    $(window).bind('mousedown', handler);
};

remix.Popout.prototype.is_visible = function () {
    return this.root.hasClass('popped');
};

remix.Popout.prototype.hide = function () {
    this.root.removeClass('popped');
    this.root.find('input').blur();
};

remix.Popout.hide_all = function () {
    $('.popped').removeClass('popped');
};

