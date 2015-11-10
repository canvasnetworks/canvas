canvas.RemixShortcutsDialog = canvas.Dialog.createSubclass();

canvas.RemixShortcutsDialog.prototype.default_args = {
    click_to_dismiss: true,
    esc_to_dismiss: true,
    title: 'Remixer Keyboard Shortcuts',
    has_alert: true,
};

canvas.RemixShortcutsDialog.prototype.create_content = function () {
    var content = $('<div class="remix_shortcuts_dialog"></div>');
    var list = $('<ul class="shortcuts"><li>');
    content.append(list);
    $.each(canvas.RemixShortcutsDialog.shortcuts, function (_, shortcut) {
        var container = $('<li></li>');
        var key = $('<div class="key"><span>' + shortcut[0] + '</span></div>');
        var desc = $('<div class="description"><span>' + shortcut[1] + '</span></div>');
        container.append(key).append(desc);
        list.append(container);
    });
    return content;
};

