
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from prescription.models import PrescriptionDraft
from patients.models import Patient
import json

@require_POST
@login_required
def autosave_draft(request, draft_id):
    """
    AJAX autosave endpoint.
    Supports:
      - Text fields (history, symptoms, findings, diagnosis, advice)
      - JSON fields (drugs)
    """
    draft = get_object_or_404(
        PrescriptionDraft,
        pk=draft_id,
        doctor=request.user.doctor,
        hospital=request.user.doctor.hospital,
    )

    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    field = request.POST.get("field")
    value = request.POST.get("value", "")

    if not field:
        return JsonResponse({"error": "Missing field"}, status=400)

    if field == "drugs":
        try:
            # Expect JSON string from UI
            parsed = json.loads(value) if isinstance(value, str) else value
            if not isinstance(parsed, list):
                raise ValueError("Drugs must be a list")
            draft.data["drugs"] = parsed
        except Exception:
            return JsonResponse({"error": "Invalid drugs payload"}, status=400)
    else:
        # Plain text fields
        draft.data[field] = (value or "").strip()

    draft.save(update_fields=["data", "updated_at"])
    return JsonResponse({"status": "ok"})