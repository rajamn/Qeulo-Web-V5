# visit_workspace/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.urls import reverse

from appointments.models import AppointmentDetails
from prescription.models import PrescriptionMaster, PrescriptionDetails
from patients.models import Patient
from .models import VisitDocument, VisitNote, FavoriteDrug, PrescriptionTemplate
from .utils.summary_generator import generate_summary
from .utils.ai_summary import generate_ai_summary
from .utils.local_summary import generate_local_summary  
import json


# ----------------------------------------------------
# 1. Visit Workspace (Doctor Screen)
# ----------------------------------------------------
@login_required
def visit_workspace_view(request, patient_id):
    hospital = request.user.hospital

    # Get the patient
    patient = get_object_or_404(
        Patient,
        id=patient_id,
        hospital=hospital
    )

    # Latest appointment (if any)
    appointment = (
        AppointmentDetails.objects
        .filter(patient=patient, hospital=hospital)
        .order_by("-appoint_id")   # correct PK
        .first()
    )

    doctor = appointment.doctor if appointment else None

    prescription = None
    is_edit = False

    if appointment:
        prescription, created = PrescriptionMaster.objects.get_or_create(
            appointment=appointment,
            defaults={
                "patient": patient,
                "doctor": doctor,
                "hospital": hospital,
            },
        )
        is_edit = not created

    context = {
        "patient": patient,
        "appointment": appointment,
        "doctor": doctor,
        "hospital": hospital,
        "prescription": prescription,
        "prescription_details": prescription.details.all() if prescription else [],
        "visit_notes": VisitNote.objects.filter(patient=patient, hospital=hospital),
        "visit_docs": VisitDocument.objects.filter(patient=patient, hospital=hospital),
        "favorite_drugs": FavoriteDrug.objects.filter(hospital=hospital, doctor=doctor) if doctor else [],
        "templates": PrescriptionTemplate.objects.filter(hospital=hospital, doctor=doctor) if doctor else [],
        "is_edit": is_edit,
    }

    return render(request, "visit_workspace/doctor_visit_workspace.html", context)

# ----------------------------------------------------
# 2. Upload Document (Browser OCR entry point)
# ----------------------------------------------------
@login_required
def upload_document(request, pk):
    hospital = request.user.hospital
    patient = get_object_or_404(Patient, id=pk, hospital=hospital)

    return render(request, "visit_workspace/upload_form.html", {
        "patient": patient,
        "hospital": hospital,
    })


# ----------------------------------------------------
# 3. OCR Text Upload API (browser → Django)
# ----------------------------------------------------


@login_required
@require_POST
def ocr_text_upload(request, pk):
    hospital = request.user.hospital
    patient = get_object_or_404(Patient, id=pk, hospital=hospital)

    data = json.loads(request.body)
    text = data.get("text", "")
    doc_type = data.get("doc_type", "OTHER")
    desc = data.get("description", "")

    # LOCAL summary (fast + improved)
    summary_data = generate_local_summary(text, doc_type)

    doc = VisitDocument.objects.create(
        hospital=hospital,
        patient=patient,
        doc_type=doc_type,
        description=desc,
        ocr_text=text,
        summary_data=summary_data,
        uploaded_by=request.user,
    )

    return JsonResponse({
        "redirect_url": reverse("visit_workspace:summary", args=[doc.id])
    })


# ----------------------------------------------------
# 4. Process Document = Show Summary Screen
# ----------------------------------------------------
@login_required
def process_document(request, doc_id):
    return redirect("visit_workspace:summary", doc_id=doc_id)

# ----------------------------------------------------
# 5. Patient History (All Docs + Notes)
# ----------------------------------------------------
@login_required
def patient_history(request, pk):
    hospital = request.user.hospital

    patient = get_object_or_404(
        Patient,
        pk=pk,
        hospital=hospital
    )

    documents = (
        VisitDocument.objects.filter(patient=patient, hospital=hospital)
        .order_by("-created_at")
    )

    notes = (
        VisitNote.objects.filter(patient=patient, hospital=hospital)
        .order_by("-created_at")
    )

    # Helper to detect valid AI summary
    def has_valid_ai(data):
        if not data or not isinstance(data, dict):
            return False
        return any([
            data.get("impression"),
            data.get("key_findings"),
            data.get("recommendations"),
            data.get("structured_values"),
            data.get("abnormal_values"),
        ])

    # Attach flag to each document
    for d in documents:
        d.has_valid_ai = has_valid_ai(d.ai_summary_data)

    context = {
        "patient": patient,
        "documents": documents,
        "notes": notes,
    }

    return render(request, "visit_workspace/history.html", context)




@login_required
def summary_view(request, doc_id):
    hospital = request.user.hospital
    doc = get_object_or_404(VisitDocument, id=doc_id, hospital=hospital)

    force_retry = request.GET.get("retry") == "1"

    # If AI summary already exists and user is NOT forcing retry
    if doc.ai_summary_data and not force_retry:
        summary = doc.ai_summary_data
        is_ai = True
        error_message = None
    else:
        # RUN AI
        try:
            json_data, bullet_summary, clinical_notes = generate_ai_summary(doc.ocr_text)

            # Convert AI output to one consistent structure for template
            summary = {
                "key_findings": bullet_summary,
                "impression": json_data.get("diagnosis") or "",
                "recommendations": json_data.get("notes") or "",
                "free_summary": clinical_notes,
                "structured_values": json_data.get("labs") or [],
                "abnormal_values": [],
            }

            is_ai = True
            error_message = None

        except Exception as e:
            print("AI Summary Error:", e)
            # Fallback
            summary = {
                "key_findings": "",
                "impression": "",
                "recommendations": "",
                "free_summary": doc.ocr_text,
                "structured_values": [],
                "abnormal_values": [],
            }
            is_ai = False
            error_message = "AI Summary unavailable."

        # Save the normalized summary structure
        doc.ai_summary_data = summary
        doc.save(update_fields=["ai_summary_data"])

    return render(request, "visit_workspace/summary.html", {
        "patient": doc.patient,
        "doc": doc,
        "summary": summary,
        "is_ai": is_ai,
        "error_message": error_message,
    })

# ----------------------------------------------------
# 6. Save summary as VisitNote entries
# ----------------------------------------------------
@login_required
@require_POST
def save_summary(request, doc_id):
    hospital = request.user.hospital
    doc = get_object_or_404(VisitDocument, id=doc_id, hospital=hospital)

    selected_sections = request.POST.getlist("save_sections")
    summary = doc.ai_summary_data or {}

    def save_section(key, note_type):
        if key in selected_sections:
            text = (summary.get(key) or "").strip()
            if text:
                VisitNote.objects.create(
                    hospital=hospital,
                    patient=doc.patient,
                    appointment=doc.appointment,
                    note_type=note_type,
                    text=text,
                    source="AI",
                    created_by=request.user,
                )

    # Map summary keys → VisitNote note_type
    save_section("free_summary", "CLINICAL")
    save_section("key_findings", "AI_SUMMARY")
    save_section("impression", "AI_SUMMARY")
    save_section("recommendations", "AI_SUMMARY")

    messages.success(request, "Selected summary sections saved to Visit Notes.")
    return redirect("visit_workspace:patient_history", pk=doc.patient.id)