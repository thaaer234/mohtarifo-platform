from django import template

register = template.Library()

@register.filter
def currency_format(value):
    if value is None or value == "":
        return "مجاني"
    try:
        val = float(value)
        if val == 0:
            return "مجاني"
        return f"{int(val):,} ل.س"
    except (ValueError, TypeError):
        return f"{value} ل.س"
