from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from prescription.models import PrescriptionDraft, PrescriptionMaster
from patients.models import Patient
from doctors.utils import get_doctor_sidebar_ctx
from prescription.constants.symptoms_constants import STANDARD_SYMPTOMS

# ---------------------------------------------------------
# 4. STEP-2: SYMPTOMS
# ---------------------------------------------------------

@login_required
def symptoms_step(request, draft_id):
    draft = get_object_or_404(
        PrescriptionDraft,
        pk=draft_id,
        finalized=False,
        doctor=getattr(request.user, "doctor", None),
    )

    patient_id = draft.data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient in draft"}, status=400)

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
        hospital=draft.hospital
    )

    data = draft.data or {}

    # ---------------------------------------------
    # Carry-forward symptoms ONLY ONCE
    # ---------------------------------------------
    if "notes_symptoms" not in data.get("carried", {}):
        last_rx = (
            PrescriptionMaster.objects
            .filter(patient=patient, doctor=draft.doctor)
            .order_by("-id")
            .first()
        )
        if last_rx and last_rx.notes_symptoms:
            carried = data.get("carried", {})
            carried["notes_symptoms"] = last_rx.notes_symptoms
            data["carried"] = carried
            draft.data = data
            draft.save(update_fields=["data"])

    carried_symptoms = data.get("carried", {}).get("symptoms", "")
    existing_symptoms = data.get("symptoms", "")

    if request.method == "POST":
        data["notes_symptoms"] = request.POST.get("symptoms", "")
        data.setdefault("touched", {})["notes_symptoms"] = True

        draft.data = data
        draft.current_step = "symptoms"
        draft.save(update_fields=["data", "current_step", "updated_at"])

        return redirect("prescription:ai_rx_decision", draft_id=draft.id)

    context = {
        "draft": draft,
        "patient": patient,
        "symptoms": existing_symptoms,
        "carried_symptoms": carried_symptoms,
        "is_edit_mode": True,
        "dw_mode": "edit",
        "std_symptoms": STANDARD_SYMPTOMS,
        "quick_symptoms": [
            "Fever", "Cough", "Headache", "Breathlessness",
            "Vomiting", "Diarrhea", "Abdominal Pain",
            "Fatigue", "Dizziness", "Rash"
        ],
    }

    context["sidebar_ctx"] = get_doctor_sidebar_ctx(request.user)

    return render(request, "prescription/wizard/symptoms.html", context)



