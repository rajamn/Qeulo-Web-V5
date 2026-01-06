from django.shortcuts       import render, redirect, get_object_or_404
from django.http            import JsonResponse, HttpResponse
from django.contrib import messages
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required, user_passes_test
from core.decorators import doctor_required
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
# from django.forms import modelformset_factory
from .forms import PrescriptionMasterForm, PrescriptionDetailForm
from django.db import transaction
from appointments.models import AppointmentDetails
from datetime import date
import json
from drugs.models import UserPreset, Drug
from drugs.forms import DetailInlineFormSet
from drugs.constants import PRESETS as GLOBAL_PRESETS
from .models import PrescriptionMaster, PrescriptionDetails, AppointmentDetails
from django.core.exceptions import ValidationError
import logging
import os
from io import BytesIO
from xhtml2pdf import pisa
from doctors.models import Doctor
from drugs.models import Drug, DrugTemplate, DrugTemplateItem
from django.views.decorators.http import require_POST
from django.http import JsonResponse, Http404
from django.db.models import Q, Value, CharField

from django.urls import reverse, NoReverseMatch
from vitals.models import PatientVital
from django.http import HttpResponseForbidden
from core.utils.roles import user_has_role


# DetailModelFormSet = modelformset_factory(
#     PrescriptionDetails,
#     form=PrescriptionDetailForm,
#     extra=1,
#     can_delete=True
#  )

# prescription/views_regular.py 

@login_required
def prescription_entry(request):
    user = request.user

    # 1. Identify doctors *only* — use your real test here
    is_doctor = request.user.doctor_id is not None

    if is_doctor:
        # send doctors to the write screen
        return redirect(reverse('prescribe_patient'))
    else:
        # send everyone else to the view-list screen
        return redirect(reverse('prescription:view_prescriptions'))




def _resolve_latest_vitals(hospital, patient, appointment=None):
    """
    If there are vitals for this appointment, return the latest of those.
    Otherwise return the patient's latest vitals overall.
    """
    qs = (PatientVital.objects
          .filter(hospital=hospital, patient=patient)
          .select_related('recorded_by')
          .order_by('-recorded_at'))
    if appointment:
        v = qs.filter(appointment=appointment).first()
        if v:
            return v
    return qs.first()


@login_required
@doctor_required
def prescribe_patient(request):
    appointment_id = request.GET.get('appointment')
    completed_id   = request.GET.get('completed_patient')
    appt_pk        = appointment_id or completed_id

    # 1) Patient header info
    patient_info = {'name': None, 'gender': None, 'age_years': None, 'age_months': None, 'source': None}
    appt = None
    if appt_pk:
        try:
            appt = AppointmentDetails.objects.select_related('patient').get(pk=int(appt_pk))
            p = appt.patient
            patient_info.update({
                'name': p.patient_name,
                'gender': getattr(p, 'gender', ''),
                'age_years': getattr(p, 'age_years', 0),
                'age_months': getattr(p, 'age_months', 0),
                'source': 'Completed' if completed_id else 'Queued',
            })
        except AppointmentDetails.DoesNotExist:
            appt = None

    # 2) If a prescription already exists for this appointment, edit the latest
    instance = None
    if appt_pk:
        instance = (
            PrescriptionMaster.objects
            .filter(appointment_id=appt_pk)
            .order_by('-prescribed_on')
            .first()
        )

    # 3) Initials for tag-like fields
    initial_data = {'appointment': appointment_id, 'completed_patient': completed_id}
    if instance:
        for field in ('notes_history','notes_symptoms','notes_findings','general_advice'):
            raw = getattr(instance, field) or ''
            initial_data[field] = [v.strip() for v in raw.split(',') if v.strip()]

    # 4) Master form
    master_data = request.POST if request.method == 'POST' else None
    prescription_form = PrescriptionMasterForm(
        master_data,
        instance=instance,
        initial=initial_data,
        user=request.user,
    )

    # Choose a parent to display rows against when not yet saved
    parent_for_display = instance or PrescriptionMaster()

    # 5) Presets (unchanged)
    presets = {
        'notes_history':   [p.value for p in UserPreset.objects.filter(user=request.user, field_name='notes_history')],
        'notes_symptoms':  [p.value for p in UserPreset.objects.filter(user=request.user, field_name='notes_symptoms')],
        'notes_findings':  [p.value for p in UserPreset.objects.filter(user=request.user, field_name='notes_findings')],
        'general_advice':  [p.value for p in UserPreset.objects.filter(user=request.user, field_name='general_advice')],
    }
    for key in ('dosage', 'frequency', 'duration', 'food_order'):
        user_vals = list(UserPreset.objects.filter(user=request.user, field_name=key).values_list('value', flat=True))
        presets[key] = user_vals + GLOBAL_PRESETS.get(key, [])

    
    # --- Vitals for dropdown ---
    latest_vitals = None
    vitals_url = None
    if appt:
        # helper defined below
        latest_vitals = _resolve_latest_vitals(request.user.hospital, appt.patient, appt)
        try:
            vitals_url = reverse("vitals:create_for_appointment",
                                 kwargs={"patient_id": appt.patient_id, "appointment_id": appt.pk})
        except NoReverseMatch:
            # fallback to patient-scoped create if appointment route is absent
            try:
                vitals_url = reverse("vitals:create_for_patient",
                                     kwargs={"patient_id": appt.patient_id})
            except NoReverseMatch:
                vitals_url = None
    
    # 6) Flow control
    if request.method == 'GET':
        # Unbound formset for display
        detailformset = DetailInlineFormSet(
            instance=parent_for_display,
            prefix='details',
            form_kwargs={'user': request.user},
        )

    else:  # POST
        action = request.POST.get('action', 'save')

        if not prescription_form.is_valid():
            messages.error(request, "Please correct the errors in the prescription header.")
            # Bind formset to a display parent so entered rows re-render with errors
            detailformset = DetailInlineFormSet(
                request.POST,
                instance=parent_for_display,
                prefix='details',
                form_kwargs={'user': request.user},
            )

        else:
            try:
                with transaction.atomic():
                    master = prescription_form.save(commit=False)
                    master.hospital = request.user.hospital
                    master.doctor   = request.user.doctor
                    # --- Normalize TomSelect notes fields (works for input OR select[multiple]) ---
                    NOTE_FIELDS = ('notes_history', 'notes_symptoms', 'notes_findings', 'general_advice')

                    def _join_notes(req, form, field):
                        val = form.cleaned_data.get(field, None)

                        # If the form field returns a list/tuple (e.g., MultipleChoice), join it
                        if isinstance(val, (list, tuple)):
                            return ", ".join(v.strip() for v in val if v and str(v).strip())

                        # If it's a plain string from a CharField, just strip it
                        if isinstance(val, str):
                            return val.strip()

                        # Fallback: read raw POST (handles <select multiple> reliably)
                        lst = req.POST.getlist(field)  # multiple values
                        if lst:
                            return ", ".join(v.strip() for v in lst if v and str(v).strip())

                        return (req.POST.get(field) or "").strip()

                    
                    appt_sel = (prescription_form.cleaned_data.get('appointment')
                                or prescription_form.cleaned_data.get('completed_patient'))
                    if not appt_sel:
                        raise ValidationError("Select an active appointment or a completed patient.")

                    master.appointment_id = appt_sel.pk
                    master.patient        = appt_sel.patient
                    
                    print(f"NOTES:, {master.notes_history}, {master.notes_symptoms}, {master.notes_findings}, {master.general_advice}")
                    master.save()  # ensure PK

                    # Build & validate the inline formset against the saved parent
                    detailformset = DetailInlineFormSet(
                        request.POST,
                        instance=master,
                        prefix='details',
                        form_kwargs={'user': request.user},
                    )

                    if not detailformset.is_valid():
                        # Optional: log details for quick pinpointing
                        print("Formset errors:", [f.errors for f in detailformset.forms],
                              "Non-form:", detailformset.non_form_errors())
                        raise ValidationError("Please correct the errors in medicine rows.")

                    details = detailformset.save(commit=False)

                    # Save details; ignore fully-empty rows defensively
                    for d in details:
                        if not any([
                            getattr(d, 'drug_name', ''), getattr(d, 'dosage', ''),
                            getattr(d, 'frequency', ''), getattr(d, 'duration', ''),
                            getattr(d, 'food_order', '')
                        ]):
                            continue
                        d.hospital = request.user.hospital
                        if d.drug_name:
                            d.drug_name = d.drug_name.strip()
                        d.save()

                    # Handle deletes
                    for obj in detailformset.deleted_objects:
                        obj.delete()

                    if hasattr(detailformset, 'save_m2m'):
                        detailformset.save_m2m()

                    # Mark appointment completed if this is the first Rx for this appt
                    if appointment_id and not instance and appt:
                        appt.completed = AppointmentDetails.STATUS_DONE
                        appt.save(update_fields=['completed'])

                    # Call next in queue
                    today = date.today()
                    next_appt = AppointmentDetails.objects.filter(
                        hospital=request.user.hospital,
                        doctor=request.user.doctor,
                        appointment_on=today,
                        completed=AppointmentDetails.STATUS_IN_QUEUE,
                        called=False
                    ).order_by('que_pos').first()
                    if next_appt:
                        next_appt.called = True
                        next_appt.save(update_fields=['called'])

            except ValidationError as e:
                messages.error(request, str(e))
            else:
                if action == "save_print":
                    return redirect("prescription_print_builder", prescription_id=master.pk)
                messages.success(request, "Prescription saved successfully.")
                return redirect('prescription_success')


    
    return render(request, 'prescription/prescribe.html', {
        'prescription_form': prescription_form,
        'detailformset':     detailformset,
        'presets':           json.dumps(presets),
        'patient_info':      patient_info,
        'latest_vitals':     latest_vitals,
        'vitals_url':        vitals_url,
    })


# prescription/views.py  (where you render the template you pasted)

def _resolve_latest_vitals(hospital, patient, appointment=None):
    qs = PatientVital.objects.filter(hospital=hospital, patient=patient)
    if appointment:
        v = qs.filter(appointment=appointment).order_by('-recorded_at').first()
        if v:
            return v
    return qs.order_by('-recorded_at').first()


@login_required
def get_patient_details(request):
    appt_id = request.GET.get('appointment')
    data = {
        "patient_name": None,
        "age_years": None,
        "age_months": None,
        "gender": None,
        "source": None,
    }
    if appt_id:
        try:
            appt = AppointmentDetails.objects.select_related("patient").get(pk=int(appt_id))
            patient = appt.patient
            # Name
            data["patient_name"] = patient.patient_name
            # Gender (assuming a .gender field on Patient)
            data["gender"] = getattr(patient, "gender", "")
            # Source comes from appointment
            data["source"] = getattr(appt, "source", "")
            # Calculate age if DOB exists, else fallback to age fields
            dob = getattr(patient, "date_of_birth", None)
            if dob:
                today = date.today()
                years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                months = (today.month - dob.month) % 12
                data["age_years"] = years
                data["age_months"] = months
            else:
                data["age_years"] = getattr(patient, "age_years", None)
                data["age_months"] = getattr(patient, "age_months", None)
        except (AppointmentDetails.DoesNotExist, ValueError):
            pass

    return JsonResponse(data)

@login_required
def save_user_preset(request):
    """AJAX endpoint: Save a new user preset for notes fields"""
    data = json.loads(request.body)
    field = data.get('field_name')
    value = data.get('value')
    if field and value:
        UserPreset.objects.get_or_create(user=request.user,
                                         field_name=field,
                                         value=value)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)

@login_required
def notes_autocomplete(request):
    """AJAX endpoint: Return matching user presets for a given notes field"""
    # Expected query params: ?field=notes_history&term=his
    field_name = request.GET.get('field') or ''
    term = request.GET.get('term', '')
    # Filter presets that contain the term
    qs = UserPreset.objects.filter(
        user=request.user,
        field_name=field_name,
        value__icontains=term
    ).values_list('value', flat=True).distinct()
    # Build the JSON response for jQuery UI Autocomplete
    suggestions = [{'label': v, 'value': v} for v in qs]
    return JsonResponse(suggestions, safe=False)

@login_required
def drug_autocomplete(request):
    term = request.GET.get('term', '')
    qs = Drug.objects.filter(name__icontains=term)[:20]
    data = [{
        "label": d.name,
        "value": d.name,
        "composition": d.composition or "",
        # optional defaults:
        "dosage": getattr(d, "default_dosage", "") or "",
        "frequency": getattr(d, "default_frequency", "") or "",
        "duration": getattr(d, "default_duration", "") or "",
        "food_order": getattr(d, "default_food_order", "") or "",
    } for d in qs]
    return JsonResponse(data, safe=False)


@login_required
def prescription_success(request):
    return render(request, 'prescription/success.html')



from django.http import HttpResponseGone
from django.shortcuts import redirect

def prescription_pdf(request, prescription_id):
    # return HttpResponseGone("This endpoint has been removed. Use print view.")
    return redirect("prescription_print_builder", prescription_id=prescription_id)



@login_required
# allow only staff users (or adjust to your “Receptionist” group)
def receptionist_or_admin(user):
    return user.is_staff or user.is_superuser


@login_required
def view_prescriptions(request):
    """
    Read-only prescription list for NON-doctor users
    (Reception, Accountant, Hospital Admin).
    """

    user = request.user

    # ---- 1. Hard block doctors ----
    if user.role and user.role.role_name == "doctor":
        return HttpResponseForbidden("Doctors should not access this page.")

    # ---- 2. Hospital is guaranteed by model ----
    hospital = user.hospital

    # ---- 3. Doctors list (for filter dropdown only) ----
    doctors = Doctor.objects.filter(hospital=hospital).order_by("doctor_name")
    selected_doctor = None

    # ---- 4. Base prescription queryset (HOSPITAL-SCOPED) ----
    prescriptions = (
        PrescriptionMaster.objects
        .filter(doctor__hospital=hospital)
        .select_related(
            "patient",
            "patient__contact",
            "doctor",
            "appointment",
            "appointment__doctor",
        )
    )

    # ---- 5. Optional doctor filter ----
    doctor_pk = request.GET.get("doctor")
    if doctor_pk:
        selected_doctor = get_object_or_404(doctors, pk=doctor_pk)
        prescriptions = prescriptions.filter(doctor=selected_doctor)

    # ---- 6. Order & limit ----
    prescriptions = prescriptions.order_by("-prescribed_on")[:20]

    return render(
        request,
        "prescription/view_prescriptions.html",
        {
            "doctors": doctors,
            "selected_doctor": selected_doctor,
            "prescriptions": prescriptions,
        }
    )


from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML

@login_required
def prescription_print_regular(request, rx_id):
    rx = get_object_or_404(
        PrescriptionMaster.objects.select_related(
            "patient", "patient__contact", "doctor", "appointment"
        ),
        pk=rx_id
    )

    if rx.doctor.hospital_id != request.user.hospital_id:
        return HttpResponseForbidden()

    html_string = render_to_string(
        "prescription/print/final_prescription.html",
        {"prescription": rx}
    )

    download = request.GET.get("dl") == "1"

    if download:
        pdf = HTML(string=html_string).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="Prescription-{rx_id}.pdf"'
        return response

    # Normal browser view
    return HttpResponse(html_string)


def get_user_hospital(user):
    """
    Safely resolve hospital for any logged-in user.
    """
    if hasattr(user, "doctor") and user.doctor:
        return user.doctor.hospital

    if hasattr(user, "hospital") and user.hospital:
        return user.hospital

    return None




# adjust these imports to your app layout



@login_required
@require_POST
def save_rx_template(request):
    """
    Payload JSON:
    {
      "name": "Viral Fever - Adults",
      "details": [
        {"drug_name":"Paracetamol", "composition":"...", "dosage":"500 mg", "frequency":"TID", "duration":"5 days", "food_order":"AF"},
        ...
      ]
    }
    """
    try:
        payload = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    name = (payload.get("name") or "").strip()
    details = payload.get("details") or []
    if not name:
        return JsonResponse({"ok": False, "error": "Template name is required"}, status=400)
    if not isinstance(details, list) or not details:
        return JsonResponse({"ok": False, "error": "No items to save"}, status=400)

    # Doctor & hospital context
    doctor = getattr(request.user, "doctor_profile", None) or getattr(request.user, "doctor", None)
    if not doctor or not isinstance(doctor, Doctor):
        return JsonResponse({"ok": False, "error": "Only doctors can save templates"}, status=403)
    hospital = getattr(request.user, "hospital", None) or getattr(doctor, "hospital", None)

    def match_drug(drug_name: str):
        """
        Best-effort match honoring your scoping rules:
        1) doctor-specific
        2) hospital-level (Doctor null)
        3) global (no hospital/doctor)
        """
        qs = Drug.objects.filter(drug_name__iexact=drug_name.strip())
        if doctor:
            m = qs.filter(added_by_doctor=doctor).first()
            if m: return m
        if hospital:
            m = qs.filter(hospital=hospital, added_by_doctor__isnull=True).first()
            if m: return m
        return qs.filter(hospital__isnull=True, added_by_doctor__isnull=True).first()

    with transaction.atomic():
        tmpl = DrugTemplate.objects.create(doctor=doctor, name=name)

        items = []
        matched_ids = set()

        for idx, row in enumerate(details):
            dn = (row.get("drug_name") or "").strip()
            if not dn:
                continue
            comp = (row.get("composition") or "").strip()
            dos  = (row.get("dosage") or "").strip()
            freq = (row.get("frequency") or "").strip()
            dur  = (row.get("duration") or "").strip()
            food = (row.get("food_order") or "").strip()

            matched = match_drug(dn)
            if matched:
                matched_ids.add(matched.id)

            items.append(DrugTemplateItem(
                template=tmpl,
                drug=matched,
                drug_name=dn,
                composition=comp,
                dosage=dos,
                frequency=freq,
                duration=dur,
                food_order=food,
            ))

        if not items:
            return JsonResponse({"ok": False, "error": "No valid rows"}, status=400)

        DrugTemplateItem.objects.bulk_create(items)

        # Fill the M2M with any matched catalog drugs (optional but keeps your M2M meaningful)
        if matched_ids:
            tmpl.drugs.add(*matched_ids)

    return JsonResponse({"ok": True, "template_id": tmpl.id, "name": tmpl.name, "items": len(items)})

# prescription/views.py

@login_required
def rx_templates_list(request):
  """Return the current doctor's templates for the select dropdown."""
  doctor = getattr(request.user, "doctor_profile", None) or getattr(request.user, "doctor", None)
  if not doctor or not isinstance(doctor, Doctor):
      return JsonResponse({"ok": False, "templates": []})

  qs = DrugTemplate.objects.filter(doctor=doctor).order_by('-created_at')
  data = [{"id": t.id, "name": t.name, "created_at": t.created_at.isoformat()} for t in qs]
  return JsonResponse({"ok": True, "templates": data})


@login_required
def rx_template_items(request, pk: int):
  """Return items for a given template (doctor-scoped)."""
  doctor = getattr(request.user, "doctor_profile", None) or getattr(request.user, "doctor", None)
  if not doctor or not isinstance(doctor, Doctor):
      return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

  try:
      t = DrugTemplate.objects.get(pk=pk, doctor=doctor)
  except DrugTemplate.DoesNotExist:
      return JsonResponse({"ok": False, "error": "Template not found"}, status=404)

  items = [{
      "drug_name": it.drug_name,
      "composition": it.composition,
      "dosage": it.dosage,
      "frequency": it.frequency,
      "duration": it.duration,
      "food_order": it.food_order,
  } for it in t.items.all().order_by('id')]

  return JsonResponse({"ok": True, "items": items, "name": t.name})



@login_required
def get_prescription_template(request, template_id: int):
    """
    Returns template items:
    [
      {"drug_name":"...", "composition":"...", "dosage":"...", "frequency":"...", "duration":"...", "food_order":"..."},
      ...
    ]
    """
    user = request.user
    doctor = getattr(user, "doctor_profile", None) or getattr(user, "doctor", None)
    hospital = getattr(user, "hospital", None) or getattr(getattr(doctor, "hospital", None), "pk", None)

    try:
        t = DrugTemplate.objects.select_related("doctor", "hospital").get(pk=template_id)
    except DrugTemplate.DoesNotExist:
        raise Http404("Template not found")

    # Visibility rules identical to list endpoint
    allowed = False
    if t.doctor_id and doctor and t.doctor_id == getattr(doctor, "id", None):
        allowed = True
    elif t.doctor_id is None and t.hospital_id and hospital and t.hospital_id == hospital:
        allowed = True
    elif t.doctor_id is None and t.hospital_id is None:
        allowed = True

    if not allowed:
        return JsonResponse({"ok": False, "error": "Not allowed"}, status=403)

    items = list(
        DrugTemplateItem.objects
        .filter(template=t)
        .order_by("id")
        .values(
            "drug_name", "composition", "dosage", "frequency", "duration", "food_order"
        )
    )
    return JsonResponse({"ok": True, "id": t.id, "name": t.name, "items": items})




@login_required
@require_POST
def apply_rx_template(request):
    try:
        payload = json.loads(request.body or "{}")
        template_id = int(payload.get("template_id") or 0)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    if not template_id:
        return JsonResponse({"ok": False, "error": "Template id is required"}, status=400)

    doctor = getattr(request.user, "doctor_profile", None) or getattr(request.user, "doctor", None)
    if not doctor:
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

    try:
        tmpl = DrugTemplate.objects.get(id=template_id, doctor=doctor)
    except DrugTemplate.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Template not found"}, status=404)

    items = [{
        "drug_name": it.drug_name,
        "composition": it.composition,
        "dosage": it.dosage,
        "frequency": it.frequency,
        "duration": it.duration,
        "food_order": it.food_order,
    } for it in tmpl.items.all().order_by('id')]

    return JsonResponse({"ok": True, "name": tmpl.name, "items": items})


# prescription/views.py


try:
    # If you have this helper from your receipt code
    from core.utils.policies import get_consultation_policy
except Exception:
    get_consultation_policy = None


def _resolve_latest_vitals(hospital, patient, appointment=None):
    """
    Return latest vitals for this appointment if present,
    otherwise latest vitals for the patient.
    """
    qs = PatientVital.objects.filter(hospital=hospital, patient=patient).order_by("-recorded_at")
    if appointment:
        v = qs.filter(appointment=appointment).first()
        if v:
            return v
    return qs.first()


@login_required
def prescription_print_builder(request, prescription_id):
    pres = get_object_or_404(
        PrescriptionMaster.objects.select_related("patient", "doctor", "hospital"),
        pk=prescription_id
    )

    hospital = pres.hospital
    doctor   = pres.doctor
    patient  = pres.patient
    appointment = getattr(pres, "appointment", None)  # safe: may be None

    contact_bits = []
    if getattr(hospital, "phone_num", None):
        contact_bits.append(str(hospital.phone_num))
    if getattr(hospital, "email", None):
        contact_bits.append(hospital.email)
    contact_line = " · ".join(contact_bits)

    # Build a combined 'notes' block and also expose each field
    history  = pres.notes_history or ""
    symptoms = pres.notes_symptoms or ""
    findings = pres.notes_findings or ""
    advice   = pres.general_advice or ""

    combined_notes = "\n\n".join([p for p in [history, symptoms, findings, advice] if p])

    meds = [{
        "name": d.drug_name or "",
        "dose": d.dosage or "",
        "freq": d.frequency or "",
        "dur":  d.duration or "",
        "route": (d.food_order or ""),
    } for d in pres.details.all()]

    # ⬇️ NEW: fetch vitals (appt-specific preferred)
    v = _resolve_latest_vitals(hospital, patient, appointment)
    vitals_payload = {
        "height_cm":     str(getattr(v, "height_cm", "") or ""),
        "weight_kg":     str(getattr(v, "weight_kg", "") or ""),
        "bmi":           str(getattr(v, "bmi", "") or ""),
        "temperature_c": str(getattr(v, "temperature_c", "") or ""),
        "bp":            (f"{v.bp_systolic}/{v.bp_diastolic}" if v else ""),
        "spo2_percent":  getattr(v, "spo2_percent", None),
        "pulse_bpm":     getattr(v, "pulse_bpm", None),
    }

    # ⬇️ NEW: bottom disclaimer (policy message + default text)
    default_disclaimer = (
        "This prescription is issued for the named patient and is not valid if altered. "
        "Take medicines as directed. In case of adverse reactions, contact the clinic immediately. "
        "Keep out of reach of children."
    )
    policy_msg = ""
    if callable(get_consultation_policy):
        try:
            policy = get_consultation_policy(hospital, doctor)  # expected to return dict with 'message'
            policy_msg = (policy or {}).get("message", "") or ""
        except Exception:
            policy_msg = ""
    disclaimer_text = (policy_msg + (" " if policy_msg else "") + default_disclaimer).strip()

    initial = {
        "doctorName":   getattr(doctor, "doctor_name", "") or "",
        "qualification":getattr(doctor, "qualification", "") or "",
        "clinic":       getattr(hospital, "hospital_name", "") or "",
        "contact":      contact_line,
        "patientName":  getattr(patient, "patient_name", "") or "",
        "patientAge":   getattr(patient, "age_years", "") or "",
        "gender":       getattr(patient, "gender", "") or "",
        "date":         (pres.prescribed_on.date().isoformat() if pres.prescribed_on else date.today().isoformat()),

        # diagnosis: pick your priority; this keeps your current approach
        "diagnosis":    findings or symptoms or "",

        # notes (for the “Advice / Notes” section and per-field areas)
        "history":  history,
        "symptoms": symptoms,
        "findings": findings,
        "advice":   advice,
        "notes":    combined_notes,

        "meds": meds,

        # ⬇️ NEW payloads consumed by the template JS
        "vitals": vitals_payload,
        "disclaimer": disclaimer_text,
    }

    return render(request, "prescription/print_builder.html", {
        "initial": initial,
        "hide_form": True,
        "print_top_mm": 50,
    })
