browse = {};

//TODO kill
browse.page_footer_adjust = function () {
    if (!$('#footer').length) { return; }

    // When loading in more, make sure not to push the footer down more
    if (!browse.scrolling.is_fixed && !browse.scrolling.is_locked) {
        $("#footer").css({
            position    :"fixed",
            bottom      :-$("#footer").outerHeight(true),
            left        :0,
            zIndex      :4,
            width       :"100%",
        });
        $("#page").css("margin-bottom", parseInt($("#page").css("margin-bottom")) + $("#footer").outerHeight(true));
        browse.scrolling.footer_offset = -$("#footer").outerHeight(true) * 2;
        browse.scrolling.is_fixed = true;
    }
};

browse.handle_posts = function (posts) {
    browse.posts_received += 1;
    // Handle duplicate posts
    var new_posts = [];
    $.each(posts, function(i, post) {
        var id = $(post).data('comment_id');
        if ($.inArray(id, browse.post_ids) === -1) {
            //TODO: flush the parent on a moderation.
            post = new canvas.NComment(post);
            new_posts.push(post);
            browse.post_ids.push(post.id);
        }
    });
    browse.insert_tiles(new_posts);
};

browse.load_more_posts = function () {
    browse.loading_node.show();
    browse.api_more({
            'nav_data'  : browse.nav_data,
            'offset'    : browse.state.offset,
            'tile_renderer' : browse.tile_renderer,
        }, function(response) {
            if ($.trim(response)) {
                var incoming_tiles = $(response).filter(browse.tile_selector);
                browse.handle_posts(incoming_tiles);
                browse.page_footer_adjust();
            }
            browse.loading_node.hide();
            browse.state.listen_for_scroll = true;
        }
    );
    browse.state.offset += browse.nav_data.pagination_size;
};

browse.standard_sorting = function (tiles, tile_nodes) {
    $(browse.column_nodes[0]).append(tile_nodes);
    $(browse.column_nodes[0]).append('<br>');
    $.each(tiles, function(i, comment) {
        stickers.update_stickerable($('.post_'+comment.id), comment.id, comment.sticker_counts, comment.sorted_sticker_counts, comment.top_sticker);
    });
}

browse.quilt_sorting = function (tiles, tile_nodes) {
    columns = browse.column_nodes;

    // First, remove any existing footers.
    columns.find('.footer').remove();

    // Resize/fit images 
    var size_threshold = 100;
    tile_nodes.find('.image_container').each(function () {
        var target_img = $(this).children("img");

        // NOTE: these depend on width and height being specified in the HTML.
        var img_width = target_img.attr('width');
        var img_height = target_img.attr('height');
        var container_width = 250;

        // Center the image by padding at most 50 pixels vertically
        if (img_width < container_width) {
            var new_padding = Math.min((container_width-img_width) / 2, 50);
            $(this).css({paddingTop: new_padding, paddingBottom: new_padding});
            target_img.addClass("small_image");
        }
    });

    // Then sort images into rows into height best possible
    var last_column = 0;
    var last_parent_cid = -1;
    var last_cid = -1;
    $.each(tiles, function (i, tile) {
        var node = $(tile.node);
        
        var cid = tile.id;
        var parent_cid = tile.parent_id;
        var column;
        
        if ((browse.should_group_by_thread && last_parent_cid && (last_parent_cid == parent_cid || last_parent_cid == cid)) || last_cid == parent_cid) {
            column = last_column;
            node.appendTo($(columns[column]).find('div.op_tile_group:last'));
        } else {
            var shortest_column = 0;
            var shortest;

            columns.each(function (i) {
                // Favor left to right by 70 vertical pixels
                var column_height = $(this).height();
                if (shortest == null || column_height < (shortest - 70)) {
                    shortest_column = i;
                    shortest = column_height;
                }
            });

            column = shortest_column;
            var div = $('<div class="op_tile_group"></div>');
            div.append(node);
            $(columns[column]).append(div);

            // Add a pin if necessary.
            if (node.hasClass('pinned')) {
                stickers.add_pin_to_comment(tile.id);
            }
        }
                
        last_parent_cid = parent_cid;
        last_cid = cid;
        last_column = column;
    });

    // Make them stickerable.
    // This needs to happen before the footers since stickers affect the size of the image tiles
    $.each(tiles, function (i, comment) {
        stickers.update_stickerable($('.post_'+comment.id), comment.id, comment.sticker_counts, comment.sorted_sticker_counts, comment.top_sticker);
    });

    // Create footers to even out the bottom while waiting for next load
    var tallest = 0;
    var tallest_column = 0;
    var shortest;
    columns.each(function (i) {
        var column_height = $(this).height();
        if (column_height > tallest) {
            tallest_column = i;
            tallest = column_height;
        }
        if (shortest == null || column_height < shortest) {
            shortest_column = i;
            shortest = column_height;
        }
    });
    var column_margin_bottom = parseInt($('#column_1 .image_tile').css('margin-bottom'), 10);
    columns.each(function (i) {
        var column = $(this);
        var tallest_height = $(columns[tallest_column]).height();
        var column_height = column.height()
        var footer_height = tallest_height - column_height - column_margin_bottom;
        var last_image_tile_footer = column.children('.op_tile_group:last-child').children('.image_tile:last-child').find('.image_footer');
        if (footer_height > 20) {
            var last_image_tile_theme = "";
            if (last_image_tile_footer.length) {
                var classes = last_image_tile_footer.attr("class").split(" ");
                last_image_tile_theme = classes[classes.length - 1];
            }
            column.append('<div class="footer sticker_themed ' + last_image_tile_theme +'" style="height:' + footer_height + 'px"></div>');
        } else if (footer_height + column_margin_bottom > 0) {
            // Pad the image_footer out if there's not room for a full footer
            last_image_tile_footer.css('padding-bottom', tallest_height - column_height);
        }
    });
}

browse.insert_tiles = function (tiles) {
    var tile_nodes = $($.map(tiles, function (tile){ return tile.node; }));
    browse.sorting_fun(tiles, tile_nodes);
};

browse.wire = function () {
    // Handle the posts that were preloaded in the DOM.
    browse.handle_posts(browse.preloaded_posts);

    // Footer + infinite scrolling logic
    if (!current.is_mobile && $('#footer').length) {
        var s = browse.scrolling;
        $(window).scroll(function(e) {
            if ($(window).scrollTop() < s.last_scrolltop && s.is_fixed) {
                // Scrolling up
                s.is_locked = false;
                if ($('#footer').length) {
                    s.footer_offset = $(window).scrollTop() - s.last_scrolltop + s.footer_offset;
                    s.footer_offset = Math.min(s.footer_offset, 0);
                    $("#footer").css({bottom:s.footer_offset});
                    var difference = $("#footer").offset().top + $("#footer").outerHeight(true) - $(document).height();
                    if (difference > 0) {
                        s.footer_offset += difference;
                        s.footer_offset = Math.min(s.footer_offset, 0);
                        $("#footer").css({bottom:s.footer_offset});
                    }
                }
            }
            else if ($(window).scrollTop() > s.last_scrolltop && s.is_fixed && !s.is_locked) {
                // Scrolling down
                s.is_locked = false;
                s.footer_offset = s.footer_offset + $(window).scrollTop() - s.last_scrolltop;
                s.footer_offset = Math.min(s.footer_offset, 0);

                $("#footer").css({bottom:s.footer_offset});
                if (s.footer_offset >= 0) {
                    s.is_locked = true;
                    $("#footer").css({bottom:0});
                    s.footer_offset = 0;
                }
            }
            else if (($(window).scrollTop() + $(window).height()) >= ($("#footer").offset().top + $("#footer").outerHeight()) && !s.is_fixed && !s.is_locked) {
                s.is_fixed = true;
                s.is_locked = true;
                $("#footer").css({position:"fixed", bottom:0, left:0, zIndex:4, width:"100%"});
                $("#page").css("margin-bottom", parseInt($("#page").css("margin-bottom")) + $("#footer").outerHeight(true));
                $(window).scrollTop($(window).scrollTop() + $("#footer").outerHeight(true));
            }
            s.last_scrolltop = $(window).scrollTop();
        });
    }

    // Infinite Scroll Loading
    $(window).scroll(function (e) {
        if (
            (browse.state.listen_for_scroll && browse.posts_received >= browse.posts_requested) &&
            ($(window).scrollTop() + $(window).height() >= $("#infinite_scroll_cutoff").offset().top - browse.scrolling.inf_load_offset)
        ) {
            // Increment the requested count, used above so multiple scroll events don't trigger loading in the same chunk a bunch of times.
            browse.posts_requested += 1;
            browse.load_more_posts();
        }
    });

    // Hide the "empty" message if there are no visible tiles. We do this in JS because there are multiple reasons a post can be invisible
    // For example, if it is a repost and you've turned on the hide-reposts feature. 
    if ($(browse.tile_selector + ':visible').length == 0){
        browse.empty_message_node.show();
    }
};

