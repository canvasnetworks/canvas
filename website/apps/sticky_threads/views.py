from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from apps.sticky_threads.models import StickyThread, update_sticky_thread_cache, ThreadPreview, sticky_threads
from canvas.models import Comment
from canvas.shortcuts import r2r_jinja
from canvas.view_guards import require_staff
from canvas.view_helpers import redirect_trailing
from services import Services


@require_staff
def sticky_admin(request):
    if request.method == 'POST':
        loaded = {}
        delete = []
        for key, val in request.POST.iteritems():
            if 'sort_order' not in key and 'text' not in key:
                continue
            _, id_ = key.split('-')
            op = get_object_or_404(Comment, id=id_)

            sticky = None
            if 'sort_order' in key:
                if val is None or not str(val).strip():
                    try:
                        sticky = StickyThread.objects.get(comment=op)
                        delete.append(sticky.id)
                    except StickyThread.DoesNotExist:
                        pass
                    continue

                try:
                    ordinal = int(val)
                except ValueError:
                    ordinal = 0

                if id_ not in loaded:
                    loaded[id_] = sticky = StickyThread.get_or_create(op)
                else:
                    sticky = loaded[id_]
                sticky.sort = ordinal

            elif 'text' in key:
                if id_ not in loaded:
                    loaded[id_] = sticky = StickyThread.get_or_create(op)
                else:
                    sticky = loaded[id_]
                sticky.text = val

        for _, sticky in loaded.iteritems():
            if sticky.id in delete:
                sticky.delete()
            else:
                sticky.save()

        page_updated = True
    else:
        page_updated = False

    if page_updated:
        update_sticky_thread_cache()

    ctx = {
        'sticky_threads': sticky_threads(),
        'page_updated': page_updated,
    }
    return r2r_jinja('sticky_threads/admin.html', ctx, request)

