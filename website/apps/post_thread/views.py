import urllib

from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from canvas.browse import TileDetails
from canvas.models import Content, Comment
from canvas.shortcuts import r2r_jinja
from canvas.view_guards import require_user

@require_user
def post_thread(request):
    default_tag = request.GET.get('t', '')
    if default_tag == 'everything':
        default_tag = 'funny'

    default_category = request.GET.get('c', "funny")
    if default_category == "following" or default_category == "everything":
        default_category = "funny"

    ctx = {
        'default_category': default_category,
        'default_tag': default_tag,
        'show_post_thread_button': False,
    }

    return r2r_jinja('post_thread/post_thread.html', ctx, request)

def popup_post_thread(request):
    try:
        upload_url = urllib.unquote(request.GET.get('upload_url'))
    except AttributeError:
        raise Http404

    if not request.user.is_authenticated():
        #return render_to_response('post_thread/popup_redirect_to_signup.django.html')
        return HttpResponseRedirect('/signup?' + urllib.urlencode({
            'next': reverse(popup_post_thread),
            'upload_url': upload_url,
        }))

    ctx = {
        'default_category': None,
        'default_tag': '',
        'show_post_thread_button': False,
        'upload_url': upload_url,
    }

    return r2r_jinja('post_thread/popup_post_thread.html', ctx, request)

@require_user
def popup_thread_posted(request):
    ctx = {}

    comment = get_object_or_404(Comment.all_objects, pk=request.GET.get('comment'))
    comment_details = comment.details()
    tile = TileDetails(comment_details)

    thumbnail = comment_details.reply_content.get_absolute_url_for_image_type('stream')

    ctx.update({
        'comment': comment_details,
        'tile': tile,
        'thumbnail_url': thumbnail,
    })
    return r2r_jinja('post_thread/popup_thread_posted.html', ctx, request)


