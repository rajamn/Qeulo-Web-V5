# vitals/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_GET

from core.models import HospitalUser
from patients.models import Patient
from appointments.models import AppointmentDetails
from .forms import PatientVitalForm
from .models import PatientVital


def _patient_detail_url(patient):
    """
    Try common patient-detail route names. Return None if none resolve.
    """
    # Try with patient_id kwarg
    for name in ("patients:patient_detail", "patients:detail", "patients:view"):
        try:
            return reverse(name, kwargs={"patient_id": patient.pk})
        except NoReverseMatch:
            pass
    # Try with pk kwarg
    for name in ("patients:patient_detail", "patients:detail", "patients:view"):
        try:
            return reverse(name, kwargs={"pk": patient.pk})
        except NoReverseMatch:
            pass
    return None


def _resolve_latest_vitals(hospital, patient, appointment=None):
    """
    Latest appointment-specific vitals if present, else latest overall.
    """
    qs = (PatientVital.objects
          .filter(hospital=hospital, patient=patient)
          .select_related("recorded_by")
          .order_by("-recorded_at"))
    if appointment:
        v = qs.filter(appointment=appointment).first()
        if v:
            return v
    return qs.first()


@login_required
def create_vitals(request, patient_id, appointment_id=None):
    hospital = request.user.hospital
    patient = get_object_or_404(Patient, pk=patient_id, hospital=hospital)

    appointment = None
    if appointment_id:
        appointment = get_object_or_404(
            AppointmentDetails, pk=appointment_id, hospital=hospital, patient=patient
        )

    # 1) Edit if this appointment already has vitals
    appt_vitals = None
    if appointment:
        appt_vitals = (PatientVital.objects
                       .filter(hospital=hospital, patient=patient, appointment=appointment)
                       .order_by("-recorded_at")
                       .first())

    # 2) Latest overall for convenience prefill when creating new
    latest_any = (PatientVital.objects
                  .filter(hospital=hospital, patient=patient)
                  .order_by("-recorded_at")
                  .first())

    if request.method == "POST":
        form = PatientVitalForm(request.POST, instance=appt_vitals if appt_vitals else None)
        if form.is_valid():
            with transaction.atomic():
                vitals: PatientVital = form.save(commit=False)
                vitals.hospital = hospital
                vitals.patient = patient
                vitals.appointment = appointment

                # recorded_by resolution
                if isinstance(request.user, HospitalUser):
                    vitals.recorded_by = request.user
                else:
                    vitals.recorded_by = HospitalUser.objects.filter(
                        user=request.user, hospital=hospital
                    ).first()

                vitals.save()

            messages.success(request, "Vitals saved successfully.")

            # ✅ Prefer explicit next param (e.g., from Prescription screen)
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                if "vitals_updated" not in next_url:
                    sep = '&' if '?' in next_url else '?'
                    next_url = f"{next_url}{sep}vitals_updated=1"
                return redirect(next_url)

            # 🔁 Fallback: patient detail → dashboard → /patients/
            dest = _patient_detail_url(patient)
            if dest:
                return redirect(dest)
            try:
                return redirect("patients:dashboard")
            except NoReverseMatch:
                return redirect("/patients/")

        else:
            messages.error(request, "Please fix the errors below.")
    else:
        # GET: form with data if available
        if appt_vitals:
            form = PatientVitalForm(instance=appt_vitals)  # BMI prefilled in form __init__
        elif latest_any:
            initial = {
                "height_cm":     latest_any.height_cm,
                "weight_kg":     latest_any.weight_kg,
                "temperature_c": latest_any.temperature_c,
                "bp_systolic":   latest_any.bp_systolic,
                "bp_diastolic":  latest_any.bp_diastolic,
                "spo2_percent":  latest_any.spo2_percent,
                "pulse_bpm":     latest_any.pulse_bpm,
                "notes":         latest_any.notes,
                "bmi":           latest_any.bmi,  # display-only field
            }
            form = PatientVitalForm(initial=initial)
        else:
            form = PatientVitalForm()

    return render(request, "vitals/vitals_form.html", {
        "hospital": hospital,
        "patient": patient,
        "appointment": appointment,
        "form": form,
    })


# ---------- Lightweight JSON API for live dropdown updates (optional) ----------

@login_required
@require_GET
def api_latest_vitals(request):
    hospital = request.user.hospital
    pid = request.GET.get("patient_id")
    aid = request.GET.get("appointment_id")

    try:
        patient = Patient.objects.get(pk=pid, hospital=hospital)
    except (Patient.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "patient not found"}, status=404)

    appt = None
    if aid:
        appt = AppointmentDetails.objects.filter(
            pk=aid, hospital=hospital, patient=patient
        ).first()

    v = _resolve_latest_vitals(hospital, patient, appt)
    if not v:
        return JsonResponse({"ok": True, "data": None})

    data = {
        "recorded_at": v.recorded_at.strftime("%b %d, %Y %H:%M"),
        "recorded_by": getattr(v.recorded_by, "user_name", None),
        "height_cm": str(v.height_cm),
        "weight_kg": str(v.weight_kg),
        "bmi": str(v.bmi),
        "temperature_c": str(v.temperature_c),
        "bp": f"{v.bp_systolic}/{v.bp_diastolic}",
        "spo2_percent": v.spo2_percent,
        "pulse_bpm": v.pulse_bpm,
        "notes": v.notes or "",
    }
    return JsonResponse({"ok": True, "data": data})
