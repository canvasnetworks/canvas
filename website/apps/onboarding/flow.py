ONBOARDING_FLOW = ['/onboarding/follow', '/invite', '/onboarding/welcome']
ONBOARDING_START = ONBOARDING_FLOW[0] + '?onboarding'
ONBOARDING_FINISH = '/'


def is_onboarding(request):
    return (request.user.is_authenticated()
            and 'onboarding' in request.GET
            and request.path in ONBOARDING_FLOW)

def get_next(request):
    try:
        return ONBOARDING_FLOW[ONBOARDING_FLOW.index(request.path) + 1] + '?onboarding'
    except IndexError:
        return '/onboarding/finish'

def current_step(request):
    return ONBOARDING_FLOW.index(request.path) + 1

