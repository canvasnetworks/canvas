from django.http import HttpResponse

from canvas import json

def inactive_user_http_response():
    return HttpResponse(json.client_dumps({
        'reason': "Your account has been suspended. If you have any questions about this, please email accounts@example.com",
        'error_type': 'DeactivatedUserError',
        'success': False,
    }), mimetype='application/json', status=403)

