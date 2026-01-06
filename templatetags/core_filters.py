#core/templatetags/core_filters.py

from django import template

register = template.Library()

@register.filter(name="add_attr")
def add_attr(bound_field, arg):
    """
    Safely adds attributes to a Django BoundField widget.
    Works with chained usage:
        {{ field|add_attr:"class='x y'"|add_attr:"placeholder=Hi" }}
    """

    try:
        field = bound_field.field
        widget = field.widget

        # Clone existing attrs
        attrs = widget.attrs.copy()

        for part in arg.split():
            if "=" in part:
                k, v = part.split("=", 1)

                # strip quotes
                if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                    v = v[1:-1]

                if k == "class":
                    # append class instead of overwriting
                    existing = attrs.get("class", "")
                    attrs["class"] = (existing + " " + v).strip()
                else:
                    attrs[k] = v
            else:
                # boolean attribute
                attrs[part] = part

        # Re-render with merged attrs
        return bound_field.as_widget(attrs=attrs)

    except Exception:
        # Fallback – return original field rendered
        return bound_field


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.simple_tag(takes_context=True)
def is_active(context, namespace=None, names=""):
    """
    Returns 'active' when the current route matches either:
      - the given namespace, or
      - any of the comma-separated url_names in `names`.

    Usage:
      {% is_active namespace='billing' %}
      {% is_active names='collection_today,collection_on' %}
    """
    request = context.get("request")
    if not request or not hasattr(request, "resolver_match"):
        return ""
    rm = request.resolver_match

    if namespace and rm.namespace == namespace:
        return "active"

    if names:
        name_list = [n.strip() for n in str(names).split(",") if n.strip()]
        if rm.url_name in name_list:
            return "active"

    return ""

@register.filter
def in_csv(value, csv_string):
    """
    Usage: {{ value|in_csv:"a,b,c" }} -> True/False
    """
    if value is None:
        return False
    options = [opt.strip() for opt in csv_string.split(",")]
    return value in options
