var post_thread = {};

post_thread.show_start_widget = function() {
    post_thread.image_chooser.show();

    $("#form_widget").hide();
};

post_thread.show_form_widget = function() {
    post_thread.image_chooser.hide();

    $('label[for=remix]').show();
};

post_thread.start_over = function() {
    post_thread.image_chooser.start_over();

    window.location.href = window.location.href;
    $('#form_widget').hide();
    post_thread.show_start_widget();
};

post_thread.remix = function () {
    action.remix.apply(this, arguments);
    post_thread.submit_button.attr('disabled', false);
    post_thread.show_form_widget();
    post_thread.pw.wire_uploadify();
};

post_thread.post_submit_callback = function (post, response) {
    var comment = response.comment;
    var is_remix = response.comment.reply_content.id;
    var comment_url = 'http://' + document.domain + comment.url;

    if (is_remix && current.enable_timeline_posts) {
        FB.getLoginStatus(function(response) {
            if (response.authResponse) {
                var accessToken = response.authResponse.accessToken;
                canvas.api.share_remix(comment_url, accessToken)
            }
        });
    }

    canvas.record_metric('posted_thread', {
        'remix_method': post_thread._last_method,
        'anonymous': $('#postwidget .pw_anonymous').is(':checked'),
        'group': $('#postwidget #category_select_input').val(),
        'tags': $('#postwidget #tag_select_input').val().replace(/#/g, ''),
    });
    return true;
};

post_thread.ignore_reposts = false;
post_thread.quest_idea = false;
post_thread.is_quest = false;

post_thread.wire = function () {
    canvas.record_metric('post_thread_page_view');

    post_thread.image_chooser = new canvas.ImageChooser($('.image_chooser'));

    // I'm specifying any DOM nodes here so it's easier to change them
    post_thread.form = $('#form_widget');
    post_thread.title_input_field = $('#post_thread_title');
    post_thread.submit_button = $('input[type=submit]', '#postwidget');

    post_thread.image_chooser.url_input_button.click(function (event) {
        post_thread.pw.upload_url(post_thread.image_chooser.url_input_field.val());
        event.preventDefault();
    });

    post_thread.image_chooser.start_from.draw.click(function () {
        canvas.record_metric('start_remix_from_draw');
        post_thread._last_method = 'draw';
        post_thread.remix(draw_from_scratch_content.id, 'draw');
    });

    var handler = {};

    var pw = new Postwidget({
        container: '#postwidget',
        bind_type: 'stream',
        default_text: '',
        skip_to_remix: true,
        upload_view: handler,
        ignore_reposts: post_thread.ignore_reposts,
        quest_idea: post_thread.quest_idea,
        post_submit_callback: post_thread.post_submit_callback,
        validator: function (post) {
            return post_thread.form.valid();
        },
    });

    $('#postwidget').bind('closing', post_thread.start_over);

    post_thread.pw = pw;

    pw.wire_uploadify();

    $(handler).bind('uploadend', function (e, content, response, upload_type) {
        var types = {
            uploadify: 'file',
            url: 'url',
        };
        canvas.record_metric('start_remix_from_' + types[upload_type]);
        post_thread._last_method = types[upload_type];

        post_thread.show_form_widget();
        pw.wire_uploadify();
    });

    var remixer = new remix.RemixWidget(pw, $('.remix_widget'), post_thread.quest_idea, post_thread.is_quest);
    remixer.install_actions();
    remixer.scoped('button').click(function (event) {
        event.preventDefault();
    });

    $('#tag_select_input').tagit({
        animate : false,
    });
};

