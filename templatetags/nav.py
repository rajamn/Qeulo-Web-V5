from django import template
register = template.Library()

@register.simple_tag(takes_context=True)
def is_active(context, *, namespace=None, names=None):
    rm = context.get('request').resolver_match
    if not rm:
        return ""
    if namespace and rm.namespace == namespace:
        return "active"
    if names and rm.url_name in names:
        return "active"
    return ""
