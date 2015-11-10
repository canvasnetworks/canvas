from datetime import timedelta as td

from django.db.models.signals import post_save
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404

import canvas.signals
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff
from drawquest import knobs
from drawquest.api_cache import cached_api
from drawquest.api_decorators import api_decorator
from drawquest.apps.quests import signals
from drawquest.apps.quests.models import QuestPreview, ScheduledQuest, archived_quests, Quest, current_quest_details
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.comment_freeze.models import filter_frozen_comments
from drawquest.pagination import Paginator


urlpatterns = []
api = api_decorator(urlpatterns)

@api('render_quest_preview')
@require_staff
def render_quest_preview(request, short_id):
    quest_preview = QuestPreview.get_by_short_id(short_id)    

    ctx = {
        'quest_preview': quest_preview,
        'admin_view': True,
        'show_curation_info': False,
    }

    return HttpResponse(render_jinja_to_string('quests/quest_preview.html', ctx))

@api('archive')
@cached_api(timeout=td(days=1), namespace='quests', key=['quest_archive', 'v5'])
def quest_archive(request):
    return {'quests': archived_quests()}

@api('comments')
@cached_api(timeout=td(hours=8), namespace='comments', key=[
    'quest_comments',
    'v2',
    lambda _, quest_id, **kwargs: [quest_id] +  kwargs.values(),
])
def quest_comments(request, quest_id, force_comment_id=None, since_id=None, before_id=None):
    quest = get_object_or_404(Quest, id=quest_id)
    comments = quest.comments_details()

    forced_comment = None
    if force_comment_id:
        for comment in comments:
            if str(comment.id) == str(force_comment_id):
                forced_comment = comment
                break

    paginator = Paginator(comments, knobs.COMMENTS_PER_PAGE, since_id=since_id, before_id=before_id)
    comments = paginator.items

    comments = filter_frozen_comments(comments)

    if forced_comment and str(forced_comment.id) not in [str(comment.id) for comment in comments]:
        comments.append(forced_comment)

    return {'comments': comments, 'pagination': paginator}

# Cache invalidators for quest_comments.
post_save.connect(
    lambda sender, instance, **kwargs: quest_comments.delete_cache(None, instance.parent_comment_id),
    sender=QuestComment, dispatch_uid='post_save_for_quest_comments_api', weak=False
)
canvas.signals.visibility_changed.connect(
    lambda sender, instance, **kwargs: quest_comments.delete_cache(None, instance.parent_comment_id),
    dispatch_uid='quest_comments_visibility_changed', weak=False
)

@api('current')
@cached_api(timeout=td(hours=2), namespace='quests', key='current_quest')
def current_quest(request):
    return {'quest': current_quest_details()}

@api('set_current_quest')
def set_current_quest(request, scheduled_quest_id):
    scheduled_quest = get_object_or_404(ScheduledQuest, id=scheduled_quest_id)
    scheduled_quest.set_as_current_quest()

@api('onboarding')
@cached_api(timeout=td(days=1), key=[
    'onboarding_quest',
    'v2',
    knobs.ONBOARDING_QUEST_ID,
])
def onboarding_quest(request):
    return {'quest': Quest.objects.get(id=knobs.ONBOARDING_QUEST_ID).details()}

