from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction
from django.urls import reverse
from django.shortcuts import redirect
from django.db.models import F
from django.http import JsonResponse
from patients.models import Patient
from appointments.models import AppointmentDetails
from drugs.models import DoctorDrugUsage
from datetime import date,datetime
import json
from prescription.models import ( PrescriptionDraft,PrescriptionMaster,
                                 PrescriptionDetails,)

@require_POST
@login_required
def ai_finalize(request, draft_id):
    draft = get_object_or_404(
        PrescriptionDraft,
        pk=draft_id,
        doctor=request.user.doctor,
        hospital=request.user.doctor.hospital,
    )

    # 🔒 Idempotency: already finalized
    if draft.finalized:
        master = PrescriptionMaster.objects.filter(
            patient_id=draft.data.get("patient_id"),
            doctor=draft.doctor,
            hospital=draft.hospital,
        ).order_by("-id").first()

        if master:
            return JsonResponse({
                "redirect": reverse(
                    "prescription:prescription_view",
                    args=[master.id]
                )
            })

        return JsonResponse({"error": "Prescription already finalized"}, status=400)

    data = draft.data or {}

    # ---- Validate patient ----
    patient_id = data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Patient missing"}, status=400)

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
        hospital=draft.hospital,
    )

    # ---- Validate drugs ----
    raw_drugs = data.get("drugs") or []
    drugs = [d for d in raw_drugs if (d.get("drug_name") or "").strip()]

    if not drugs:
        return JsonResponse({"error": "At least one medicine required"}, status=400)

    doctor = draft.doctor
    hospital = draft.hospital

    # ---- Resolve appointment (best effort) ----
    appointment = None
    appt_id = data.get("appointment_id")

    if appt_id:
        appointment = AppointmentDetails.objects.filter(
            pk=appt_id,
            hospital=hospital,
        ).first()

    if not appointment:
        appointment = AppointmentDetails.objects.filter(
            patient=patient,
            doctor=doctor,
            hospital=hospital,
            appointment_on=date.today(),
            completed__in=[
                AppointmentDetails.STATUS_REGISTERED,
                AppointmentDetails.STATUS_IN_QUEUE,
            ],
        ).order_by("-appoint_id").first()

    # ---- Atomic finalize ----
    try:
        with transaction.atomic():

            master = PrescriptionMaster.objects.create(
                patient=patient,
                doctor=doctor,
                hospital=hospital,
                appointment=appointment,
                notes_history=data.get("history", ""),
                notes_symptoms=data.get("symptoms", ""),
                notes_findings=data.get("findings", ""),
                diagnosis=data.get("diagnosis", ""),
                general_advice=data.get("general_advice", ""),
            )

            for d in drugs:
                PrescriptionDetails.objects.create(
                    prescription=master,
                    hospital=hospital,
                    drug_name=d.get("drug_name", "").strip().title(),
                    composition=(d.get("composition") or "").strip(),
                    dosage=(d.get("dosage") or "").strip(),
                    frequency=(d.get("frequency") or "").strip(),
                    duration=(d.get("duration") or "").strip(),
                    food_order="before"
                        if "before" in (d.get("food_order") or "").lower()
                        else "after",
                    instructions=(d.get("instructions") or "").strip(),
                )

                DoctorDrugUsage.objects.update_or_create(
                    doctor=doctor,
                    drug_name=d.get("drug_name").strip().title(),
                    defaults={"usage_count": F("usage_count") + 1},
                )

            if appointment:
                appointment.completed = AppointmentDetails.STATUS_DONE
                appointment.completed_at = datetime.now()
                appointment.save(update_fields=["completed", "completed_at"])

            draft.finalized = True
            draft.current_step = "finalized"
            draft.save(update_fields=["finalized", "current_step", "updated_at"])

    except Exception as e:
        return JsonResponse(
            {"error": f"Finalize failed: {str(e)}"},
            status=500,
        )

    return JsonResponse({
        "redirect": reverse(
            "prescription:prescription_view",
            args=[master.id],
        )
    })
