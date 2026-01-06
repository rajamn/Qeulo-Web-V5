# queue_mgt/templatetags/queue_filters.py

from django import template

register = template.Library()

@register.filter(name='replace')
def replace(value, arg):
    try:
        old, new = arg.split(',')
        return value.replace(old, new)
    except Exception:
        return value  # fail gracefully
    