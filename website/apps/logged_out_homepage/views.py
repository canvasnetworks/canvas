from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from apps.logged_out_homepage.models import (SpotlightedThread, suggested_threads,
                                             spotlighted_threads, cached_homepage)
from canvas.models import Comment
from canvas.shortcuts import r2r_jinja
from canvas.view_guards import require_staff
from services import Services

def homepage(request):
    if 'force_refresh' in request.GET:
        cached_homepage.force()
    return r2r_jinja('logged_out_homepage/logged_out_homepage.html', {}, request)

@require_staff
def homepage_admin(request):
    if request.method == 'POST':
        ordinals = {}
        for key, ordinal in request.POST.iteritems():
            if 'sort_order' not in key:
                continue
            _, id_ = key.split('-')
            op = get_object_or_404(Comment, id=id_)

            if ordinal is None or not str(ordinal).strip():
                try:
                    spotlight = SpotlightedThread.objects.get(comment=op)
                    spotlight.delete()
                except SpotlightedThread.DoesNotExist:
                    pass
                continue

            try:
                ordinal = int(ordinal)
            except ValueError:
                ordinal = 0

            spotlight = SpotlightedThread.get_or_create(op)

            if not spotlight.curator:
                spotlight.curator = request.user
                spotlight.timestamp = Services.time.time()

            spotlight.sort = ordinal
            spotlight.save()
        cached_homepage.force()
        page_updated = True
    else:
        page_updated = False

    ctx = {
        'spotlighted_threads': spotlighted_threads(),
        'suggested_threads': suggested_threads(),
        'page_updated': page_updated,
    }
    return r2r_jinja('logged_out_homepage/admin.html', ctx, request)

