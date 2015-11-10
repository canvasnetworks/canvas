// Warning: This file is NOT conditionally included, it's always compressed and available for everyone.

var admin = {};
admin.wrapped_sticker_drop = null;

admin.moderate = function(moderate, visibility, comment_id, callback) {
    var callback = callback ? callback : admin.update_status;
    // When undoing we need to tell the server so it knows how to handle Comment.judged.
    undoing = false;
    if (visibility == 'undo') {
        visibility = 'public';
        undoing = true;
    }
    return canvas.jsonPOST(
        '/api/' + moderate + '/moderate',
        {
            visibility: visibility,
            comment_id: comment_id,
            undoing: undoing,
        },
        callback
    );
};

admin.sticky = function(comment_id, callback) {
    var callback = callback ? callback : admin.update_status;
    var text = prompt("Sticky text?");
    var response = canvas.api.sticky_comment(comment_id, text);
    callback();
};

admin.update_status = function(info) {
    $('.admin').replaceWith(canvas.render('#comment_admin_template', info));
};

admin.on_admin_sticker_drop = function(drag, drop, comment_id, type_id) {
    // Admin call wrapper, handling drag/drop and overlay message.
    var placeholder = $("#sticker_widget .empty");
    var admin_call = function(callable, message, undo) {
        callable(function() {
            stickers.overlay_message(drop, message + ' <a class="overlay_link" href="#" onclick="' + undo + '">Undo</a>');
            stickers.on_drop_success(drag, drop, comment_id, {'new_counts': {}});
        });
    }

    var hide_callback = "function(){$('.drop_target_border').css({zIndex:-1});}";
    // Visibility moderation.
    if (type_id == 901 || type_id == 8902) {
        var visibility = {
            901: 'hidden',
            8902: 'curated',
        }[type_id];
        admin_call(admin.moderate.partial('comment', visibility, comment_id), 'Post successfully ' + visibility + '.', "admin.moderate('comment', 'undo', " + comment_id + ", " + hide_callback + ')');
    } else if (type_id == 8903) {
        admin_call(admin.sticky.partial(comment_id), 'Post successfully stickied.', '({})');
    } else {
        throw new Error(type_id + ' is not a valid admin sticker type.');
    }
};
