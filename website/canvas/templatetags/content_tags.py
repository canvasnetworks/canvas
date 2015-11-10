from django import template
from canvas.details_models import ContentDetails
from canvas.models import Visibility
register = template.Library()

def _wh(content_data, ratio):
    return dict((dimension, int(content_data[dimension] / ratio),)
                for dimension in ['width', 'height'])

def _fit_inside(fit_w, fit_h, content_data):
    rw = float(content_data['width'])  / fit_w
    rh = content_data['height'] / fit_h
    ratio = max(1, rw, rh)
    return _wh(content_data, ratio)

def _fit_height(fit_h, content_data):
    ratio = float(content_data['height']) / fit_h
    return _wh(content_data, ratio)

def _fit_width(fit_w, content_data):
    ratio = float(content_data['width']) / fit_w
    return _wh(content_data, ratio)

def _size_attrs(content_data, fit_w=None, fit_h=None):
    if fit_w is None and fit_h is None:
        # Do nothing
        return {'width': content_data['width'], 'height': content_data['height']}
    elif fit_w is None:
        return _fit_height(fit_h, content_data)
    elif fit_h is None:
        return _fit_width(fit_w, content_data)
    else:
        return _fit_inside(fit_w, fit_h, content_data)


@register.inclusion_tag('content/tag.django.html')
def content(comment, content_details, image_type):
    """ Renders an html snippet (includes an img tag) for @content_details.
        param @image_type: Could be "column" 
    """
    details = content_details
    if not isinstance(details, ContentDetails):
        details = ContentDetails(details)

    data = details[image_type]
    wh = _size_attrs(data)

    return {
        'url': details.get_absolute_url_for_image_type(image_type),
        'width': wh['width'],
        'height': wh['height'],
        # @TODO: Note the @comment here is a dict. The current version of the details does not store
        # is_visbile. Hence, we're duplicating the is_visibile code here.
        'alt': details.get("remix_text") if comment.get("visibility") == Visibility.PUBLIC else ""
    }


