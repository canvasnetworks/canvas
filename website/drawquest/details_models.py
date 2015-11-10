from django.conf import settings

from canvas.details_models import ContentDetails as CanvasContentDetails


class ContentDetails(CanvasContentDetails):
    UGC_IMAGES = [
        ('gallery', True),
        ('homepage_featured', True),
        ('archive', True),
        ('activity', True),
        ('editor_template', True),
    ]

    TO_CLIENT_WHITELIST = [
        'id',
        'timestamp',
        'original',
    ] + UGC_IMAGES

    def ugc_content(self, content):
        if content:
            url = self.ugc_url(content['name'])

            return {
                'url': url,
            }

        return {}

