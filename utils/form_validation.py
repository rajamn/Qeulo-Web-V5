# utils/form_validation.py
import logging
from django.forms.utils import ErrorList
from django.contrib import messages

logger = logging.getLogger(__name__)

def first_error_string(form):
    """
    Returns a compact string of the first field + message (or non-field error).
    """
    if form.non_field_errors():
        return f"non_field: {form.non_field_errors().as_text()}"
    for field, errors in form.errors.items():
        if isinstance(errors, ErrorList) and errors:
            return f"{field}: {errors[0]}"
    return "(no error text)"

def validate_or_report(request, name, form):
    """
    Runs is_valid on a form.
      - Logs full JSON errors if invalid
      - Adds a short message to the user
      - Returns True/False
    """
    if form.is_valid():
        return True

    # Full structured errors in logs
    logger.warning("[%s] validation failed; errors=%s; prefix=%s",
                   name, form.errors.get_json_data(), form.prefix)

    # Short, readable message
    first = first_error_string(form)
    messages.error(request, f"❌ {name.title()} form error → {first}")

    return False
