# prescription/views_ai_wizard.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from django.forms import formset_factory
from django.shortcuts import render, get_object_or_404
from prescription.models import PrescriptionDraft, PrescriptionDetails, PrescriptionMaster,DoctorHistoryTemplate
from prescription.forms import PrescriptionMasterForm, ManualDetailFormSet
from drugs.forms import DetailInlineFormSet
from vitals.models import PatientVital
from drugs.models import Drug, DrugTemplate, DrugTemplateItem,DoctorDrugUsage
from appointments.models import AppointmentDetails

from doctors.models import Doctor
from core.models import Hospital
from patients.models import Patient
from openai import OpenAI
import json
from datetime import date, datetime
from visit_workspace.models import VisitDocument
from vitals.models import PatientVital
from prescription.models import PrescriptionMaster, PrescriptionDetails
from prescription.forms import PrescriptionDetailForm
import logging
from django.db.models import F



logger = logging.getLogger(__name__)


DraftDetailFormSet = formset_factory(
    PrescriptionDetailForm,
    extra=0,
    can_delete=True
)



# ---------------------------------------------------------
# 1. Start AI Prescription
# ---------------------------------------------------------


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

    try:
        patient = Patient.objects.get(pk=patient_id, hospital=doctor.hospital)
    except Patient.DoesNotExist:
        messages.error(request, "Invalid patient selected.")
        return redirect("queue")

    ai_mode = request.GET.get("ai_mode", "true") == "true"

    # Fetch last prescription
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

        for d in previous_rx.details.all():
            carried_drugs.append({
                "drug_name": d.drug_name,
                "composition": d.composition,
                "dosage": d.dosage,
                "frequency": d.frequency,
                "duration": d.duration,
                "food_order": d.food_order or "",
            })

    draft = PrescriptionDraft.objects.create(
        doctor=doctor,
        hospital=doctor.hospital,
        current_step="history",
        data={
            "patient_id": patient.id,
            "ai_enabled": ai_mode,
            "carried": carried,        # notes to display
            "carried_drugs": carried_drugs,
        }
    )

    return redirect("prescription:ai_rx_history", draft_id=draft.id)

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
        }
    )

    return redirect("prescription:ai_rx_history", draft_id=draft.id)



# ---------------------------------------------------------
# 3. STEP-1: HISTORY
# ---------------------------------------------------------

@login_required
def edit_history(request, draft_id):
    """
    Step 1 of wizard: enter history, optionally get AI summary.
    """
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    # Ensure only the right doctor can access
    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # ---------------------------------------------------------
    # Load Patient (FIX)
    # ---------------------------------------------------------
    patient_id = draft.data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient in draft"}, status=400)

    
    patient = Patient.objects.get(pk=patient_id)

    # Doctor saved templates (custom history templates)
    doctor_templates = DoctorHistoryTemplate.objects.filter(
        doctor=draft.doctor
    ).values("label", "content")

    # Standard history structure
    STD_HISTORY = {
        "medical_history": [
            "Diabetes Mellitus", "Hypertension", "Asthma", "COPD",
            "Thyroid Disorder", "Epilepsy", "Heart Disease",
            "Tuberculosis (past)", "Hepatitis/Jaundice", "Cancer",
            "Chronic Kidney Disease"
        ],
        "surgical_history": [
            "Appendectomy", "Cesarean Section", "Cardiac Surgery",
            "Orthopedic Surgery", "Other Major Surgery"
        ],
        "allergies": [
            "Drug Allergy", "Food Allergy", "Environmental Allergy",
            "No Known Allergies"
        ],
        "family_history": [
            "Diabetes", "Hypertension", "Heart Disease",
            "Cancer", "Psychiatric Illness", "Genetic Disorders"
        ],
        "medication_history": [
            "Current Medications", "Past Long-term Medications",
            "Steroid Use", "Chemotherapy/Radiotherapy"
        ],
        "social_history": [
            "Smoking", "Alcohol Use", "Substance Use",
            "Occupation Exposure", "Diet Habits", "Exercise Habits"
        ],
        "recent_special_history": [
            "Recent Hospitalization", "Vaccination Status",
            "Trauma/Injury", "Autoimmune Disorders",
            "Pregnancy/Obstetric History"
        ]
    }

    # ---------------------------------------------------------
    # Save POST
    # ---------------------------------------------------------
    if request.method == "POST":
        history_text = request.POST.get("history", "").strip()

        draft.data["history"] = history_text
        draft.current_step = "history"
        draft.save(update_fields=["data", "current_step", "updated_at"])

        return redirect("prescription:ai_rx_symptoms", draft_id=draft.id)

    # ---------------------------------------------------------
    # Fetch past prescriptions (recent 3)
    # ---------------------------------------------------------
    

    past_prescriptions = (
        PrescriptionMaster.objects
        .filter(patient_id=patient_id)
        .exclude(id=draft.data.get("existing_prescription_id", None))
        .order_by("-prescribed_on")
        .prefetch_related("details")[:3]
    )

    context = {
        "draft": draft,
        "patient": patient,    # ⭐ IMPORTANT
        "history": draft.data.get("history", ""),
        "past_prescriptions": past_prescriptions,
        "std_history": STD_HISTORY,
        "doctor_templates": doctor_templates,
    }

    return render(request, "prescription/ai/history.html", context)


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




@login_required
@require_POST
def ai_copy_old_prescription(request, draft_id, prescription_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

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


# ---------------------------------------------------------
# 4. STEP-2: SYMPTOMS
# ---------------------------------------------------------

@login_required
def edit_symptoms(request, draft_id):

    STANDARD_SYMPTOMS = {
        "General": [
            "Fever",
            "Fatigue",
            "Weight Loss",
            "Night Sweats",
            "Loss of Appetite",
        ],
        "Respiratory": [
            "Cough",
            "Shortness of Breath",
            "Chest Pain",
            "Wheezing",
            "Sputum Production",
        ],
        "Cardiovascular": [
            "Palpitations",
            "Chest Tightness",
            "Swelling of Legs",
            "Dizziness",
            "Syncope (Fainting)",
        ],
        "Gastrointestinal": [
            "Abdominal Pain",
            "Nausea",
            "Vomiting",
            "Diarrhea",
            "Constipation",
            "Blood in Stool",
        ],
        "Neurological": [
            "Headache",
            "Seizures",
            "Weakness",
            "Numbness",
            "Tremors",
            "Confusion",
        ],
        "Musculoskeletal": [
            "Joint Pain",
            "Muscle Pain",
            "Back Pain",
            "Stiffness",
            "Swelling",
        ],
        "Dermatological": [
            "Rash",
            "Itching",
            "Redness",
            "Swelling",
            "Ulcer",
        ],
        "Genitourinary": [
            "Burning Urination",
            "Frequent Urination",
            "Blood in Urine",
            "Pelvic Pain",
            "Discharge",
        ],
        "ENT": [
            "Sore Throat",
            "Ear Pain",
            "Hearing Loss",
            "Nasal Congestion",
            "Runny Nose",
        ],
        "Psychiatric": [
            "Depressed Mood",
            "Anxiety",
            "Insomnia",
            "Hallucinations",
            "Memory Loss",
        ],
    }

    """
    Step 2 of wizard: enter symptoms, store in draft.data, continue to findings.
    """
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    # Ensure doctor-only access
    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # -----------------------------
    # Load patient (FIX)
    # -----------------------------
    patient_id = draft.data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient in draft"}, status=400)

    
    patient = Patient.objects.get(pk=patient_id)

    # Load previous prescription to enable Copy Symptoms →
    last_rx = (
        PrescriptionMaster.objects.filter(
            patient=patient,
            doctor=draft.doctor
        )
        .order_by("-id")
        .first()
    )

    if last_rx:
        carried = draft.data.get("carried", {})
        carried["notes_symptoms"] = last_rx.notes_symptoms or ""
        draft.data["carried"] = carried
        draft.save(update_fields=["data"])


    # Existing symptoms
    existing_symptoms = draft.data.get("symptoms", "")

    # -----------------------------
    # Handle POST save
    # -----------------------------
    if request.method == "POST":
        symptoms_text = request.POST.get("symptoms", "").strip()

        # Update JSON
        draft.data["symptoms"] = symptoms_text
        draft.current_step = "symptoms"
        draft.save(update_fields=["data", "current_step", "updated_at"])

        return redirect("ai_rx_findings", draft_id=draft.id)

    # -----------------------------
    # Render template
    # -----------------------------
    context = {
        "draft": draft,
        "patient": patient,
        "symptoms": existing_symptoms,
        "std_symptoms": STANDARD_SYMPTOMS,
    }

    return render(request, "prescription/ai/symptoms.html", context)


# @login_required
# def autosave_draft(request, draft_id):
#     """
#     AJAX autosave endpoint. Expects {field: "history", value: "..."}.
#     """
#     draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

#     if draft.doctor != getattr(request.user, "doctor", None):
#         return JsonResponse({"error": "Unauthorized"}, status=403)

#     field = request.POST.get("field")
#     value = request.POST.get("value", "").strip()

#     if not field:
#         return JsonResponse({"error": "Missing field"}, status=400)

#     draft.data[field] = value
#     draft.save(update_fields=["data", "updated_at"])

#     return JsonResponse({"status": "ok"})


@require_POST
@login_required
def autosave_draft(request, draft_id):
    """
    AJAX autosave endpoint.
    Supports:
      - Text fields (history, symptoms, findings, diagnosis, advice)
      - JSON fields (drugs)
    """
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

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


# ---------------------------------------------------------
# 5. STEP-3: FINDINGS
# ---------------------------------------------------------

@login_required
def edit_findings(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    # Only the assigned doctor can access
    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # ------------------------
    # Load patient
    # ------------------------
    patient_id = draft.data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient in draft"}, status=400)

    patient = Patient.objects.get(pk=patient_id, hospital=draft.hospital)

    # ------------------------
    # Load documents + vitals
    # ------------------------
    visit_docs = VisitDocument.objects.filter(
        hospital=draft.hospital,
        patient=patient
    ).order_by("-created_at")

    latest_vitals = PatientVital.objects.filter(
        hospital=draft.hospital,
        patient=patient
    ).order_by("-recorded_at").first()

    # ------------------------
    # Build vitals block
    # ------------------------
    if latest_vitals:
        bmi = latest_vitals.bmi if latest_vitals.bmi not in [None, "", 0] else "—"

        vitals_block = (
            "Vitals:\n"
            f"Ht {latest_vitals.height_cm or '—'} cm · "
            f"Wt {latest_vitals.weight_kg or '—'} kg (BMI {bmi}) · "
            f"Temp {latest_vitals.temperature_c or '—'} °C\n"
            f"BP {latest_vitals.bp_systolic or '—'}/{latest_vitals.bp_diastolic or '—'} · "
            f"Pulse {latest_vitals.pulse_bpm or '—'} bpm · "
            f"SpO₂ {latest_vitals.spo2_percent or '—'}%"
        )
    else:
        vitals_block = (
            "Vitals:\n"
            "Ht:    · Wt:    · Temp:   \n"
            "BP:    · Pulse:    · SpO₂:   "
        )

    # ---------------------------------------------
    # ✨ Carried-forward logic for Previous Findings
    # ---------------------------------------------
    last_rx = (
        PrescriptionMaster.objects.filter(
            patient=patient,
            doctor=draft.doctor
        )
        .order_by("-id")
        .first()
    )

    if last_rx:
        carried = draft.data.get("carried", {})
        carried["notes_findings"] = last_rx.notes_findings or ""
        draft.data["carried"] = carried
        draft.save(update_fields=["data"])


    # ------------------------
    # POST
    # ------------------------
    if request.method == "POST":
        findings_text = request.POST.get("findings", "").strip()
        draft.data["findings"] = findings_text
        draft.current_step = "findings"
        draft.save(update_fields=["data", "current_step", "updated_at"])
        return redirect("ai_rx_diagnosis", draft_id=draft.id)

    # ------------------------
    # Context
    # ------------------------
    context = {
        "draft": draft,
        "patient": patient,
        "findings": draft.data.get("findings", ""),
        "visit_docs": visit_docs,
        "latest_vitals": latest_vitals,
        "vitals_block": vitals_block,
    }

    return render(request, "prescription/ai/findings.html", context)


# ---------------------------------------------------------
# 6. STEP-4: DIAGNOSIS
# ---------------------------------------------------------

@login_required
def edit_diagnosis(request, draft_id):
    """
    Step 4 of the AI Rx wizard: Doctor enters diagnosis.
    Next step depends on hospital.ai_enabled.
    """
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    # Only the same doctor can access
    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    patient_id = draft.data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient in draft"}, status=400)

    patient = Patient.objects.get(pk=patient_id)
    existing_diagnosis = draft.data.get("diagnosis", "")

    if request.method == "POST":
        diagnosis_text = request.POST.get("diagnosis", "").strip()

        draft.data["diagnosis"] = diagnosis_text
        draft.current_step = "diagnosis"
        draft.save(update_fields=["data", "current_step", "updated_at"])

        # -------------------------------
        # 🔥 AI ON → Go to AI Suggestions
        # 🔥 AI OFF → Go to manual prescription
        # -------------------------------
        if draft.hospital.ai_enabled:
            return redirect("ai_rx_ai_suggestions", draft_id=draft.id)
        else:
            return redirect("ai_rx_prescription_manual", draft_id=draft.id)

    context = {
        "draft": draft,
        "diagnosis": existing_diagnosis,
        "patient": patient,
    }

    return render(request, "prescription/ai/diagnosis.html", context)



# ---------------------------------------------------------
# 7. STEP-5: AI Suggestions
# ---------------------------------------------------------


AI_MODEL = "gpt-4o-mini"   # or your selected lightweight model





def get_client():
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        logger.error("OpenAI API key missing in settings.")
        raise RuntimeError("OpenAI API key missing. Configure environment variable OPENAI_API_KEY.")
    return OpenAI(api_key=api_key)



@login_required
def ai_suggestions(request, draft_id):

    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    # -------------------------------------------------------
    # 🚫 If AI is OFF → Skip this view entirely 
    # -------------------------------------------------------
    if not draft.hospital.ai_enabled:
        return redirect("ai_rx_prescription", draft_id=draft.id)

    # Only assigned doctor can access
    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    doctor = request.user.doctor
    hospital = doctor.hospital

    # Load patient
    patient_id = draft.data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient in draft"}, status=400)

    patient = Patient.objects.get(pk=patient_id)

    # -------------------------------------------------------
    # 🧮 Check AI balance – do NOT call if empty
    # -------------------------------------------------------
    ai_balance = getattr(hospital, "ai_balance", 0)

    if ai_balance <= 0:
        messages.warning(
            request,
            "No AI credits remaining. You may continue manually."
        )
        return render(
            request,
            "prescription/ai/ai_suggestions.html",
            {
                "draft": draft,
                "ai_enabled": False,
                "ai_data": None,
            },
        )

    # -------------------------------------------------------
    # Load existing draft data
    # -------------------------------------------------------
    h   = draft.data.get("history", "")
    s   = draft.data.get("symptoms", "")
    f   = draft.data.get("findings", "")
    dgn = draft.data.get("diagnosis", "")

    ai_data = draft.data.get("ai_notes", {})

    # -------------------------------------------------------
    # Refresh or first-time → Call the model
    # -------------------------------------------------------
    if request.GET.get("refresh") == "1" or not ai_data:

        prompt = f"""
You are a clinical assistant helping a doctor.
Summarize all information and provide DIFFERENTIALS and SUGGESTIONS but DO NOT DIAGNOSE with certainty.

Input:
History: {h}
Symptoms: {s}
Findings: {f}
Diagnosis (provisional): {dgn}

Provide output in JSON:
{{
  "summary": "...",
  "differential_diagnoses": ["...", "..."],
  "suggested_tests": ["...", "..."],
  "red_flags": ["...", "..."],
  "notes": ["...", "..."]
}}
"""

        try:
            client = get_client()
            res = client.chat.completions.create(
                model=AI_MODEL,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            ai_data = json.loads(res.choices[0].message.content)

        except Exception as e:
            messages.error(request, f"AI suggestions unavailable: {e}")
            ai_data = None

        draft.data["ai_notes"] = ai_data
        draft.current_step = "ai_suggestions"
        draft.save(update_fields=["data", "current_step", "updated_at"])

    # -------------------------------------------------------
    # Render page
    # -------------------------------------------------------
    return render(
        request,
        "prescription/ai/ai_suggestions.html",
        {
            "draft": draft,
            "ai_data": ai_data,
            "ai_enabled": True,
        },
    )


@login_required
def autosave_draft(request, draft_id):
    """
    AJAX autosave endpoint. Expects {field: "history", value: "..."}.
    """
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    field = request.POST.get("field")
    value = request.POST.get("value", "").strip()

    if not field:
        return JsonResponse({"error": "Missing field"}, status=400)

    draft.data[field] = value
    draft.save(update_fields=["data", "updated_at"])

    return JsonResponse({"status": "ok"})

@login_required
def ai_discard(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    if draft.doctor != request.user.doctor:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    draft.delete()
    messages.info(request, "Draft discarded.")

    return redirect("prescription")



# ---------------------------------------------------------
# STEP 8: AI-Assisted Prescription Suggestion
# ---------------------------------------------------------
@login_required
def ai_prescription(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    # Only the assigned doctor can access
    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # If AI disabled → load manual screen
    if not draft.data.get("ai_enabled", True):
        return ai_prescription_manual(request, draft)

    # ---------------------------------------------------------
    # EXISTING AI-enabled prescription logic (unchanged)
    # ---------------------------------------------------------
    patient_id = draft.data.get("patient_id")
    patient = Patient.objects.get(pk=patient_id)

    h = draft.data.get("history", "")
    s = draft.data.get("symptoms", "")
    f = draft.data.get("findings", "")
    dgn = draft.data.get("diagnosis", "")

    existing_drugs = [
        d.get("drug_name", "").lower()
        for d in draft.data.get("drugs", [])
    ]

    ai_drugs = draft.data.get("ai_drug_suggestions", {})

    # Generate suggestions if needed
    if request.GET.get("refresh") == "1" or not ai_drugs:

        prompt = f"""
You are a medical assistant. Suggest medications ONLY as options...
(unchanged)
"""

        try:
            client = get_client()
            response = client.chat.completions.create(
                model=AI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            ai_drugs = json.loads(response.choices[0].message.content)
        except Exception as e:
            ai_drugs = {"error": str(e)}

        draft.data["ai_drug_suggestions"] = ai_drugs
        draft.current_step = "ai_prescription"
        draft.save()

    return render(
        request,
        "prescription/ai/ai_prescription.html",
        {"draft": draft, "ai_drugs": ai_drugs, "patient": patient},
    )


@require_POST
@login_required
def ai_add_drug(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

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
    }

    return render(request, "prescription/ai/ai_review.html", context)



@login_required
def ai_discard(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    if draft.doctor != request.user.doctor:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    master = PrescriptionMaster.objects.filter(
        draft_id=draft.id, draft=True
    ).first()

    if master:
        master.delete()  # cascades to PrescriptionDetails

    draft.delete()

    messages.info(request, "Draft discarded.")
    return redirect("prescription")




@require_POST
@login_required
def ai_finalize(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    data = draft.data
    drugs = data.get("drugs", []) or []

    # Ensure valid drug entries exist
    valid_drugs = [d for d in drugs if (d.get("drug_name") or "").strip()]
    if not valid_drugs:
        return JsonResponse({"error": "No valid medicines added."}, status=400)

    patient_id = data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient."}, status=400)

    patient = get_object_or_404(Patient, pk=patient_id)
    doctor = draft.doctor
    hospital = draft.hospital

    

    # Try reading appointment_id from draft first
    appointment = None
    appt_id = data.get("appointment_id")

    if appt_id:
        appointment = AppointmentDetails.objects.filter(pk=appt_id).first()

    # If draft does NOT contain appointment → find today's appointment for this patient + doctor
    if not appointment:
        appointment = AppointmentDetails.objects.filter(
            patient=patient,
            doctor=doctor,
            hospital=hospital,
            appointment_on=date.today(),
            completed__in=[
                AppointmentDetails.STATUS_REGISTERED,
                AppointmentDetails.STATUS_IN_QUEUE
            ]
        ).order_by("-appoint_id").first()


    try:
        with transaction.atomic():

            # -------- Create PrescriptionMaster --------
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

            # -------- Create PrescriptionDetails --------
            # ----------------------------
            # NORMALIZE FOOD ORDER
            # ----------------------------
            
            for d in valid_drugs:
                # -------- Normalize food --------
                raw_food = (d.get("food_order") or "").lower().strip()
                if "before" in raw_food:
                    food = "before"
                else:
                    food = "after"  # default

                # -------- Normalize drug name --------
                name = (d.get("drug_name") or "").strip().title()
                if not name:
                    continue

                # -------- Save prescription detail --------
                PrescriptionDetails.objects.create(
                    prescription=master,
                    hospital=hospital,
                    drug_name=name,
                    composition=(d.get("composition") or "").strip(),
                    dosage=(d.get("dosage") or "").strip(),
                    frequency=(d.get("frequency") or "").strip(),
                    duration=(d.get("duration") or "").strip(),
                    food_order=food,
                )

                # -------- Learn doctor usage (Docon logic) --------
                obj, _ = DoctorDrugUsage.objects.get_or_create(
                    doctor=doctor,
                    drug_name=name
                )

                DoctorDrugUsage.objects.filter(pk=obj.pk).update(
                    usage_count=F("usage_count") + 1
                )


            # -------- Update appointment status --------
            
            if appointment:
                # Mark as completed
                appointment.completed = AppointmentDetails.STATUS_DONE

                # Native datetime (USE_TZ=False is safe)
                appointment.completed_at = datetime.now()

                appointment.save(update_fields=["completed", "completed_at"])

            # -------- Finalize the draft --------
            draft.finalized = True
            draft.current_step = "finalized"
            draft.save(update_fields=["finalized", "current_step", "updated_at"])

    except Exception as e:
        return JsonResponse({"error": f"Error finalizing prescription: {str(e)}"}, status=500)

    return JsonResponse({
        "redirect": reverse("ai_prescription_print_builder", args=[master.id])
    })






@login_required
def ai_prescription_manual(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, pk=draft_id, finalized=False)

    if draft.doctor != getattr(request.user, "doctor", None):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    doctor = request.user.doctor
    hospital = doctor.hospital

    # Patient
    patient_id = draft.data.get("patient_id")
    patient = get_object_or_404(Patient, pk=patient_id)

    # Prefill notes (display only)
    initial_data = {
        "notes_history":  draft.data.get("history", ""),
        "notes_symptoms": draft.data.get("symptoms", ""),
        "notes_findings": draft.data.get("findings", ""),
        "general_advice": draft.data.get("general_advice", ""),
        "diagnosis":      draft.data.get("diagnosis", ""),
    }

    if request.method == "POST":
        # --- 1. Read general advice from textarea ---
        general_advice_text = (request.POST.get("general_advice") or "").strip()
        draft.data["general_advice"] = general_advice_text

        # --- 2. Extract drug rows manually from POST ---
        total = int(request.POST.get("details-TOTAL_FORMS", 0) or 0)
        meds = []

        for i in range(total):
            prefix = f"details-{i}"

            # Deleted row?
            if request.POST.get(f"{prefix}-DELETE"):
                continue

            name = (request.POST.get(f"{prefix}-drug_name") or "").strip()
            if not name:
                # skip completely blank rows
                continue

            meds.append({
                "drug_name":  name,
                "composition": (request.POST.get(f"{prefix}-composition") or "").strip(),
                "dosage":      (request.POST.get(f"{prefix}-dosage") or "").strip(),
                "frequency":   (request.POST.get(f"{prefix}-frequency") or "").strip(),
                "duration":    (request.POST.get(f"{prefix}-duration") or "").strip(),
                "food_order":  (request.POST.get(f"{prefix}-food_order") or "").strip(),
            })

        if not meds:
            # Rebuild formset from POST so user input is preserved
            initial_rows = []
            for i in range(total):
                prefix = f"details-{i}"
                initial_rows.append({
                    "drug_name":  request.POST.get(f"{prefix}-drug_name", ""),
                    "composition": request.POST.get(f"{prefix}-composition", ""),
                    "dosage":      request.POST.get(f"{prefix}-dosage", ""),
                    "frequency":   request.POST.get(f"{prefix}-frequency", ""),
                    "duration":    request.POST.get(f"{prefix}-duration", ""),
                    "food_order":  request.POST.get(f"{prefix}-food_order", ""),
                })

            form = PrescriptionMasterForm(initial=initial_data, user=request.user)
            formset = ManualDetailFormSet(
                initial=initial_rows or [{}],
                prefix="details",
                form_kwargs={"user": request.user},
            )

            return render(request, "prescription/ai/ai_prescription_manual.html", {
                "draft": draft,
                "patient": patient,
                "form": form,
                "formset": formset,
                "error": "Please add at least one medicine.",
            })

        # --- 3. Save to draft and go to review ---
        draft.data["drugs"] = meds
        draft.current_step = "prescription"
        draft.save(update_fields=["data", "current_step", "updated_at"])

        return redirect("ai_rx_review", draft_id=draft.id)

    # ---------------------------
    # GET — LOAD SAVED DRUGS
    # ---------------------------
    saved_rows = draft.data.get("drugs", []) or [{}]

    form = PrescriptionMasterForm(initial=initial_data, user=request.user)
    formset = ManualDetailFormSet(
        initial=saved_rows,
        prefix="details",
        form_kwargs={"user": request.user},
    )

    return render(request, "prescription/ai/ai_prescription_manual.html", {
        "draft": draft,
        "patient": patient,
        "form": form,
        "formset": formset,
    })


@login_required
def ai_prescription_print_builder(request, rx_id):
    """
    Print view specifically for AI-generated prescriptions.
    """
    master = get_object_or_404(
        PrescriptionMaster.objects.select_related("doctor", "patient", "hospital", "appointment"),
        pk=rx_id,
    )

    details = PrescriptionDetails.objects.filter(prescription=master)

    return render(
        request,
        "prescription/print/final_prescription.html",
        {"master": master, "details": details},
    )


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
