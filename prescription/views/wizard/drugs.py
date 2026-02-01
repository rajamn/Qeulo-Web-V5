from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from prescription.models import PrescriptionDraft, PrescriptionMaster,PrescriptionDetails
from patients.models import Patient
from appointments.models import AppointmentDetails
from drugs.models import DrugTemplate
import json

@login_required
@require_POST
def ai_copy_old_prescription(request, draft_id, prescription_id):
    draft = get_object_or_404(
        PrescriptionDraft,
        pk=draft_id,
        doctor=request.user.doctor,
        hospital=request.user.doctor.hospital,
    )

    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    old_rx = get_object_or_404(
        PrescriptionMaster,
        pk=prescription_id,
        patient_id=draft.data.get("patient_id")
    )

    copied_drugs = []
    for d in old_rx.details.all():
        copied_drugs.append({
            "drug_name": d.drug_name,
            "composition": d.composition,
            "dosage": d.dosage,
            "frequency": d.frequency,
            "duration": d.duration,
            "food_order": d.food_order or "after",
        })

    # Merge into current draft without overriding existing ones
    current = draft.data.get("drugs", [])
    existing_names = {x["drug_name"].lower() for x in current}

    for drug in copied_drugs:
        if drug["drug_name"].lower() not in existing_names:
            current.append(drug)

    draft.data["drugs"] = current
    draft.save(update_fields=["data", "updated_at"])

    return JsonResponse({"status": "ok", "added": copied_drugs})

@require_POST
@login_required
def ai_add_drug(request, draft_id):
    draft = get_object_or_404(
        PrescriptionDraft,
        pk=draft_id,
        doctor=request.user.doctor,
        hospital=request.user.doctor.hospital,
    )

    if draft.doctor != request.user.doctor:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # Load JSON
    try:
        payload = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Get patient
    patient_id = draft.data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient"}, status=400)

    patient = Patient.objects.get(pk=patient_id)
    hospital = draft.hospital

    # Appointment (optional)
    appointment = None
    appt_id = draft.data.get("appointment_id")
    if appt_id:
        appointment = AppointmentDetails.objects.filter(pk=appt_id).first()

    # ------------------------------
    # 1️⃣ CREATE MASTER IF NOT EXISTS
    # ------------------------------
    master = PrescriptionMaster.objects.filter(
        draft_id=draft.id, draft=True
    ).first()

    if not master:
        master = PrescriptionMaster.objects.create(
            draft=True,
            draft_id=draft.id,
            patient=patient,
            doctor=draft.doctor,
            hospital=hospital,
            appointment=appointment,
            # Notes copied ONLY at finalization
        )

    # ------------------------------
    # 2️⃣ DETERMINE COMPOSITION
    # ------------------------------
    composition = payload.get("composition")
    if not composition:
        from drugs.models import Drug
        d = Drug.objects.filter(brand_name__iexact=payload["drug_name"]).first()
        composition = d.generic_name if d else payload["drug_name"]

    # ------------------------------
    # 3️⃣ SAVE DRUG AS PERSISTENT DETAIL ROW
    # ------------------------------
    raw_food = (payload.get("food_order") or "").lower().strip()

    if "before" in raw_food:
        food_order = "before"
    elif "after" in raw_food:
        food_order = "after"
    else:
        food_order = "after"

    
    PrescriptionDetails.objects.create(
        prescription=master,
        hospital=hospital,
        drug_name=payload["drug_name"],
        composition=composition,
        dosage=payload.get("dosage", ""),
        frequency=payload.get("frequency", ""),
        duration=payload.get("duration", ""),
        food_order=payload.get("food_order", "after"),
    )


    return JsonResponse({"status": "ok"})


@require_POST
@login_required
def apply_drug_template_to_draft(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    template_id = request.POST.get("template_id")
    if not template_id:
        return JsonResponse({"error": "Missing template_id"}, status=400)

    template = get_object_or_404(
        DrugTemplate,
        pk=template_id,
        doctor=draft.doctor
    )

    drugs_payload = []

    for it in template.items.all().order_by("id"):
        name = (it.drug_name or (it.drug.drug_name if it.drug else "")).strip()
        if not name:
            continue

        raw_food = (it.food_order or "").lower()
        if "before" in raw_food:
            food = "before"
        else:
            food = "after"

        drugs_payload.append({
            "drug_name": name,
            "composition": (it.composition or "").strip(),
            "dosage": (it.dosage or "").strip(),
            "frequency": (it.frequency or "").strip(),
            "duration": (it.duration or "").strip(),
            "food_order": food,
        })

    # Canonical overwrite (by design)
    draft.data["drugs"] = drugs_payload
    draft.save(update_fields=["data", "updated_at"])

    return JsonResponse({
        "status": "ok",
        "drugs": drugs_payload
    })
