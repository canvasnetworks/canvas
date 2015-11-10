from django.conf import settings

from canvas.metrics import Metrics


class Funnel(object):
    def __init__(self, name, steps):
        self.name = name
        self.steps = steps

    def __repr__(self):
        return self.name

    def step_names(self):
        return [step.name for step in self.steps]

class Funnels(object):
    if settings.PROJECT == 'canvas':
        names = (
            ('signup_to_activation', [
                Metrics.signup,
                Metrics.sticker,
                Metrics.post,
            ]),
            ('onboarding', [
                Metrics.signup_form_view,
                Metrics.signup,
                Metrics.onboarding_funnel_start,
                Metrics.onboarding_groups,
                Metrics.onboarding_invites,
                Metrics.invite_facebook_friends,
                Metrics.onboarding_welcome_tutorial_view,
                Metrics.onboarding_finish,
            ]),
        )
    elif settings.PROJECT == 'drawquest':
        names = ()

def _setup_funnels():
    by_name = {}
    for name, steps in Funnels.names:
        funnel = Funnel(name, steps)
        setattr(Funnels, name, funnel)
        by_name[name] = funnel
    Funnels.by_name = by_name
_setup_funnels()

