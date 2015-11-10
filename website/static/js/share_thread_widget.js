canvas.ShareThreadWidget = Object.createSubclass();

canvas.ShareThreadWidget.prototype.init = function (content, comment_id, type) {
    if (type) {
        this.invite_type = type;
    } else {
        this.invite_type = "invite";
    }

    this.comment_id = comment_id;
    this.content = content;
    this.button = this.content.find('button');

    this.button.click($.proxy(this.submit_invite, this));
    this.content.find('.canvas_username').keypress($.proxy(function () {
        var keycode = (event.keyCode ? event.keyCode : event.which);
        if(keycode == $.ui.keyCode.ENTER){
            this.submit_invite();
        }
    }, this));
};

canvas.ShareThreadWidget.prototype.show_message = function (message) {
    var status_area = this.content.find('.invite_status_message');
    status_area.empty();

    var msg = $("<p/>");
    msg.text(message);
    status_area.append(msg);

    if (this.timer_id) {
        clearTimeout(this.timer_id);
    }

    this.timer_id = setTimeout($.proxy(function () {
        msg.fadeOut("slow", $.proxy(function () {
            msg.remove();
            this.timer_id = null;
        }, this));
    }, this), 5000);
    return msg;
};

canvas.ShareThreadWidget.prototype.make_button_submit_styled = function(bool) {
    if (bool) {
        this.button.attr("disabled", "disabled").addClass("submitting");
    } else {
        this.button.removeClass("submitting").removeAttr("disabled");
    }
};

canvas.ShareThreadWidget.prototype.submit_invite = function () {
    var username_textbox = this.content.find('.canvas_username');
    var username = username_textbox.val();

    if (username.length > 0){
        this.make_button_submit_styled(true);
        var done = $.proxy(function (data, jq_xhr) {
            username_textbox.val("");
            this.show_message("Invited " + username);
            this.make_button_submit_styled(false);
        }, this);

        var fail = $.proxy(function(data, jq_xhr){
            var msg = this.show_message(data.reason);
            msg.addClass('invalid');
           this.make_button_submit_styled(false);
        }, this);

        if (this.invite_type == "monster") {
            canvas.api.invite_canvas_user_to_complete_monster(username, this.comment_id)
            .done(done)
            .fail(fail);
        } else if (this.invite_type == "invite") {
            canvas.api.invite_canvas_user_to_remix(username, this.comment_id)
            .done(done)
            .fail(fail);
        }
        username_textbox.focus();
    }
};

