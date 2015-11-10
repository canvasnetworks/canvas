from django.http import HttpResponseRedirect

from apps.activity.models import Activity


class ActivityReadMiddleware(object):
    def process_request(self, request):
        activity_id = request.GET.get('from_activity')
        if not activity_id:
            return

        try:
            activity_id = int(activity_id)
        except ValueError:
            pass

        try:
            request.user.redis.activity_stream.mark_read(activity_id)
        except AttributeError:
            pass

        query = request.GET.copy()
        del query['from_activity']
        url = request.path
        if query:
            url += '?' + query.urlencode()

        return HttpResponseRedirect(url)

