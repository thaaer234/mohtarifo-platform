import base64
import mimetypes

from django import template
from django.contrib.staticfiles import finders
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def inline_static(path):
    static_path = finders.find(path)
    if not static_path:
        return ''

    with open(static_path, encoding='utf-8') as static_file:
        return mark_safe(static_file.read())


@register.simple_tag
def static_data_uri(path):
    static_path = finders.find(path)
    if not static_path:
        return ''

    mime_type = mimetypes.guess_type(static_path)[0] or 'application/octet-stream'
    with open(static_path, 'rb') as static_file:
        encoded = base64.b64encode(static_file.read()).decode('ascii')

    return mark_safe(f'data:{mime_type};base64,{encoded}')
