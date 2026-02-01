from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from patients.models import Patient
from prescription.models import PrescriptionDraft, PrescriptionDetails, PrescriptionMaster,DoctorHistoryTemplate
from appointments.models import AppointmentDetails
# ---------------------------------------------------------
# 1. Start AI Prescription
# ---------------------------------------------------------

# prescription/views/wizard/start.py

@login_required
def ai_start(request):
    doctor = getattr(request.user, "doctor", None)
    if doctor is None:
        messages.error(request, "Only doctors can write prescriptions.")
        return redirect("queue")

    patient_id = request.GET.get("patient")
    if not patient_id:
        messages.error(request, "Patient not selected.")
        return redirect("queue")

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
        hospital=doctor.hospital
    )

    ai_mode = request.GET.get("ai_mode", "true") == "true"

    # 🔹 Try to reuse latest unfinished draft
    draft = (
        PrescriptionDraft.objects
        .filter(
            doctor=doctor,
            hospital=doctor.hospital,
            finalized=False,
            data__patient_id=patient.id,
        )
        .order_by("-updated_at")
        .first()
    )

    if draft:
        return redirect("prescription:ai_rx_decision", draft_id=draft.id)

    # 🔹 No draft → create new one
    previous_rx = (
        PrescriptionMaster.objects
        .filter(patient=patient, doctor=doctor, hospital=doctor.hospital)
        .order_by("-prescribed_on")
        .first()
    )

    carried = {}
    carried_drugs = []

    if previous_rx:
        carried = {
            "history": previous_rx.notes_history or "",
            "symptoms": previous_rx.notes_symptoms or "",
            "findings": previous_rx.notes_findings or "",
            "diagnosis": previous_rx.diagnosis or "",
        }

        carried_drugs = [
            {
                "drug_name": d.drug_name,
                "composition": d.composition,
                "dosage": d.dosage,
                "frequency": d.frequency,
                "duration": d.duration,
                "food_order": d.food_order or "",
            }
            for d in previous_rx.details.all()
        ]

    draft = PrescriptionDraft.objects.create(
        doctor=doctor,
        hospital=doctor.hospital,
        current_step="history",
        data={
            "patient_id": patient.id,
            "ai_enabled": ai_mode,
            "carried": carried,
            "carried_drugs": carried_drugs,
        },
    )

    # if carried or carried_drugs:
    #     return redirect("prescription:ai_rx_decision", draft_id=draft.id)

    # return redirect("prescription:ai_rx_history", draft_id=draft.id)

    return redirect("prescription:ai_rx_decision", draft_id=draft.id)

    


# ---------------------------------------------------------
# 2. Create Draft when patient is selected
# ---------------------------------------------------------

@login_required
def select_patient(request):
    """
    Doctor selects a patient/appointment. If draft exists, reuse.
    Else create new one.
    """
    doctor = getattr(request.user, "doctor", None)
    hospital = request.user.hospital
    appt_id = request.GET.get("appointment")

    if not doctor or not appt_id:
        messages.error(request, "Select a patient to start prescription.")
        return redirect("ai_prescription_start")

    appt = get_object_or_404(AppointmentDetails, pk=appt_id, doctor=doctor, hospital=hospital)

    draft, created = PrescriptionDraft.objects.get_or_create(
        doctor=doctor,
        appointment=appt,
        defaults={
            "hospital": hospital,
            "current_step": "history",
            "data": {},
            "ai_suggestions": {},
            "dw_mode": "edit",
        }
    )

    return redirect("prescription:ai_rx_history", draft_id=draft.id)

