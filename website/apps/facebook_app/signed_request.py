# http://sunilarora.org/parsing-signedrequest-parameter-in-python-bas

import base64
import hashlib
import hmac
import simplejson as json

from canvas.metrics import Metrics
from canvas.models import UserInfo
from django.conf import settings

def base64_url_decode(inp):
    padding_factor = (4 - len(inp) % 4) % 4
    inp += '=' * padding_factor
    return base64.b64decode(unicode(inp).translate(dict(zip(map(ord, u'-_'), u'+/'))))

def parse_signed_request(request, signed_request):
    l = signed_request.split('.', 2)
    encoded_sig = l[0]
    payload = l[1]

    sig = base64_url_decode(encoded_sig)
    data = json.loads(base64_url_decode(payload))

    if data.get('algorithm').upper() != 'HMAC-SHA256':
        Metrics.facebook_signed_request_error.record(request)
        return

    expected_sig = hmac.new(settings.FACEBOOK_APP_SECRET, msg=payload, digestmod=hashlib.sha256).digest()

    if sig != expected_sig:
        Metrics.facebook_signed_request_error.record(request)
        return

    return data

def authenticate(request, facebook_id, signed_request):
    try:
        data = parse_signed_request(request, signed_request)
        if data['user_id'] == facebook_id:
            return UserInfo.objects.get(facebook_id=facebook_id).user
        else:
            return None

    except UserInfo.DoesNotExist:
        return None

