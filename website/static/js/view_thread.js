var view_thread = {};

view_thread.replies_per = 3;

view_thread.distribute_image_tiles = function (tiles) {
    for(var i = 0; i < tiles.length; i++){
        if (i%3==0){
            view_thread.column2.append(tiles[i]);
        } else if (i%3==1) {
            view_thread.column3.append(tiles[i]);
        } else {
            view_thread.column1.append(tiles[i]);
        }
    }
};

view_thread.load_more_remixes = function () {
    var page = view_thread.current_page;
    var per = view_thread.num_top;
    var len = Math.min(view_thread.remaining_remixes.length, (page * per) + ((page+1) * per));

    var ids = [];
    for (var i = (page * per); i < len; i++){
        ids.push(view_thread.remaining_remixes[i]);
    }

    if (len == view_thread.remaining_remixes.length){
        $(".sidebar .more a").hide();
    }

    canvas.api.view_thread_more(ids).done(function (response) {
        if ($.trim(response)) {
            var incoming_tiles = $(response).filter("div.image_tile");
            view_thread.distribute_image_tiles(incoming_tiles);
        }
    });

    view_thread.current_page = page + 1;
};

view_thread.load_more_replies = function () {
    var replies = $('.replies').find('.reply');
    var end = replies.length - view_thread.replies_per;
    for (var i=0; i < end; i++){
        $(replies[i]).parent().show();
    }
    $("#page .main_column .replies .more").hide();
};

view_thread.image_tile_formatting = function(rendered_comment, comment, image_type) {
    var comment = new canvas.Comment(comment);
    if (!(image_type == "thumbnail" || image_type == "small_column")) {
        canvas.format_comment_content(rendered_comment, image_type);
    }
    stickers.update_stickerable(rendered_comment, comment.id, comment.sticker_counts, comment.sorted_sticker_counts, comment.top_sticker);
};

view_thread.wire = function() {
    view_thread.remixes = $(".sidebar_remixes");
    view_thread.preload_area = view_thread.remixes.find(".preloaded_tiles");
    view_thread.column1 = view_thread.remixes.find(".column_1");
    view_thread.column2 = view_thread.remixes.find(".column_2");
    view_thread.column3 = view_thread.remixes.find(".column_3");
    view_thread.current_page = 0;

    var tiles_to_sort = view_thread.preload_area.find("div.image_tile");
    view_thread.distribute_image_tiles(tiles_to_sort);

    /* Match the height of the remix button to the image tiles */
    var match_height = $(tiles_to_sort[0]).height();
    $("#page .sidebar .remix_button").css({
        height : match_height,
    });

    var replies = $('.replies').find('.reply');
    if (replies.length <= view_thread.replies_per) {
        $("#page .main_column .replies .more").hide();
    }
    for(var i = replies.length - 1; i >= 0; i--){
        if(i < replies.length - (view_thread.replies_per)){
            $(replies[i]).parent().hide();
        }
    }

    if (view_thread.remaining_remixes.length == 0){
        $(".sidebar .more a").hide();
    }

    var tiles_to_format = [];
    var main_tile_node = $('#page .main_column > .image_tile');
    tiles_to_format.push([main_tile_node, view_thread.main_comment, "giant"]);
    if (view_thread.top_replies.length) {
        $.each(view_thread.top_replies, function(i, reply) {
            tiles_to_format.push([$($('#page .sidebar .image_tile')[i]), reply, "column"]);
        });
    }
    $.each(tiles_to_format, function(i, array) {
        view_thread.image_tile_formatting(array[0], array[1], array[2]);
    });

    /* Unbind click from main tile */
    $(".image_footer", main_tile_node).attr("onClick", null);

    $("#page .remix_wrapper").bind("closing", function() {
        var wrapper = $("#page .remix_wrapper");
        wrapper.animate({
            "opacity" : 0,
        }, 200, function() {
            wrapper.css("z-index", -1);
        });
    });

    var has_parent = typeof view_thread.parent_comment === "object";
    var parent = view_thread.main_comment;
    if (has_parent) {
        parent = view_thread.parent_comment;
    }

    var pw = new Postwidget({
        container: '.remix_wrapper',
        bind_type: 'column',
        default_text: 'Write something!',
        submit_text: 'Reply!',
        parent_comment: parent,
    });

    $('#page .main_column > .image_tile').bind("click", function(e) {
        e.preventDefault();
        e.stopPropagation();
        canvas.record_fact('flow_click_remix');
        view_thread.remix(view_thread.main_comment.reply_content_id);
    });

    $("#page .replies .more a").bind("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        view_thread.load_more_replies();
    });

    $("#page .sidebar .more a").bind("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        view_thread.load_more_remixes();
    });

    $('#page .replies .add_reply, .replies .comment').bind("click", function (e) {
        e.preventDefault();
        canvas.encourage_signup('add_reply');
    })

    // Calling this on the parent comment so it's data gets stored
    if (view_thread.parent_comment) {
        view_thread.parent_comment = new canvas.Comment(view_thread.parent_comment);
    }

    // Hover remix button for main image (it's not built into the image tile template)
    $(main_tile_node).prepend('<div class="remix_link_hover"><img src="/static/img/remix_button_white.png"></div>');

    var remixer = new remix.RemixWidget(pw, $('.remix_widget'));
    remixer.install_actions();
    $('#postwidget div.identity').hide();
    $('#postwidget div.image_chooser').hide();

    pw.pre_submit_callback = function () {
        remixer.unbind_window();
    };
};

view_thread.remix = function(content_id) {
    var source = (content_id == view_thread.main_comment.reply_content_id) ? "view_thread_main" : "view_thread_secondary";
    action.remix(content_id, source);
    if (typeof thread != "undefined" && thread.pw) {
        thread.pw.remix_started();
    }
    var wrapper = $("#page .remix_wrapper");
    wrapper.css("z-index", 3).animate({
        "opacity" : 1,
    }, 400);
};

