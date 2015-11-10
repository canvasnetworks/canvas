from datetime import timedelta as td

from django.conf import settings
from django.conf.urls.defaults import url, patterns, include
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404

from canvas.exceptions import ServiceError, ValidationError
from canvas.models import Content
from canvas.upload import api_upload, chunk_uploads
from canvas.view_guards import require_staff, require_POST, require_user
from drawquest import knobs, models, economy, api_forms
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.details_models import PrivateUserDetails
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.palettes.models import user_palettes, palettes_hash
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.models import current_quest_details, completed_quest_ids
from drawquest.api_cache import cached_api
from drawquest import signals
from website.apps.share_tracking.models import ShareTrackingUrl

urls = patterns('',
    url(r'^quest_comments/flag', 'apps.comments.api.flag_comment'),
)

urls += patterns('drawquest.api',
    url(r'^activity/', include('apps.activity.api')),
    url(r'^auth/', include('drawquest.apps.drawquest_auth.api')),
    url(r'^chunk/', include(chunk_uploads)),
    url(r'^following/', include('drawquest.apps.following.api')),
    url(r'^iap/', include('drawquest.apps.iap.api')),
    url(r'^palettes/', include('drawquest.apps.palettes.api')),
    url(r'^playback/', include('drawquest.apps.playback.api')),
    url(r'^push_notifications/', include('drawquest.apps.push_notifications.api')),
    url(r'^quest_comments/', include('drawquest.apps.quest_comments.api')),
    url(r'^quests/', include('drawquest.apps.quests.api')),
    url(r'^stars/', include('drawquest.apps.stars.api')),
    url(r'^submit_quest/', include('drawquest.apps.submit_quest.api')),
    url(r'^timeline/', include('drawquest.apps.timeline.api')),
    url(r'^tumblr/', include('drawquest.apps.tumblr.api')),
    url(r'^upload$', api_upload),
    url(r'^whitelisting/', include('drawquest.apps.whitelisting.api')),

    # Only used for the admin.
    url(r'^comment/', include('apps.comments.api')),

    # Disabled for now for perf.
    #url(r'^', include('apps.analytics.api')),
)

api = api_decorator(urls)

@api('metric/record')
def metric_record(request, name, info={}):
    """ Currently a no-op. """

@api('economy/rewards')
@cached_api(key=['reward_amounts', sum(knobs.REWARDS.values())])
def rewards(request):
    return {'rewards': knobs.REWARDS}

@api('user/profile')
def user_profile(request, username):
    return models.user_profile_for_viewer(username, viewer=request.user)

@api('user/change_profile')
@require_user
def change_profile(request, old_password=None, new_password=None, new_email=None, bio=None):
    if bio is not None:
        request.user.userinfo.bio_text = bio
        request.user.userinfo.save()
        request.user.details.force()

    if new_email is not None:
        if not User.validate_email(new_email):
            raise ValidationError({'new_email': "Please enter a valid email address."})

        if request.user.email != new_email:
            if not User.email_is_unused(new_email):
                raise ValidationError({'new_email': "Sorry! That email address is already being used for an account."})

            request.user.email = new_email
            request.user.save()
            request.user.details.force()

    if old_password is not None and new_password is not None:
        if not User.validate_password(new_password):
            raise ValidationError({
                'new_password': "Sorry, your new password is too short. "
                                "Please use {} or more characters.".format(User.MINIMUM_PASSWORD_LENGTH),
            })

        form = PasswordChangeForm(user=request.user, data={
            'old_password': old_password,
            'new_password1': new_password,
            'new_password2': new_password,
        })

        api_forms.validate(form)
        form.save()
        request.user.details.force()

@api('user/change_avatar')
@require_user
def change_avatar(request, content_id):
    user_info = request.user.userinfo
    user_info.avatar = get_object_or_404(Content, id=content_id)
    user_info.save()

    user = User.objects.get(id=request.user.id)
    user.details.force()

@api('create_email_invite_url')
def create_email_invite_url(request):
    #TODO iTunes URL
    url = 'http://example.com/download'

    if request.user.is_authenticated():
        sharer = request.user
        share = ShareTrackingUrl.create(sharer, url, 'email')
        url = share.url_for_channel()

    return {'invite_url': url}

@api('realtime/sync')
def realtime_sync(request):
    return {'channels': models.realtime_sync(request.user)}

@api('share/create_for_channel')
def share_create_for_channel(request, comment_id, channel):
    comment = get_object_or_404(QuestComment, id=comment_id)
    url = comment.get_share_page_url_with_tracking(request.user, channel, request=request)

    if channel == 'facebook':
        url = 'http://example.com' + url

    return {
        'share_url': url,
    }

@api('economy/balance')
@require_user
def coin_balance(request):
    return {'balance': economy.balance(request.user)}

@api('heavy_state_sync')
def heavy_state_sync(request):
    ret = {
        'realtime_sync': models.realtime_sync(request.user),
        'user_palettes': user_palettes(request.user),
        'current_quest': current_quest_details(),
        'onboarding_quest_id': knobs.ONBOARDING_QUEST_ID,
    }

    if request.user.is_authenticated():
        ret.update({
            'user_email': request.user.email,
            'user_profile': models.user_profile(request.user.username),
            'balance': economy.balance(request.user),
            'completed_quest_ids': completed_quest_ids(request.user),
        })

    return ret

