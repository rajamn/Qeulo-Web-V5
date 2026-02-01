# prescription/views/wizard/decision.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from doctors.utils import get_doctor_sidebar_ctx
from prescription.models import PrescriptionDraft
from patients.models import Patient
from doctors.utils import get_doctor_today_context



@login_required
def decision_hub(request, draft_id):
    doctor = getattr(request.user, "doctor", None)
    if doctor is None:
        messages.error(request, "Only doctors can access prescriptions.")
        return redirect("queue")

    draft = get_object_or_404(
        PrescriptionDraft,
        pk=draft_id,
        doctor=doctor,
        hospital=doctor.hospital,
        finalized=False,
    )

    patient = get_object_or_404(
        Patient,
        pk=draft.data.get("patient_id"),
        hospital=doctor.hospital
    )

    data = draft.data or {}

    doctor_context = get_doctor_today_context(doctor)

    context = {
        "draft": draft,
        "patient": patient,

        # snapshot
        "history": data.get("history", ""),
        "symptoms": data.get("symptoms", ""),
        "findings": data.get("findings", ""),
        "diagnosis": data.get("diagnosis", ""),
        "drugs": data.get("drugs", []) or data.get("carried_drugs", []),
        "is_edit_mode": False, 
        "ai_enabled": data.get("ai_enabled", False),

        # 🔹 NEW
        "doctor_ctx": doctor_context,
    }
    context["sidebar_ctx"] = get_doctor_sidebar_ctx(request.user)


    return render(
        request,
        "prescription/wizard/decision.html",
        context,
    )


@login_required
def doctor_workspace_entry(request):
    doctor = request.user.doctor

    if not doctor:
        redirect("queue")

    doctor_ctx = get_doctor_today_context(doctor)

    context = {
        "mode": "idle",              # ← KEY
        "doctor_ctx": doctor_ctx,
        "sidebar_ctx": get_doctor_sidebar_ctx(request.user),

        # explicitly NO draft, NO patient
        "draft": None,
        "patient": None,
        "is_edit_mode": False,
        "dw_mode": "active",
    }

    return render(request,"prescription/wizard/workspace_entry.html",context)

