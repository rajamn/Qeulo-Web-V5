from django.contrib.auth.decorators import login_required
from django.http  import JsonResponse
from drugs.models import UserPreset, Drug


@login_required
def notes_autocomplete(request):
    """AJAX endpoint: Return matching user presets for a given notes field"""
    # Expected query params: ?field=notes_history&term=his
    field_name = request.GET.get('field') or ''
    term = request.GET.get('term', '')
    # Filter presets that contain the term
    qs = UserPreset.objects.filter(
        user=request.user,
        field_name=field_name,
        value__icontains=term
    ).values_list('value', flat=True).distinct()
    # Build the JSON response for jQuery UI Autocomplete
    suggestions = [{'label': v, 'value': v} for v in qs]
    return JsonResponse(suggestions, safe=False)