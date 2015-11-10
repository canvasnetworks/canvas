
var profile_edit = {};

profile_edit.show_start_widget = function() {
    profile_edit.image_chooser.show();

    $("#form_widget").hide();
};

profile_edit.show_form_widget = function() {
    profile_edit.image_chooser.hide();

    $('label[for=remix]').show();
};

profile_edit.start_over = function() {
    profile_edit.image_chooser.start_over();

    window.location.href = window.location.href;
    $('#form_widget').hide();
    profile_edit.show_start_widget();
};

profile_edit.remix = function () {
    action.remix.apply(this, arguments);
    profile_edit.submit_button.attr('disabled', false);
    profile_edit.show_form_widget();
    profile_edit.pw.wire_uploadify();
};

profile_edit.post_submit_callback = function (post, response) {
    canvas.record_metric('posted_thread', {
        'remix_method': profile_edit._last_method,
        'anonymous': $('#postwidget .pw_anonymous').is(':checked'),
        'group': $('#postwidget #category_select_input').val(),
        'tags': $('#postwidget #tag_select_input').val(),
    });
    var comment_id = response.comment.id;
    canvas.api.user_set_profile(comment_id).done(function (response) {
        window.location = '/user/' + current.username;
    });
    return false;
};

profile_edit.wire = function () {

    profile_edit.image_chooser = new canvas.ImageChooser($('.image_chooser'));

    // I'm specifying any DOM nodes here so it's easier to change them
    profile_edit.form = $('#form_widget');
    profile_edit.title_input_field = $('#post_thread_title');
    profile_edit.submit_button = $('input[type=submit]', '#postwidget');
    profile_edit.caption = $('#postwidget #postwidget_caption');

    profile_edit.image_chooser.url_input_button.click(function (event) {
        profile_edit.pw.upload_url(profile_edit.image_chooser.url_input_field.val());
        event.preventDefault();
    });

    profile_edit.image_chooser.start_from.draw.click(function () {
        canvas.record_metric('start_remix_from_draw');
        profile_edit._last_method = 'draw';
        profile_edit.remix(draw_from_scratch_content.id, 'draw');
    });

    var handler = {};

    var pw = new Postwidget({
        container: '#postwidget',
        bind_type: 'stream',
        default_text: '',
        skip_to_remix: true,
        upload_view: handler,
        is_reply: profile_edit.current_comment == null,
        parent_comment: profile_edit.thread_op,
        post_submit_callback: profile_edit.post_submit_callback,
        validator: function (post) {
            return profile_edit.form.valid();
        },
        ignore_reposts: true,
    });


    $('#postwidget').bind('closing', profile_edit.start_over);

    profile_edit.pw = pw;

    pw.wire_uploadify();

    $(handler).bind('uploadend', function (e, content, response, upload_type) {
        var types = {
            uploadify: 'file',
            url: 'url',
        };
        canvas.record_metric('start_remix_from_' + types[upload_type]);
        profile_edit._last_method = types[upload_type];

        profile_edit.show_form_widget();
        pw.wire_uploadify();
    });

    var remixer = profile_edit.remixer = new remix.RemixWidget(pw, $('.remix_widget'));
    remixer._hide_close_button();
    remixer.install_actions();
    remixer.scoped('button').click(function (event) {
        event.preventDefault();
    });

    $('#start_over').click(function (event) {
        event.preventDefault();
        canvas.api.user_set_profile(null).done(function (response) {
            window.location = '/user/' + current.username + '/edit';
        });
    });
};

