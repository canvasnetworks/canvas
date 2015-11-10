from django.conf.urls.defaults import *
from canvas.shortcuts import direct_to_template
from canvas.view_guards import require_staff

urlpatterns = patterns('drawquest.apps.quests.views',
    url(r'^schedule$', 'schedule'),
)
top_comments_urls = patterns('drawquest.apps.quests.views',
    url(r'^top_comments$', require_staff(direct_to_template), kwargs={'template': 'quests/top_comments.html'}, name='top_comments_page'),
)
# To guarantee their import.
import drawquest.apps.quests.signals

