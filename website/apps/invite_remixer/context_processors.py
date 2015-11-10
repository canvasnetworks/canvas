from apps.invite_remixer.urls import absolute_invite_url


def invite_remixer_context(request):
    context = {}

    if request.user.is_authenticated():
        context.update({
            'homepage_invite_url': absolute_invite_url(request.user),
        })

    return context

