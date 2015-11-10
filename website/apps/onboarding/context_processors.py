from apps.onboarding import flow


def onboarding_context(request):
    ctx = {}
    onboarding = ctx['onboarding'] = flow.is_onboarding(request)

    if onboarding:
        ctx.update({
            'onboarding_next': flow.get_next(request),
            'onboarding_current_step': flow.current_step(request),
            'onboarding_total_steps': len(flow.ONBOARDING_FLOW),
        })

    return ctx

