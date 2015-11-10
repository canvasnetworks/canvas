from django.http import HttpResponseRedirect

from apps.onboarding.flow import ONBOARDING_START, ONBOARDING_FINISH
from canvas.knobs import SUGGESTED_USERS, SUGGESTED_TOPICS, SUGGESTED_TOPIC_PREVIEWS

from canvas.cache_patterns import CachedCall
from canvas.models import Metrics, Category, Comment, Content, Tag, User
from canvas.shortcuts import r2r, r2r_jinja
from random import sample

from apps.tags.models import get_tracked_tags


def start(request):
    Metrics.onboarding_funnel_start.record(request)
    return HttpResponseRedirect(ONBOARDING_START)

def welcome_tutorial(request):
    ctx = {
        'request': request,
    }
    Metrics.onboarding_welcome_tutorial_view.record(request)
    return r2r_jinja('welcome.html', ctx, request)

def finish(request):
    Metrics.onboarding_finish.record(request)

    post_pending_signup_url = request.user.kv.post_pending_signup_url.get()
    if post_pending_signup_url:
        return HttpResponseRedirect(post_pending_signup_url)

    return HttpResponseRedirect(ONBOARDING_FINISH)

def suggested_users(request):
    user_list = []
    users = sample(SUGGESTED_USERS, 5)
    users = list(User.objects.filter(username__in=users, is_active=True))
    for user in users:
        if user.userinfo.profile_image is not None:
            avatar_comment = Comment.details_by_id(user.userinfo.profile_image.id)()
        else:
            avatar_comment = None

        is_following = False
        try:
            is_following = request.user.is_following(user)
        except AttributeError:
            pass

        user_list.append({
            'user'              : user,
            'avatar_comment'    : avatar_comment,
            'is_following'      : is_following,
            'is_self'           : request.user == user,
        })

    topics = sample(SUGGESTED_TOPICS, 5)
    topics = [{'name': topic} for topic in topics]
    topic_previews = Content.all_objects.filter(id__in=SUGGESTED_TOPIC_PREVIEWS.values())

    topic_previews = CachedCall.multicall([preview.details for preview in topic_previews])

    preview_mapping = dict([(content['id'], content) for content in topic_previews])

    try:
        followed_tags = request.user.redis.followed_tags
    except AttributeError:
        followed_tags = []

    for topic in topics:
        topic['preview'] = preview_mapping.get(SUGGESTED_TOPIC_PREVIEWS[topic['name']])
        topic['is_following'] = topic['name'] in followed_tags

    ctx = {
        'request': request,
        'users': user_list,
        'topics': topics,
    }
    return r2r_jinja('onboarding/suggested_users.html', ctx, request)

