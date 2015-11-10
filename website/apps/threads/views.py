from django.http import HttpResponseRedirect, HttpResponseServerError, Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

from apps.features import feature_flags as features
from canvas import experiments, fact
from canvas.browse import TileDetails
from canvas.cache_patterns import CachedCall
from canvas.knobs import VIEW_THREAD_PAGE_NUM_TOP
from canvas.metrics import Metrics
from canvas.models import Comment
from canvas.shortcuts import r2r_jinja, r2r
from canvas.templatetags.helpers import TemplateComment
from canvas.templatetags.jinja_tags import ugc_text
from canvas.view_helpers import redirect_trailing, CommentViewData
from django.conf import settings

@redirect_trailing
def logged_out_thread_view(request, short_id, page=None, gotoreply=None):
    view_data = CommentViewData(request, short_id, page=page, gotoreply=gotoreply)

    ctx = view_data.thread_context()

    if request.is_mobile:
        return r2r_jinja('mobile/thread.html', ctx)

    fact.record('flow_start', request, {})

    return render_to_response('threads/new_thread.django.html', ctx, context_instance=RequestContext(request))

@redirect_trailing
def thread(request, short_id, page=None, gotoreply=None, sort_by_top=False,
           template_name='comment/new_base_thread.django.html'):
    from apps.monster.models import MONSTER_GROUP

    if not request.user.is_authenticated() and template_name == 'comment/new_base_thread.django.html' and not features.thread_new(request):
        return logged_out_thread_view(request, short_id, page=page, gotoreply=gotoreply)

    view_data = CommentViewData(request, short_id, page=page, gotoreply=gotoreply)

    if '/p/' + short_id == request.user.kv.post_pending_signup_url.get():
        request.user.kv.post_pending_signup_url.delete()

    ctx = view_data.thread_context()

    ctx['request'] = request

    # monstermash posts redirect to monstermash app
    if ctx['op_comment'].category == MONSTER_GROUP and not ctx['viewer_is_staff']:
        return HttpResponseRedirect('/monster/{0}'.format(ctx['op_comment'].short_id()))

    # all hidden group posts are invisible to normal users
    if ctx['op_comment'].category in settings.HIDDEN_GROUPS and not ctx['viewer_is_staff']:
        return Http404()

    # If we hit the size threshold, record metric that the user is viewing a large thread
    if ctx['large_thread_view']:
        Metrics.large_thread_view.record(request)

    ctx['remix_invite_share_view'] = 'rmi' in request.GET
    if ctx['remix_invite_share_view']:
        ctx['fb_metadata']['title'] = "Come Remix With Me!"
        if ctx['op_comment'].title:
            ctx['fb_metadata']['description'] = """I just started a thread on Canvas, "{0}". Click the link to add your remix to the thread!""".format(op_comment.title)
        else:
            ctx['fb_metadata']['description'] = "I just started a thread on Canvas. Click the link to add your remix to the thread!"

    # Inviting experiment
    ctx['is_in_invite_remixers_v2'] = False

    ctx.update({
        'request': request,
        'sort_by_top': sort_by_top,
    })

    if request.is_mobile:
        return r2r_jinja("mobile/thread.html", ctx)

    if features.thread_new(request):
        ctx['has_top_remixes'] = bool(len(ctx['top_remixes']))
        if sort_by_top:
            ctx['replies'] = ctx['top_remixes']
            ctx['has_top_remixes'] = True

        return r2r_jinja('threads_new/thread.html', ctx, request)

    return r2r(template_name, ctx)

