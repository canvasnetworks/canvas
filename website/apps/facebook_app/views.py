from django.views.decorators.csrf import csrf_exempt

from canvas.exceptions import NotLoggedIntoFacebookError
from canvas.shortcuts import r2r
from canvas.util import get_fb_api

@csrf_exempt
def facebook_iframe(request):
    fb_message_id = request.GET.get('request_ids')

    try:
        fb_user, fb = get_fb_api(request)
        app_requests = fb.request('{}/apprequests'.format(fb_user['id']))

        redirect_url = None
        for app_request in app_requests['data']:
            if not redirect_url:
                redirect_url = app_request.get('data')
            fb.delete_object(app_request['id'])

        if not redirect_url:
            redirect_url = '/'
    except NotLoggedIntoFacebookError:
        redirect_url = '/'

    context = {
        'request': request,
        'fb_message_id': fb_message_id,
        'redirect_url': redirect_url,
    }
    resp = r2r('facebook_app/facebook_iframe.django.html', context)

    resp.set_cookie('fb_message_id', fb_message_id)

    return resp

