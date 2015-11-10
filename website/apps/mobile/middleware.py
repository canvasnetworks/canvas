import re


MOBILE_AGENT_PROG = re.compile('(alcatel|amoi|android|avantgo|blackberry|benq|cell|cricket|docomo|elaine|htc|iemobile|iphone|ipad|ipaq|ipod|j2me|java|midp|mini|mmp|mobi|motorola|nec-|nokia|palm|panasonic|philips|phone|sagem|sharp|sie-|smartphone|sony|symbian|t-mobile|telus|up\.browser|up\.link|vodafone|wap|webos|wireless|xda|xoom|zte|playstation)', re.IGNORECASE)
IE_VERSION_PROG = re.compile("MSIE ([0-9]{1,}[\.0-9]{0,})", re.IGNORECASE)

def detect_mobile_user_agent(user_agent):
    return bool(MOBILE_AGENT_PROG.search(user_agent))

def detect_ie8_or_lesser(user_agent):
    ie_version_match = IE_VERSION_PROG.search(user_agent)
    if not ie_version_match:
        return False

    groups = ie_version_match.groups()
    if not groups:
        return False

    try:
        ie_version = float(groups[0])
    except ValueError:
        return False

    return ie_version < 9


class MobileDetectionMiddleware(object):
    def process_request(self, request):
        user_agent = request.META.get("HTTP_USER_AGENT", '')
        get_opt_out = request.GET.get('m') == 'no'
        cookie_opt_out = request.COOKIES.get('m') == 'no'

        gets_mobile = detect_mobile_user_agent(user_agent) or detect_ie8_or_lesser(user_agent)
        opt_out = get_opt_out or cookie_opt_out
        request.is_mobile = gets_mobile and not opt_out

    def process_response(self, request, response):
        if request.GET.get('permanent_no_mobile') == 'yes':
            response.set_cookie('m', 'no', max_age = 365 * 24 * 60 * 60)
        return response
