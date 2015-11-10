from django.shortcuts import get_object_or_404
from django.conf import settings

from canvas.forms import validate_and_clean_comment
from canvas.models import Comment
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.models import User

urlpatterns = []
api = api_decorator(urlpatterns)

@api('post_quest_idea')
def post_quest_idea(request, title, content, name, email):
    user = User.objects.get(username=settings.QUEST_IDEAS_USERNAME)

    text = "Name: {}\n\nEmail: {}".format(name, email)

    replied_comment, parent_comment, reply_content, external_content, category, title = validate_and_clean_comment(
        user,
        reply_text=text,
        reply_content=content,
        title=title,
    )

    comment = Comment.create_and_post(
        request,
        user,
        False,
        category,
        reply_content,
        parent_comment=parent_comment,
        reply_text=text,
        replied_comment=replied_comment,
        external_content=external_content,
        fact_metadata={},
        title=title,
    )

    return {'comment': comment.details()}

