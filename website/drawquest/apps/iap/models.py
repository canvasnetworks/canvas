import urllib2

from django.core.exceptions import ValidationError
from django.db.models import *
from django.conf import settings

from canvas import json
from canvas.models import BaseCanvasModel
from canvas.util import UnixTimestampField, Now
from drawquest.apps.drawquest_auth.models import User
from drawquest import economy


COIN_PRODUCTS = dict(('as.canv.drawquest.products.coins.' + key, val) for key,val in {
    '50': {
        'amount': 50,
    },
    '150': {
        'amount': 150,
        #'description': "Save 15%!",
    },
    '400': {
        'amount': 400,
        #'description': "Save 33%!",
    },
}.items())

def deliver_product(user, product_id):
    product = COIN_PRODUCTS[product_id]
    economy.credit(user, product['amount'])


class IapReceipt(BaseCanvasModel):
    """
    See: http://developer.apple.com/library/ios/#documentation/NetworkingInternet/Conceptual/StoreKitGuide/VerifyingStoreReceipts/VerifyingStoreReceipts.html
    """
    purchaser = ForeignKey(User, db_index=True, related_name='iap_receipts')
    receipt_data = TextField()
    timestamp = UnixTimestampField()

    product_id = CharField(blank=True, max_length=256)
    version_external_identifier = CharField(blank=True, max_length=256)
    bvrs = CharField(blank=True, max_length=256)
    bid = CharField(blank=True, max_length=256)

    verified = BooleanField(default=False)

    def verify(self):
        try:
            cleaned_data = verify_receipt(self.receipt_data)
        except ValidationError:
            self.verified = False
            self.save()
            raise

        for prop in ['bid', 'bvrs', 'product_id']:
            setattr(self, prop, cleaned_data[prop])

        # Missing in the sandbox.
        if 'version_external_identifier' in cleaned_data:
            self.version_external_identifier = cleaned_data['version_external_identifier']

        self.verified = True
        self.save()


def verify_receipt(receipt_data):
    """
    Returns the receipt data, or raises a ValidationError.
    """
    #data = json.dumps({'receipt-data': '{' + receipt_data + '}'})
    data = '{{\n "receipt-data" : "{}" \n}}'.format(receipt_data)

    def verify(url):
        req = urllib2.Request(url, data)
        resp = urllib2.urlopen(req)
        return json.loads(resp.read())

    cleaned_data = verify(settings.IAP_VERIFICATION_URL)

    # See: http://developer.apple.com/library/ios/#technotes/tn2259/_index.html
    if cleaned_data['status'] == 21007:
        cleaned_data = verify(settings.IAP_VERIFICATION_SANDBOX_URL)

    if cleaned_data['status'] != 0:
        raise ValidationError("Invalid receipt.")

    return cleaned_data['receipt']

