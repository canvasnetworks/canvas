explore = {};

explore.wire = function() {
    // Don't show "loading more" if there are only a few responses
    var initial_results = $('#content_well ' + explore.tile_selector);
    if (initial_results.length < explore.post_offset) {
        $('#content > footer').hide();
        if (!initial_results.length) {
            var text_feedback = ($('#content_header .disabled').length) ? "This account is disabled." : "No results found.";
            $('#content_well').append('<p>' + text_feedback + '</p>');
            return;
        }
    }
    smooth_scroll.wire({
        selector            : "explore_tile",
        top_threshold       : 2000,
        bottom_threshold    : 4000,
    });

    // Handle posts already loaded in
    explore.handle_tiles(initial_results);

    // Infinite Scroll
    canvas.infinite_scroll({
        buffer_px: 1500,
        cutoff_selector: $('#content > footer'),
        scroll_callback: function (disable_scroll_callback) {
            return explore.api_more({
                    'nav_data'      : explore.nav_data,
                    'offset'        : explore.post_offset,
                    'tile_renderer' : explore.tile_renderer,
                }, function (response) {
                    response = $(response);

                    var incoming_tiles = response.filter(explore.tile_selector);
                    incoming_tiles = explore.dedupe_tiles(incoming_tiles);

                    if (!incoming_tiles.length) {
                        disable_scroll_callback();
                        $('#content > footer').hide();
                        return;
                    }

                    explore.post_offset += incoming_tiles.length;
                    explore.handle_tiles(incoming_tiles);
                    explore.sort_into_columns(incoming_tiles);

                    smooth_scroll.add_items(incoming_tiles);
                }
            );
        }
    });
};

explore.dedupe_tiles = function(incoming_tiles) {
    var tiles = $();
    $.each(incoming_tiles, function(_, tile) {
        var id = $(tile).data("comment_id");
        if (!canvas.getComment(id)) {
            tiles = tiles.add(tile);
        }
    });
    return tiles;
};

explore.handle_tiles = function(tiles) {
    // We have to create these for sharing to work
    tiles.each(function() {
        new canvas.NComment(this);
    });
};

explore.sort_into_columns = function(tiles) {
    // We're going to sort the tiles into jQuery objects
    // so that we only have to do 3 DOM manipulations
    var tile_groups = {
        group_1 : $(),
        group_2 : $(),
        group_3 : $(),
    }

    // Sort into 3 groups
    tiles.each(function(i, tile) {
        var group_name = "group_" + (i%3 + 1);
        tile_groups[group_name] = tile_groups[group_name].add($(tile));
    });

    // Then add each group to the respective column
    $('#content_well > .column > div:first-of-type').each(function(i, column) {
        $(column).append(tile_groups["group_" + (i + 1)]);
    });

    explore.even_out_columns();
};

explore.even_out_columns = function() {
    // Call this anytime we load in new tiles
    // It just looks nicer :)
    var columns = [];
    $('#content_well > .column').each(function() {
        var column = $(this);
        var filler = $('.filler', column);
        filler.css({
            display : "none",
            height  : 0,
        });

        var height = column.height();
        columns.push({
            height  : height,
            filler  : filler,
        });
    });
    columns.sort(function(a, b) {
        if (a.height >= b.height) {
            return -1;
        } else {
            return 1;
        }
    });
    // We need to find out what the margin-bottom is for threshold
    var margin = 25;
    for (var i = 1; i < columns.length; i++) {
        // Skip over the tallest column,
        // check the others to see if we dislay the filler
        var column = columns[i];
        var difference = columns[0].height - column.height - margin;
        if (difference > margin) {
            column.filler.css({
                display : "block",
                height  : difference,
            });
        }
    }
};
