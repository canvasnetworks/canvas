import itertools

from collections import defaultdict

from canvas.view_guards import require_staff
from canvas.shortcuts import r2r, r2r_jinja

@require_staff
def staff_api_console(request):
    """ Shows an html wrapper around our APIs that staff can use. """
    from canvas.js_api import get_api_calls
    import drawquest.apps.stars.api
    import drawquest.apps.stars.api
    import drawquest.apps.drawquest_auth.api
    import drawquest.apps.iap.api
    import drawquest.apps.quests.api
    import drawquest.apps.quest_comments.api
    import drawquest.apps.playback.api
    import drawquest.apps.palettes.api
    import drawquest.apps.push_notifications.api
    import drawquest.apps.following.api
    import drawquest.apps.timeline.api
    import drawquest.apps.tumblr.api
    from drawquest.api_decorators import api_functions

    api_dict = defaultdict(lambda: [])
    # Group apis by their prefix.
    api_key = lambda func: func.url.strip("/").split("/")[1]
    functions = get_api_calls(api_functions=api_functions, ignore_unfound=True)
    for key, api_calls in itertools.groupby(functions, api_key):
        api_dict[key].extend(api_calls)

    apis = []
    for key, api_calls in api_dict.items():
        apis.append(dict(name=key, commands=api_calls))
    # Order apis alphabetically
    apis = sorted(apis, key=lambda entry: entry.get("name"))
    # Inspect it.
    # @todo: Add a "staff" api for staff only calls.
    #apis = [dict(path="/api/", name="Canvas API", commands=functions)]
    # @gotcha: Be sure to use r2r, else {% csrf_token %} won't work.
    return r2r("api_wrapper.django.html", dict(apis=apis, request=request))

