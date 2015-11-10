from django.shortcuts import get_object_or_404

from apps.canvas_auth.models import User
from canvas.api_decorators import api_decorator
from canvas.cache_patterns import CachedCall
from canvas.details_models import CommentDetails
from canvas.metrics import Metrics
from canvas.models import Comment, Category
from canvas.view_guards import require_user
from django.conf import settings
from urbanairship import Airship

urlpatterns = []
api = api_decorator(urlpatterns)


@api('register_token')
@require_user
def register_token(request, device_token):
    from apps.monster.models import MobileUser

    MobileUser.register(request.user, device_token)
    ret = {
        'username': request.user.username,
        'device_token': device_token,
    }
    return ret

@api('invite_user')
@require_user
def invite_user(request, username, payload):
    user = get_object_or_404(User, username=username)
    ua = Airship(settings.URBANAIRSHIP_APP_KEY, settings.URBANAIRSHIP_APP_MASTER_SECRET)
    ua.push(payload, aliases=[username])
    return {}

@api('all_completed_mobile_monsters')
def all_completed_mobile_monsters(request):
    """ Returns all completed mobile monsters for ones the logged-in user began. """
    from apps.monster.models import MONSTER_MOBILE_GROUP

    comment_details = []
    cids = Comment.objects.filter(category__name=MONSTER_MOBILE_GROUP,
                                  parent_comment__author=request.user).values_list('id', flat=True)
    if cids:
        comment_details = CommentDetails.from_ids(cids)
    return {'bottoms': comment_details}

