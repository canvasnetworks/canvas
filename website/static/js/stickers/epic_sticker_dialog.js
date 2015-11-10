
canvas.EpicStickerDialog = canvas.Dialog.createSubclass();

canvas.EpicStickerDialog.prototype.default_args = {
    click_to_dismiss: true,
    esc_to_dismiss: true,
    title: 'Epic Sticker',
    has_alert: true,
};

canvas.EpicStickerDialog.prototype.init = function (success, cancel) {
    canvas.EpicStickerDialog.__super__.init.apply(this, [{}, success, cancel]);
};

canvas.EpicStickerDialog.prototype.create_content = function () {
    var content = $('<div class="epic_sticker_dialog"></div>');
    $('<label for="epic_sticker_message_input"></label>').text("If you like, attach a short private message to this sticker:").addClass('prompt').appendTo(content);
    var form = $('<form></form>').appendTo(content);
    var wrapper = $('<div></div>').addClass('input_wrapper').appendTo(form);
    var input = $('<input type="text" id="epic_sticker_message_input" maxlength="140">').appendTo(wrapper);
    $('<div></div>').addClass('from').html('&mdash; from ').append($('<span></span>').text(current.username)).appendTo(wrapper);
    var submit = $('<input type="submit" class="advance" value="Send">').appendTo(form);

    submit.click($.proxy(function (event) {
        event.preventDefault();
        this.close(true);
    }, this));

    var skip = $('<a></a>').text("No thanks, send the sticker without a message");
    $('<div></div>').addClass('skip').append(skip).appendTo(content);

    skip.click($.proxy(function (event) {
        event.preventDefault();
        this.close();
    }, this));

    return content;
};

canvas.EpicStickerDialog.prototype.wire_container = function () {
    canvas.EpicStickerDialog.__super__.wire_container.apply(this, arguments);
    this.content.find('input').first().focus();
};

canvas.EpicStickerDialog.prototype.get_message = function () {
    return this.content.find('input[type="text"]').val();
};

