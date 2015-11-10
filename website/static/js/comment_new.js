// This is a replacement for comment.js
// Once this is done, comment.js will be deleted and this stuff will be renamed to just "comment".

canvas.NComment = function(tile_node) {
    // This has a `node` property that contains the DOM node of this comment.
    
    var self = this;
    tile_node = $(tile_node);
    this.node = tile_node[0];

    // Add every key,val pair from the details data to this object as properties.
    $.each(tile_node.data('details'), function (key, value) {
        self[key] = value;
    });
    
    this.reply_content = this.reply_content ? canvas.storeContent(this.reply_content) : this.reply_content;
    canvas._comments[this.id] = this;
};

//TODO is this needed? it's used in thread.js, but maybe unnecessary
canvas.NComment.prototype.is_collapsed = function() {
    return this.node.hasClass('collapsed');
};

canvas.NComment.prototype.get_content = function () {
    return canvas.getContent(this.reply_content_id);
};

// Camelcase is deprecated
canvas.NComment.prototype.get_comment_url = canvas.NComment.prototype.getCommentURL = canvas.Comment.prototype.getCommentURL;