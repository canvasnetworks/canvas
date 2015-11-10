//TODO move all the subclasses of Dialog into their own non-reusable files. This is getting cluttered.
canvas.Dialog = Object.createSubclass();

canvas.Dialog.prototype.default_args = {
    has_alert: true,
};

canvas.Dialog.prototype.init = function (args, success, cancel) {
    if ($('.modal_container').length) {
        return false;
    }

    this.args = {
        title: null,
        message: null,
        fade: true,
        success: success,
        cancel: cancel,
        click_to_dismiss: false,
        esc_to_dismiss: false,
    };

    $.extend(this.args, this.default_args);
    $.extend(this.args, args);

    this.wire_container();
    this.resize();
};

canvas.Dialog.prototype.get_left_position = function () {
    return ($(window).width()/2) - (this.content.outerWidth()/2);
};

canvas.Dialog.prototype.get_top_position = function () {
    if(this.args.position_at_top){
         return ($(window).height()/4) - (this.content.outerHeight()/4);
    } else {
         return ($(window).height()/2) - (this.content.outerHeight()/2);
    }
};

canvas.Dialog.prototype.resize = function () {
    this.content_container().css({
        display : "block",
        position : "absolute",
        left: this.get_left_position(),
        top: this.get_top_position(),
    });
};

canvas.Dialog.prototype.create_frame = function () {
    var frame = $('<div class="modal"></div>');
    if (this.args.has_alert) {
        frame.addClass('alert');
    }
    return frame;
};

canvas.Dialog.prototype.create_title = function () {
    if (this.args.has_alert && this.args.title) {
        return $('<h1>' + this.args.title + '</h1>');
    }
};

canvas.Dialog.prototype.create_content = function () {
    return $('<div></div>')
};

canvas.Dialog.prototype.content_container = function () {
    return this.content_frame;
};

canvas.Dialog.prototype.wire_container = function () {
    this.wrapper = $("<div></div>").addClass('iframe_wrapper');
    this.modal = $("<div></div>").addClass('modal_container').css({ zIndex: 100 }).append(this.wrapper);

    if (this.args.modal_class) {
        this.modal.addClass(this.args.modal_class);
    }

    $(document.body).append(this.modal);

    this.content_frame = this.create_frame();
    this.modal.append(this.content_frame);

    this.content = this.create_content().addClass('dialog_content');
    this.content_container().append(this.content);
    this.content.show();

    this.title = this.create_title();
    this.content.prepend(this.title);

    $(window).bind("resize.modal_container", this.resize.bind(this));
    this.resize();

    if (this.args.click_to_dismiss) {
        this.modal.bind("click", $.proxy(function (e) {
            if (!$(e.target).parents(".modal_container > *").length) {
                this.close();
            }
        }, this));
    }
    if (this.args.esc_to_dismiss) {
        $('body').bind('keyup.canvas', $.proxy(function (e) {
            if (e.keyCode === $.ui.keyCode.ESCAPE) {
                this.close();
                e.preventDefault();
            }
        }, this));
    }

    this.modal.show();
};

canvas.Dialog.prototype.destroy = function () {
    $([window, document]).unbind(".modal_container");
    $('body').unbind('keyup.canvas');
    this.modal.remove();
};

canvas.Dialog.prototype.close = function (successful) {
    this.modal.animate({ opacity: 0 }, 200, $.proxy(function () {
        $(this).css({ zIndex: -100 });
        if (successful && this.args.success) {
            this.args.success();
        } else if (this.args.cancel) {
            this.args.cancel();
        }
        this.destroy();
    }, this));
};


canvas.ConfirmDialog = canvas.Dialog.createSubclass();

canvas.ConfirmDialog.prototype.default_args = {
    ok_text: "OK",
    cancel_text: "Cancel",
    default_button: 'ok',
    extra_buttons: null,
    has_alert: true,
    esc_to_dismiss: true,
};

canvas.ConfirmDialog.prototype.init = function (args, success) {
    if (typeof args === "string") {
        args = { message: args };
    }
    canvas.ConfirmDialog.__super__.init.apply(this, [args, success]);
};

canvas.ConfirmDialog.prototype.wire_container = function () {
    canvas.ConfirmDialog.__super__.wire_container.apply(this, arguments);

    this.content.append('<p>' + this.args.message + '</p><div class="buttons"><input class="button_cancel cancel dismiss" type="submit" value="'+ this.args.cancel_text + '"><input class="button_submit ok" type="submit" value="' + this.args.ok_text + '"></div>');

    if (this.args.extra_buttons){
        this.args.extra_buttons.insertAfter(this.content.find('.button_cancel'));
    }

    this.content.find('.button_cancel').click($.proxy(function () {
        this.close();
    }, this));

    var submit_button = this.content.find('.button_submit');
    submit_button.click($.proxy(function () {
        this.close(true);
    }, this));

    this.content.find('.buttons .' + this.args.default_button).focus();
};

canvas.ConfirmDialog.prototype.destroy = function () {
    $('body').unbind('keyup.canvas');
    canvas.ConfirmDialog.__super__.destroy.apply(this, arguments);
};


canvas.AlertDialog = canvas.Dialog.createSubclass();

canvas.AlertDialog.prototype.default_args = {
    ok_text: "OK",
    default_button: 'ok',
    has_alert: true,
    esc_to_dismiss: true,
};

canvas.AlertDialog.prototype.init = function (args, success, cancel) {
    if (typeof args === 'string') {
        args = { message: args };
    }
    canvas.AlertDialog.__super__.init.apply(this, arguments);
};

canvas.AlertDialog.prototype.wire_container = function () {
    canvas.AlertDialog.__super__.wire_container.apply(this, arguments);

    this.content.append('<p>' + this.args.message + '</p><div class="buttons"><input class="button_submit ok" type="submit" value="' + this.args.ok_text + '"></div>');

    this.content.find(".buttons ." + this.args.default_button).focus();

    var submit_button = this.content.find(".button_submit");
    submit_button.click($.proxy(function () {
        this.close(true);
    }, this));
};


canvas.EncourageSignupDialog = canvas.Dialog.createSubclass();

canvas.EncourageSignupDialog.prototype.default_args = {
    has_alert: false,
    click_to_dismiss: true,
};

canvas.EncourageSignupDialog.prototype.init = function (reason, info) {
    this.info = info || {};
    this.info.reason = reason;

    canvas.record_metric('login_wall', info);

    this.get_arg = "?info=" + encodeURIComponent(JSON.stringify(this.info));
    if (this.info.post) {
        this.get_arg += "&post_pending";
        this.get_arg += "&small_column_url=" + encodeURIComponent(this.info.content.small_column.url);

        after_signup.post_comment(this.info.post);
    } else if (this.reason === "sticker") {
        this.get_arg += "&sticker_limit";
    }

    canvas.EncourageSignupDialog.__super__.init.apply(this, []);
};

canvas.EncourageSignupDialog.prototype.wire_container = function () {
    canvas.EncourageSignupDialog.__super__.wire_container.apply(this, arguments);

    var close = $("<div></div>").addClass('close').appendTo(this.content);
    $(".close", this.wrapper).bind("click", $.proxy(function () {
        this.close();
    }, this));
};

canvas.EncourageSignupDialog.prototype.content_container = function () {
    return this.wrapper;
};

canvas.EncourageSignupDialog.prototype.create_content = function () {
    var content_container = $('<div></div>');
    var iframe = $('<iframe src="https://' + window.location.hostname + '/signup_prompt' + this.get_arg + '" width="500px" height="550px" scrolling="no" seamless></iframe>').appendTo(content_container);

    $("body").trigger("click");

    $("a.login", this.wrapper).attr("href", "/login?next=" + window.location.pathname);

    $(document).bind("keydown.modal_container", $.proxy(function(event) {
        if (!event.isDefaultPrevented() && event.keyCode && event.keyCode === $.ui.keyCode.ESCAPE) {
            this.destroy();
            event.preventDefault();
        }
    },this));

    return content_container;
};

