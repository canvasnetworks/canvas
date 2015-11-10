from canvas import models, knobs
from canvas.exceptions import ServiceError

def validate_and_clean_comment(user, reply_text='', parent_comment=None, replied_comment=None,
                               reply_content=None, category=None, external_content=None,
                               title=None):
    """
    Raises `ServiceError` if not valid.

    Returns a tuple containing model instances of the following (in this order):
        replied_comment
        parent_comment
        reply_content
        external_content
        category
    """
    from apps.monster.models import MONSTER_GROUP

    noun = 'thread'
    attribute = 'title'

    original_parent_comment = parent_comment

    if category == MONSTER_GROUP:
        noun = 'monster'
        attribute = 'name'

    if title:
        if len(title) > knobs.POST_TITLE_MAX_LENGTH:
            raise ServiceError("{0} is too long.".format(attribute))
    elif parent_comment is None:
        raise ServiceError("Your {0} needs a {1}.".format(noun, attribute))
    else:
        title = ''

    # Was this a reply, or a new comment?
    if replied_comment is not None:
        # This is a new comment.
        replied_comment = models.Comment.all_objects.get(id=replied_comment)

    try:
        parent_comment = models.Comment.all_objects.get(id=parent_comment)
    except models.Comment.DoesNotExist:
        parent_comment = None

    if parent_comment is not None and original_parent_comment is None:
        parent_comment = None

    reply_content = models.Content.all_objects.get_or_none(pk=reply_content)

    if parent_comment:
        if parent_comment.visibility == models.Visibility.DISABLED and not user.is_staff:
            raise ServiceError('Sorry, this thread has been disabled.')
        # Replies must be of the same category as the parent.
        _category = parent_comment.category
    else:
        _category = None
        if category is not None:
            _category = models.Category.objects.get_or_none(name=category)
            if not _category:
                raise ServiceError("Group not found.")

    # Text-only OPs are only valid if the group explicitly allows them.
    if not reply_content and not parent_comment:
        raise ServiceError('Text-only OPs are not enabled for this group.')

    # Was there external content with this post? ie, YouTube data?
    # Fetch the dict from the request.
    # An external content dict should look like this:
    # {type: "yt",
    # start_time: 10, end_time: 20, url}
    # Note that we're using the abbreviated form of ExternalContent.CONTENT_CHOICES.
    # @TODO: It would be nicer to use the easier to understand long form, ie, 'youtube' instead of 'yt'
    if external_content is not None:
        external_content = models.ExternalContent.from_dict(external_content)

    return (replied_comment, parent_comment, reply_content, external_content, _category, title,)

