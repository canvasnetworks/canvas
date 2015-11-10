from django.shortcuts import get_object_or_404

from canvas.exceptions import ServiceError, ValidationError
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest import economy
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.models import User, AnonymousUser
from drawquest.apps.palettes import models

urlpatterns = []
api = api_decorator(urlpatterns)

@api('purchasable_palettes')
def purchasable_palettes(request):
    return {'palettes': models.purchasable_palettes}

@api('user_palettes')
def user_palettes(request):
    return {'palettes': models.user_palettes(request.user)}

@api('purchase_palette')
@require_user
def purchase_palette(request, username, palette_name):
    try:
        palette = models.get_palette_by_name(palette_name)
    except KeyError:
        raise ValidationError("Invalid palette name.")

    try:
        economy.purchase_palette(request.user, palette)
    except economy.InvalidPurchase as e:
        raise ServiceError(e.message)

    return {'palettes': request.user.redis.palettes}

