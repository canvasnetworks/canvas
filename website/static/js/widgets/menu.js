canvas.Menu = Object.createSubclass();

canvas.Menu._timer = null;
canvas.Menu._timer_func = null;

canvas.Menu.prototype.init = function (container, args) {
    // `container` should have two children: a span (or a link), and an unordered list.
    args = typeof args === 'undefined' ? {} : args;

    this.args = {
        timeout: 0,
    };
    $.extend(this.args, args);

    this.container = container = $(container);

    this.label = container.find('a > span').first();
    this.dropdown = container.children('ul, div');

    $('<div></div>').addClass('shadow_clear').insertAfter(container.find('a').first());

    this._wire();
};

canvas.Menu.prototype._wire = function () {
    var arrow = $('<a></a>').addClass('menu_arrow').attr({
        href: '#',
    }).appendTo(this.label.closest('a')).click($.proxy(function (event) {
        event.preventDefault();
    }, this));
    $('<div></div>').addClass('clear').insertAfter(arrow);

    this.label.addClass('menu_label');
    this.dropdown.addClass('menu_dropdown');

    this.container.hover($.proxy(this._hover_in, this), $.proxy(this._hover_out, this));
    this.container.addClass('menu wired');
};

canvas.Menu.prototype._clear_timer = function () {
    if (canvas.Menu._timer) {
        clearTimeout(canvas.Menu._timer);
    }
    if (canvas.Menu._timer_func) {
        canvas.Menu._timer_func();
        canvas.Menu._timer_func = null;
    }
};

canvas.Menu.prototype._hover_in = function () {
    this._clear_timer();
    if (!this.container.hasClass('disabled')) {
        this.open();
    }
};

canvas.Menu.prototype._hover_out = function () {
    this._clear_timer();

    canvas.Menu._timer_func = $.proxy(function () {
        this.close();
    }, this);

    canvas.Menu._timer = setTimeout(canvas.Menu._timer_func, this.args.timeout);
};

canvas.Menu.prototype.open = function () {
    this._clear_timer();
    this.container.addClass('open');
};

canvas.Menu.prototype.close = function () {
    this.container.removeClass('open');
};

