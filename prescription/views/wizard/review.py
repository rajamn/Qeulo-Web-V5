from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from prescription.models import PrescriptionDraft
from patients.models import Patient

# ---------------------------------------------------------
# STEP 9: REVIEW & FINALIZE
# ---------------------------------------------------------

@login_required
def ai_review(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    patient_id = draft.data.get("patient_id")
    patient = Patient.objects.get(pk=patient_id)

    raw_drugs = draft.data.get("drugs", []) or []

    # -------------- CLEAN & SANITIZE DRUGS ----------------
    cleaned_drugs = []
    for d in raw_drugs:
        if not isinstance(d, dict):
            continue

        drug_name = (d.get("drug_name") or "").strip()
        if not drug_name:
            continue  # skip blank rows

        cleaned_drugs.append({
            "drug_name": drug_name,
            "composition": (d.get("composition") or "").strip(),
            "dosage": (d.get("dosage") or "").strip(),
            "frequency": (d.get("frequency") or "").strip(),
            "duration": (d.get("duration") or "").strip(),
            "food_order": (d.get("food_order") or "").strip(),
            "instructions":(d.get("instructions") or "").strip(),
        })

    context = {
        "draft": draft,
        "patient": patient,
        "history": draft.data.get("history", ""),
        "symptoms": draft.data.get("symptoms", ""),
        "findings": draft.data.get("findings", ""),
        "diagnosis": draft.data.get("diagnosis", ""),
        "general_advice": draft.data.get("general_advice", ""),
        "drugs": cleaned_drugs,
        "dw_mode": "edit",
        "is_edit_mode": True,
    }

    return render(request, "prescription/wizard/ai_review.html", context)
