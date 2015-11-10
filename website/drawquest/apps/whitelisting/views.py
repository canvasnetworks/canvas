from canvas.redis_models import redis
from canvas.shortcuts import r2r_jinja
from drawquest.apps.quest_comments.models import QuestComment
from drawquest import knobs


def whitelisting(request):
    freeze_id = redis.get('dq:comment_freeze_id')
    comments = []

    if freeze_id is not None:
        comments = QuestComment.unjudged().filter(
            id__gte=freeze_id,
        ).order_by('id')[:knobs.WHITELIST_COMMENTS_PER_PAGE]

    ctx = {
        'comments': comments,
        'enabled': freeze_id is not None,
    }

    return r2r_jinja('whitelisting/whitelisting.html', ctx, request)

def whitelisting_paginated(request, after_id=None):
    freeze_id = redis.get('dq:comment_freeze_id')
    comments = []

    if after_id >= freeze_id:
        comments = QuestComment.unjudged().filter(
            id__gt=after_id,
        ).order_by('id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],

    return r2r_jinja('whitelisting/whitelist_items.html', {'comments': comments}, request)

def flag_queue(request):
    ctx = {
        'comments': QuestComment.unjudged_flagged().order_by('id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
    }
    return r2r_jinja('whitelisting/flagged.html', ctx, request)

def flag_queue_paginated(request, after_id=None):
    ctx = {
        'comments': QuestComment.unjudged_flagged().filter(
            id__gt=after_id,
        ).order_by('id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
    }
    return r2r_jinja('whitelisting/whitelist_items.html', ctx, request)

def new(request):
    ctx = {
        'comments': QuestComment.unjudged().order_by('-id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
    }
    return r2r_jinja('whitelisting/new.html', ctx, request)

def new_paginated(request, after_id=None):
    ctx = {
        'comments': QuestComment.unjudged().filter(
            id__gt=after_id,
        ).order_by('-id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
    }
    return r2r_jinja('whitelisting/whitelist_items.html', ctx, request)

def all(request):
    ctx = {
        'comments': QuestComment.all_objects.all().order_by('-id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
    }
    return r2r_jinja('whitelisting/new.html', ctx, request)

def all_paginated(request, after_id=None):
    ctx = {
        'comments': QuestComment.all_objects.filter(
            id__gt=after_id,
        ).order_by('-id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
    }
    return r2r_jinja('whitelisting/whitelist_items.html', ctx, request)

