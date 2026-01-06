# prescription/views_ajax.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils.text import capfirst

from drugs.models import Drug
from doctors.models import Doctor


# ---------------------------------------------------------
# 🔍 1) Autocomplete — returns matching drug names
# ---------------------------------------------------------
@login_required
@require_GET
def drug_autocomplete(request):
    term = request.GET.get("term", "").strip()

    if not term:
        return JsonResponse([], safe=False)

    qs = Drug.objects.filter(
        Q(drug_name__icontains=term) |
        Q(composition__icontains=term)
    ).order_by("drug_name")[:20]

    results = [
        {
            "label": f"{d.drug_name} ({d.composition})" if d.composition else d.drug_name,
            "value": d.drug_name,
            "composition": d.composition or "",
        }
        for d in qs
    ]

    return JsonResponse(results, safe=False)


# ---------------------------------------------------------
# ➕ 2) Add new Drug (Manual Entry)
# ---------------------------------------------------------
@login_required
@require_POST
def ajax_add_drug(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    name = request.POST.get("drug_name", "").strip()
    comp = request.POST.get("composition", "").strip()

    if not name or not comp:
        return JsonResponse({"error": "Both drug name and composition are required."})

    doctor = getattr(request.user, "doctor", None)
    hospital = doctor.hospital if doctor else None

    try:
        drug = Drug(
            drug_name=name,
            composition=comp,
            hospital=hospital,
            added_by_doctor=doctor
        )
        drug.save()
    except ValueError as e:
        return JsonResponse({"error": str(e)})

    return JsonResponse({
        "success": True,
        "text": f"{drug.drug_name} ({drug.composition})"
    })
