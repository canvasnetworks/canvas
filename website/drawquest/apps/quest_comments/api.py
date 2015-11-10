from collections import defaultdict
from datetime import timedelta as td

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from canvas.cache_patterns import CachedCall
from canvas.exceptions import ServiceError
from canvas.forms import validate_and_clean_comment
from canvas.redis_models import RateLimit
import canvas.signals
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest import knobs, economy
from drawquest.api_cache import cached_api
from drawquest.api_decorators import api_decorator
from drawquest.apps.comment_freeze.models import filter_frozen_comments
from drawquest.apps.drawquest_auth.models import User, AnonymousUser, associate_facebook_account
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.models import QuestPreview, ScheduledQuest, archived_quests, Quest
from drawquest.apps.timeline.models import complete_quest
from drawquest.pagination import Paginator

urlpatterns = []
api = api_decorator(urlpatterns)

@api('post')
@require_user
def post_quest_comment(request, quest_id, content_id, fact_metadata={},
                       facebook_share=False, facebook_access_token=None):
    # Rate-limit?
    if not request.user.is_staff:
        prefix = 'user:{}:post_limit:'.format(request.user.id)
        if not RateLimit(prefix+'h', 60, 60*60).allowed() or not RateLimit(prefix+'d', 100, 8*60*60).allowed():
            raise ServiceError("Attempting to post drawings too quickly.")

    _, parent_comment, content, _, _, _ = validate_and_clean_comment(
        request.user,
        parent_comment=quest_id,
        reply_content=content_id,
    )

    if facebook_share:
        if not facebook_access_token:
            raise ServiceError("Can't share to your timeline if you haven't signed into Facebook yet.")

        associate_facebook_account(request.user, facebook_access_token)

    comment = QuestComment.create_and_post(request, request.user, content, parent_comment,
                                           fact_metadata=fact_metadata)

    if facebook_share:
        complete_quest(request.user, comment, facebook_access_token, request=request)

    return {
        'comment': comment.details(),
        'balance': economy.balance(request.user),
    }

@api('user_comments')
@cached_api(timeout=td(days=2), namespace='comments', key=[
    'user_comments',
    'v4',
    lambda _, username, **kwargs: [username] + kwargs.items(),
])
def user_comments(request, username, since_id=None, before_id=None):
    user = get_object_or_404(User, username=username)

    comments = QuestComment.by_author(user)

    paginator = Paginator(comments, knobs.COMMENTS_PER_PAGE, since_id=since_id, before_id=before_id)
    comments = paginator.items

    comments = CachedCall.multicall([cmt.details for cmt in comments])

    comments = filter_frozen_comments(comments)

    return {'comments': comments, 'pagination': paginator}
canvas.signals.visibility_changed.connect(
    lambda sender, instance, **kwargs: user_comments.delete_cache(None, instance.author.username),
    dispatch_uid='user_comments_visibility_changed', weak=False
)

@api('rewards_for_posting')
def rewards_for_posting(request, quest_id, facebook=False, tumblr=False):
    rewards = defaultdict(int)

    def reward(name):
        rewards[name] += knobs.REWARDS[name]

    if not request.user.is_authenticated() or QuestComment.posting_in_first_quest(request.user):
        reward('first_quest')
        return {'rewards': rewards}

    quest = get_object_or_404(Quest, id=quest_id)

    if QuestComment.posting_would_complete_quest_of_the_day(request.user, quest):
        reward('quest_of_the_day')
    elif QuestComment.posting_would_complete_archived_quest(request.user, quest):
        reward('archived_quest')

    if QuestComment.posting_in_first_quest(request.user):
        reward('first_quest')

    if facebook:
        reward('personal_share')

    if tumblr:
        reward('personal_share')

    streak = QuestComment.posting_would_reward_streak(request.user, quest)
    if streak:
        reward('streak_{}'.format(streak))

    return {'rewards': rewards}

