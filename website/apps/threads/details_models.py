from apps.client_details.models import ClientDetailsBase


class ThreadDetails(ClientDetailsBase):
    def __init__(self, comment_details):
        """ `comment_details` can be either the parent comment, or any comment within the thread. """
        from canvas.details_models import CommentDetails

        if getattr(comment_details, 'parent_id', None):
            op = CommentDetails.from_id(comment_details.parent_id)
        else:
            op = comment_details
            if not isinstance(op, CommentDetails):
                op = CommentDetails(comment_details)
        self.op = op

    @property
    def title(self):
        return self.op.title

    @property
    def reply_count(self):
        return self.op.reply_count

    @property
    def author_count(self):
        return self.op.thread_author_count

