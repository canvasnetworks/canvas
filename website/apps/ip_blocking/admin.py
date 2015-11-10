from django.contrib import admin

from apps.ip_blocking.models import IPBlock
from canvas.util import Now
from services import Services


class IPBlockAdmin(admin.ModelAdmin):
    list_display = ('ip', 'moderator', 'timestamp', 'note')
    list_filter = ('moderator',)
    search_fields = ['ip', 'moderator__username', 'note']
    fieldsets = [
        (None, {
            'fields': [('ip', 'note')],
        }),
    ]

    def save_model(self, request, obj, form, change):
        obj.moderator = request.user
        obj.timestamp = Now()
        obj.save()

admin.site.register(IPBlock, IPBlockAdmin)

