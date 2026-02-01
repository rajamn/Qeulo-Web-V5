from django.contrib.auth.decorators import login_required
from django.http  import JsonResponse
from drugs.models import UserPreset, Drug
from drugs.forms import DetailInlineFormSet
from drugs.constants import PRESETS as GLOBAL_PRESETS


"""
DORMANT API – not currently wired to URLs.

This version of drug_autocomplete is intended for
future non-UI / REST usage.

Current UI uses views_ajax.drug_autocomplete.
"""



@login_required
def drug_autocomplete(request):
    term = request.GET.get('term', '')
    qs = Drug.objects.filter(name__icontains=term)[:20]
    data = [{
        "label": d.name,
        "value": d.name,
        "composition": d.composition or "",
        # optional defaults:
        "dosage": getattr(d, "default_dosage", "") or "",
        "frequency": getattr(d, "default_frequency", "") or "",
        "duration": getattr(d, "default_duration", "") or "",
        "food_order": getattr(d, "default_food_order", "") or "",
    } for d in qs]
    return JsonResponse(data, safe=False)
