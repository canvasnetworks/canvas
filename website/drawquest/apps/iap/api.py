from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from drawquest import economy
from drawquest.api_decorators import api_decorator
from drawquest.apps.iap.models import IapReceipt, COIN_PRODUCTS, deliver_product
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.util import Now
from canvas.view_guards import require_staff, require_user

urlpatterns = []
api = api_decorator(urlpatterns)

@api('coin_products')
@require_user
def iap_coin_products(request):
    return {'coin_products': COIN_PRODUCTS}


@api('process_receipt')
@require_user
def iap_process_receipt(request, receipt_data):
    """
    Verifies the receipt, and processes the purchase.
    """
    #TODO To be safer against botting, the receipt_data uniqueness constraint
    # needs to be done atomically.
    if IapReceipt.objects.filter(receipt_data=receipt_data).exists():
        # Already processed this receipt, fail silently.
        return {'balance': economy.balance(request.user)}

    receipt = IapReceipt.objects.create(
        purchaser=request.user,
        receipt_data=receipt_data,
        timestamp=Now(),
    )

    receipt.verify()

    if receipt.verified:
        deliver_product(request.user, receipt.product_id)

    return {'balance': economy.balance(request.user)}

