from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from drugs.models import Drug, UserPreset
from prescription.models import PrescriptionItem
import json
from drugs.constants import PRESETS

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Drug

@require_GET
@login_required
def drug_autocomplete(request):
    query = request.GET.get('term') or request.GET.get('q', '')
    results = []

    if query:
        drugs = Drug.objects.filter(Q(drug_name__icontains=query)).order_by('drug_name')[:20]
        results = [{
            'id': drug.id,
            'label': drug.drug_name,
            'value': drug.drug_name,
            'composition': drug.composition or '',
        } for drug in drugs]

    return JsonResponse(results, safe=False)


# ✅ Drug autocomplete (used by drug name field)
@require_GET
@login_required
def notes_autocomplete(request):
    field = request.GET.get('field')
    term = request.GET.get('term', '').strip().lower()

    if not field or field not in PRESETS:
        return JsonResponse([], safe=False)

    presets_default = PRESETS[field]

    # 1. User-defined presets
    user_presets = list(UserPreset.objects.filter(
        user=request.user, field_name=field
    ).values_list("value", flat=True))

    # 2. Frequently used values (hospital-specific)
    used_values = list(PrescriptionItem.objects.filter(
        prescription__hospital=request.user.hospital
    ).exclude(**{field: None}).values(field).annotate(
        count=Count(field)
    ).order_by('-count').values_list(field, flat=True)[:10])

    # 3. Combine without duplicates
    combined = user_presets + [v for v in presets_default if v not in user_presets] + \
               [v for v in used_values if v not in user_presets and v not in presets_default]

    filtered = [val for val in combined if term in val.lower()][:10]

    # ✅ Final payload with 'field'
    results = [{"label": val, "value": val, "field": field} for val in filtered]

    return JsonResponse(results, safe=False)


# ✅ Save a user-defined preset
@csrf_exempt
@login_required
def save_user_preset(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            field = data.get("field_name")
            value = data.get("value", "").strip()

            if field in PRESETS and value:
                UserPreset.objects.get_or_create(
                    user=request.user, field_name=field, value=value
                )
                return JsonResponse({"message": "Preset saved!"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)

def get_combined_presets(user, field):
    user_presets = list(UserPreset.objects.filter(user=user, field_name=field).values_list("value", flat=True))
    default_presets = PRESETS.get(field, [])
    return user_presets + [v for v in default_presets if v not in user_presets]
