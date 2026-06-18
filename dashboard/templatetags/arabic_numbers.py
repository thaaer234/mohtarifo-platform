from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()

ARABIC_DIGITS = {
    '0': '٠',
    '1': '١',
    '2': '٢',
    '3': '٣',
    '4': '٤',
    '5': '٥',
    '6': '٦',
    '7': '٧',
    '8': '٨',
    '9': '٩',
}

def to_arabic(num_str):
    return ''.join(ARABIC_DIGITS.get(ch, ch) for ch in num_str)

@register.filter
def arabic_intcomma(value):
    """Convert a number to string with Arabic thousand separator and digits."""
    s = intcomma(value)
    s = s.replace(',', '٬')  # Arabic thousands separator
    return to_arabic(s)
