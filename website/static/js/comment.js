
canvas.Comment = Object.createSubclass();

canvas.Comment.defaultMessage = 'Write something!';

canvas.Comment.prototype.init = function (data) {
    var self = this;
    $.each(data, function (key, value) {
        self[key] = value;
    });
    this.reply_content = canvas.storeContent(data.reply_content);
    canvas._comments[this.id] = this;
};

canvas.Comment.prototype.getContent = function () {
    return canvas.getContent(this.reply_content_id);
};

canvas.Comment.prototype.getUserURL = function () {
    var anon = this.author_name == "Anonymous",
        admin_name = (this.thread && this.thread.admin_infos && this.thread.admin_infos[this.id]) ? this.thread.admin_infos[this.id].username : false;
        
    if (anon && !admin_name) {
        return "";
    } else if (admin_name) {
        return "/user/" + admin_name;
    } else {
        return "/user/" + this.author_name;
    }
};

canvas.Comment.prototype.has_audio_remix = function () {
    return Boolean(this.external_content.length);
};

canvas.Comment.prototype.get_visibility_name = function () {
    switch (this.visibility) {
        case 0: return "public";
        case 1: return "hidden";
        case 2: return "disabled";
        case 3: return "unpublished";
        case 4: return "curated";
        default: return "unknown";
    }
};

//TODO delete
canvas.Comment.prototype.isDownvoted = function() {
    var scores = stickers.get_scores(this.sticker_counts);
    return scores.downvote >= scores.upvote + 4;
};

//TODO delete
canvas.Comment.prototype.isUnviewable = function() {
    return this.visibility == 2 || this.visibility == 3;
};

//TODO delete?
canvas.Comment.prototype.isCollapsed = function() {
    if (this.isUnviewable()) {
        return false;
    } else {
        return this.visibility == 1 || this.ot_hidden || this.isDownvoted();
    }
};

//TODO delete
canvas.Comment.prototype.isInappropriate = function() {
    if (this.ot_hidden && !this.judged) return false;
    return this.visibility == 1;
};

//TODO delete
canvas.Comment.prototype.isDisabled = function() {
    return this.visibility == 2;
};

//TODO delete
canvas.Comment.prototype.isRemoved = function() {
    return this.visibility == 3;
};

//TODO delete
canvas.Comment.prototype.isOffTopic = function () {
    return this.ot_hidden;
};

//TODO delete
canvas.Comment.prototype.getModClasses = function() {
    var classes = '';
    if (this.isInappropriate()) {
        classes += ' inappropriate';
    } else if (this.isOffTopic()) {
        classes += ' offtopic';
    } else if (this.isDownvoted()) {
        classes += ' downvoted';
    } else if (this.isDisabled()) {
        classes += ' disabled';
    } else if (this.isRemoved()) {
        classes += ' disabled';
    }
    
    // Add the collapsed class if any of the above were true.
    if (classes) {
        classes += ' collapsed';
    }
    return classes;
};

//TODO delete
canvas.Comment.prototype.collapsedText = function() {
    if (this.isRemoved()) {
        return 'This post was deleted by its author.';
    } else if (this.isDisabled()) {
        return 'This post has been disabled.';
    } else if (this.isInappropriate()) {
        return 'This post has been flagged as inappropriate. Click to show.';
    } else if (this.isOffTopic()) {
        return 'This post was marked off-topic by a group referee. Click to show.';
    } else if (this.isDownvoted()) {
        return 'This post is hidden due to downvotes. Click to show.';
    }
};

//TODO delete
canvas.Comment.prototype.getRepliedText = function () {
    var reply_to_op = thread && thread.op_comment && this.id == thread.op_comment.id;
    var replied_text = '@' + (reply_to_op ? 'DAVE DICED' : this.replied_comment.author_name);
    if (this.reply_text) {
        replied_text += ':';
    }
    return replied_text;
};

//TODO delete?
canvas.Comment.prototype.getLinkedComment = function () {
    if (this.parent_comment && this.parent_url && (this.parent_comment.reply_count >= this.reply_count)) {
        return this.parent_comment;
    } else {
        return this;
    }
};

canvas.Comment.prototype.getCommentURL = function() {
    var url = this.url;
    
    // The URL of a comment (and its parent) should keep you under the current nav_category.
    if (current.nav_category.name != current.default_category.name) {
        url += '?nav=' + current.nav_category.name;
    }
    
    return url;
};

//TODO delete
canvas.Comment.prototype.render = function (options) {
    var post = $(canvas.render('#' + options.template + '_template', {'comment': this, 'options': options}));
    var content = this.getContent();
    if (content) {
        var node = $('img.comment-image', post);
        // Click to play instead, unless it's the OP
        if (options.image_type == "giant" && content.original.animated) {
            content.bindToImage(node, 'ugc_original');
            node.attr({'width': content[options.image_type].width, 'height': content[options.image_type].height });
        } else {
            content.bindToImage(node, options.image_type);
        }
    }
    return post;
};

canvas.Comment.remove = function (comment_id, stay_on_page) {
    console.log(stay_on_page);
    var location;
    if (stay_on_page) {
        location = window.location.href;
    } else {
        location = '/user/' + current.username;
    }
    console.log(location);
    new canvas.ConfirmDialog({
        title:"Delete this post?",
        message:"This post will be deleted, but not replies to it. This cannot be undone!",
        cancel_text: "Cancel",
        ok_text: "Delete",
        success: function() {
            canvas.api.delete_comment(comment_id).done(function (response) {
                new canvas.AlertDialog('Your post has been successfully deleted.', function() {
                    window.location.href = location;
                }, true);
            }).fail(function (reason) {
                new canvas.AlertDialog("An error has occurred, sorry! Please email bugs@example.com and we'll get it taken care of.");
            });
        },
    });
};

canvas.Comment.claim = function(comment_id, stay_on_page) {
    var location;
    if (stay_on_page) {
        location = window.location.href;
    } else {
        location = '/user/' + current.username;
    }
    new canvas.ConfirmDialog({
        title:"Claim this post?",
        message:"Are you sure you want to make this post non-anonymous? This CANNOT be undone. This post will be attributed to you and will appear on your user page.",
        cancel_text: "Cancel",
        ok_text: "OK",
        success: function() {
            canvas.api.claim_comment(comment_id).done(function (response) {
                new canvas.AlertDialog('Your post has been successfully claimed.', function() {
                    window.location.href = location;
                }, true);
            }).fail(function (reason) {
                new canvas.AlertDialog("An error has occurred, sorry! Please email bugs@example.com and we'll get it taken care of.");
            });
        },
    });
};

