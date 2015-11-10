canvas.wire_tag_editing = function (base_selector) {
    if (typeof base_selector == 'undefined') {
        var base_selector = $(document);
    }

    var tags = $('p.tags', base_selector);
    var edit_section = $('hgroup div.edit_tags', base_selector);
    var edit_link = $('hgroup a.edit_tags_link', base_selector);
    var save_link = $('a.save_tags_link', edit_section);
    var tag_input = $('#tag_select_input', edit_section);

    base_selector.delegate('a.edit_tags_link', 'click', function (event) {
        event.preventDefault();
        tags.hide();
        edit_link.hide();
        save_link.show();
        edit_section.show();
        tag_input.tagit({
            animate : false,
        });
    });

    save_link.click(function (event) {
        event.preventDefault();
        var comment_id = $(event.target).data('comment_id');
        var new_tags = tag_input.tagit('assignedTags');
        canvas.api.update_comment_tags(comment_id, new_tags).done( function(response) {
            if (response.success) {
                tags.html('');
                for (var i = 0; i < response.tags.length; i++){
                    var t = response.tags[i];
                    tags.append('<a href="' + t.url + '" class="tag_link">' + t.name + '</a> \n');
                }
                tags.append('<a href="#" class="edit_tags_link">Edit</a>');
            }
        });

        tags.show();
        edit_link.show();
        save_link.hide();
        edit_section.hide();
    });
};

$(function () {
    canvas.wire_tag_editing();
});
