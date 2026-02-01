from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from prescription.models import PrescriptionDraft, PrescriptionMaster,DoctorHistoryTemplate
from patients.models import Patient
# from prescription.constants.history_constants import STD_HISTORY
from prescription.constants.history_phrases import STD_HISTORY_PHRASES
from doctors.utils import get_doctor_sidebar_ctx

# ---------------------------------------------------------
# 3. STEP-1: HISTORY
# ---------------------------------------------------------

@login_required
def history_step(request, draft_id):

    doctor = getattr(request.user, "doctor", None)
    if not doctor:
        return HttpResponseForbidden("Doctor access required")

    draft = get_object_or_404(
        PrescriptionDraft,
        pk=draft_id,
        finalized=False,
        doctor=doctor,
    )

    patient_id = draft.data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient in draft"}, status=400)

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
        hospital=draft.hospital
    )

    carried_history = draft.data.get("carried", {}).get("history", "")
    existing_history = draft.data.get("history", "")

    doctor_templates = DoctorHistoryTemplate.objects.filter(
        doctor=doctor
    ).values("label", "content")

    primary = doctor.primary_specialty
    secondary = doctor.secondary_specialties or []
    applicable = set([primary, *secondary, "general"])

    phrases = [
        p for p in STD_HISTORY_PHRASES
        if applicable.intersection(p["specialties"])
    ]
    phrases.sort(key=lambda p: p["priority"])

    if request.method == "POST":
        draft.data["history"] = request.POST.get("history", "")
        draft.save(update_fields=["data", "updated_at"])
        return redirect("prescription:ai_rx_decision", draft_id=draft.id)

    past_prescriptions = (
        PrescriptionMaster.objects
        .filter(patient_id=patient_id, hospital=draft.hospital)
        .exclude(id=draft.data.get("existing_prescription_id"))
        .order_by("-prescribed_on")
        .prefetch_related("details")[:3]
    )

    context = {
        "draft": draft,
        "patient": patient,
        "history": existing_history,
        "carried_history": carried_history,
        "past_prescriptions": past_prescriptions,
        "doctor_templates": doctor_templates,
        "history_phrases": phrases,
        "is_edit_mode": True,
        "dw_mode": "edit",
    }
    context["sidebar_ctx"] = get_doctor_sidebar_ctx(request.user)

    return render(request, "prescription/wizard/history.html", context)



@login_required
@require_POST
def add_history_template(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)
    doctor = draft.doctor

    label = request.POST.get("label", "").strip()
    content = request.POST.get("content", "").strip()

    if label and content:
        DoctorHistoryTemplate.objects.create(
            doctor=doctor,
            label=label,
            content=content
        )
        messages.success(request, "Custom template added.")

    return redirect("prescription:ai_rx_history", draft_id=draft_id)

def merge_history(carried="", selected=None, free_text=""):
    """
    Merge carried history, selected tags, and free text
    into a clean, de-duplicated multiline string.
    """
    parts = []

    if carried:
        parts.extend([line.strip() for line in carried.splitlines() if line.strip()])

    if selected:
        parts.extend(dict.fromkeys(s.strip() for s in selected if s.strip()))


    if free_text:
        parts.extend([line.strip() for line in free_text.splitlines() if line.strip()])

    # De-duplicate while preserving order
    seen = set()
    final = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            final.append(p)

    return "\n".join(final)
