var ThreadComment = canvas.ThreadComment = canvas.Comment.createSubclass();

ThreadComment.prototype.init = function (thread_, comment_data) {
    this.thread = thread_;

    // Take on some first-class relationships, then create the comment object.
    // The comment here isn't always a child of the OP, in the case of the OP itself and the sidebar.
    if (comment_data.parent_id == this.thread.op_comment.id) {
        comment_data.parent_comment = this.thread.op_comment;
    }
    if (this.thread.op_category && comment_data.category == this.thread.op_category.name) {
        comment_data.category = this.thread.op_category;
    }

    ThreadComment.__super__.init.call(this, comment_data);

    // SERVERSIDETODO:
    // bind dragstart from bindContent

    // Populate the full replied_comment if it has an id.
    if (this.replied_comment) {
        //TODO port thread.get_replied_comment to a Thread method
        this.replied_comment = this.thread.get_replied_comment(this.replied_comment.id);
    }

    //TODO port to Thread rather than thread module
    this.thread.replies[this.id] = true;
    new_timestamp = Math.max(this.thread.last_timestamp, this.timestamp);
    if (new_timestamp) {
        this.thread.last_timestamp = new_timestamp;
    }
};

