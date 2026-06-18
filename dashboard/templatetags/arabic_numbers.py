from django import template

register = template.Library()


@register.filter
def format_money(value):
    """Format a number with English thousands separator, e.g. 1550000 -> 1,550,000"""
    try:
        value = int(value)
        return '{:,}'.format(value)
    except (ValueError, TypeError):
        return value


@register.filter
def arabic_intcomma(value):
    """Alias kept for backwards compatibility – same as format_money."""
    return format_money(value)
