from django.forms import modelformset_factory
from django.db import transaction
from django.db.models import Q, Sum
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from decimal import Decimal
from datetime import date, datetime
from django.http import JsonResponse
from django.urls import reverse
from patients.forms import PatientRegistrationForm,PatientSearchForm
from appointments.forms import AppointmentForm
from billing.forms import PaymentTransactionForm
from billing.models import PaymentTransaction, PaymentMaster
from appointments.models import AppointmentDetails
from doctors.models import Doctor
from patients.utils import generate_token_string
from .utils import perform_patient_search
from appointments.utils import get_next_queue_position, get_registration_queue_position
from utils.eta_calculator import calculate_eta_time
from .models import Patient
from .utils import render_to_pdf
from django.http import JsonResponse, HttpResponse
import logging
from django.utils.timezone import now
import traceback
from utils.form_validation import validate_or_report
from django.core.exceptions import ValidationError
from django.template.loader import get_template
from weasyprint import HTML
from decimal import Decimal, ROUND_HALF_UP
from core.utils.policies import get_consultation_policy  # ⬅️ add this import
from core.models import Hospital
from django.urls import reverse, NoReverseMatch
from django.utils.dateparse import parse_date, parse_datetime
from .utils import (_safe,_parse_date_flexible,_compute_eta_preview, 
                    _render_register,_amount_in_words_inr,
                    _queue_position_for, _appointment_date_str,_fmt_date)
from utils.user_helpers import collected_by_label
# patients/views.py

# --- 1. New Patient Registration ---

logger = logging.getLogger(__name__)

def register_patient_view(request):
    hospital = request.user.hospital
    today = date.today()

    appt_obj = None  # For later reference in render()

    if request.method == 'POST':
        post = request.POST.copy()
        post.setdefault('appointment-appointment_on', today.isoformat())

        patient_form = PatientRegistrationForm(post, prefix='patient')
        appointment_form = AppointmentForm(post, prefix='appointment', hospital_id=hospital.id)
        txn_form = PaymentTransactionForm(post, prefix='txn', hospital_id=hospital.id)

        if patient_form.is_valid() and appointment_form.is_valid() and txn_form.is_valid():
            try:
                with transaction.atomic():
                    # 1️⃣ Save Contact and Patient
                    contact, patient = patient_form.save(hospital=hospital)
                    

                    # 2️⃣ Create and save PaymentMaster
                    pay = PaymentMaster.objects.create(
                        paid_on=appointment_form.cleaned_data["appointment_on"],
                        mobile_num=contact.mobile_num,
                        patient=patient,
                        hospital=hospital,
                        collected_by = collected_by_label(request.user),
                        total_amount=Decimal("0.00")
                    )
                    pay.full_clean()
                    pay.save()

                    # 3️⃣ Save PaymentTransaction
                    txn = txn_form.save(commit=False)
                    txn.patient = patient
                    txn.payment = pay
                    txn.hospital = hospital
                    txn.doctor = appointment_form.cleaned_data["doctor"]
                    txn.service = txn_form.cleaned_data["service"]
                    txn.amount = txn_form.cleaned_data["amount"]
                    txn.paid_on = pay.paid_on
                    txn.save()

                    # 4️⃣ Update PaymentMaster total
                    total = PaymentTransaction.objects.filter(payment=pay).aggregate(
                        total=Sum("amount")
                    )["total"] or Decimal("0.00")
                    pay.total_amount = total
                    pay.save(update_fields=["total_amount"])
                    
                    # 5️⃣ Save AppointmentDetails
                    appt_obj = appointment_form.save(commit=False)
                    appt_obj.doctor = appointment_form.cleaned_data['doctor']
                    appt_obj.patient = patient
                    appt_obj.mobile_num = contact.mobile_num
                    appt_obj.hospital = hospital
                    appt_obj.payment = pay
                    appt_obj.token_num = generate_token_string()

                    # Calculate queue position and ETA
                    pos_data = get_registration_queue_position(
                                    doctor=appt_obj.doctor,
                                    date=appt_obj.appointment_on,
                                    hospital=hospital
                                )
                    appt_obj.que_pos = appt_obj.que_pos or pos_data["next_pos"]
                    appt_obj.eta = calculate_eta_time(
                        appt_obj.doctor.start_time,
                        appt_obj.doctor.average_time_minutes,
                        appt_obj.que_pos,
                        appointment_on=appt_obj.appointment_on
                    )
                    appt_obj.status = AppointmentDetails.STATUS_REGISTERED
                    appt_obj.save()

                    # 🔁 Final consistency check
                    final_total = PaymentTransaction.objects.filter(payment=pay).aggregate(
                        total=Sum("amount")
                    )["total"] or Decimal("0.00")
                    if final_total != pay.total_amount:
                        pay.total_amount = final_total
                        pay.save(update_fields=["total_amount"])

                messages.success(request, "✅ Patient registration completed successfully.")
                return redirect(reverse('patients:view', args=[patient.pk]))

            except Exception as e:
                logger.exception("❌ Error during patient registration/save")
                messages.error(request, f"❌ An error occurred while saving: {e}")
        else:
            # Log validation errors
            def _errors(form):
                return {k: [str(e) for e in v] for k, v in form.errors.items()}
            logger.warning(
                "Form validation failed: patient=%s, appointment=%s, txn=%s",
                _errors(patient_form), _errors(appointment_form), _errors(txn_form)
            )
            messages.error(request, "❌ Please correct the errors below.")
    else:
        # GET: Initialize blank forms
        patient_form = PatientRegistrationForm(prefix='patient')
        appointment_form = AppointmentForm(prefix='appointment', hospital_id=hospital.id)
        txn_form = PaymentTransactionForm(prefix='txn', hospital_id=hospital.id)

    return render(request, 'patients/register.html', {
        'patient_form': patient_form,
        'appointment_form': appointment_form,
        'transaction_form': txn_form,
        'is_edit': False,
        'eta': getattr(appt_obj, 'eta', None),
        'que_pos': getattr(appt_obj, 'que_pos', None),
        'total_amount': getattr(txn_form, 'consultation_fee', 0.00),
        'consultation_fee': getattr(txn_form, 'consultation_fee', 0.00),
    })
# --- 2. Edit Existing Patient ---

@login_required
def edit_patient_view(request, patient_id):
    hospital = request.user.hospital
    today = date.today()
    eta_preview = None

    # Fetch patient and related records
    patient = get_object_or_404(Patient, pk=patient_id, hospital=hospital)
    contact = patient.contact
    appt = AppointmentDetails.objects.filter(patient=patient, hospital=hospital).order_by('-appointment_on').first()
    payment = appt.payment if appt and appt.payment else None
    txn = PaymentTransaction.objects.filter(payment=payment).first() if payment else None

    if request.method == 'POST':
        post = request.POST.copy()
        post.setdefault('payment-paid_on', today)
        post.setdefault('appointment-appointment_on', today)

        patient_form = PatientRegistrationForm(post, prefix='patient')
        appointment_form = AppointmentForm(post, prefix='appointment', instance=appt, hospital_id=hospital.id)
        txn_form = PaymentTransactionForm(post, prefix='txn', instance=txn, hospital_id=hospital.id)

        eta_preview = _compute_eta_preview(appointment_form, hospital, post_data=post)

        if patient_form.is_valid() and appointment_form.is_valid() and txn_form.is_valid():
            try:
                with transaction.atomic():
                    if appt: appt.delete()
                    if txn: txn.delete()
                    if payment: payment.delete()

                    contact, patient = patient_form.save(hospital=hospital)

                    pay = PaymentMaster.objects.create(
                        paid_on=appointment_form.cleaned_data["appointment_on"],
                        mobile_num=contact.mobile_num,
                        patient=patient,
                        hospital=hospital,
                        collected_by = collected_by_label(request.user),
                        total_amount=Decimal("0.00"),
                    )

                    appt_obj = appointment_form.save(commit=False)
                    appt_obj.doctor = appointment_form.cleaned_data['doctor']
                    appt_obj.patient = patient
                    appt_obj.mobile_num = contact.mobile_num
                    appt_obj.hospital = hospital
                    appt_obj.payment = pay
                    appt_obj.token_num = appt_obj.token_num or generate_token_string()

                    pos_data = get_next_queue_position(
                        doctor=appt_obj.doctor,
                        date=appt_obj.appointment_on,
                        hospital=hospital
                    )
                    appt_obj.que_pos = appt_obj.que_pos or pos_data.get("next_pos")

                    doc = Doctor.objects.get(pk=appt_obj.doctor.pk)
                    appt_obj.eta = calculate_eta_time(
                        doc.start_time,
                        doc.average_time_minutes,
                        appt_obj.que_pos,
                        appointment_on=appt_obj.appointment_on
                    )
                    appt_obj.completed = appt.completed if appt else AppointmentDetails.STATUS_REGISTERED
                    appt_obj.save()

                    txn_obj = txn_form.save(commit=False)
                    txn_obj.patient = patient
                    txn_obj.payment = pay
                    txn_obj.hospital = hospital
                    txn_obj.doctor = appt_obj.doctor
                    txn_obj.paid_on = pay.paid_on
                    if not txn_obj.amount:
                        raise ValueError("Transaction amount is missing!")
                    txn_obj.save()

                    pay.total_amount = txn_obj.amount
                    pay.save(update_fields=['total_amount'])

                messages.success(request, "✅ Patient updated successfully.")
                return redirect(reverse('patients:view', args=[patient.pk]))

            except Exception as e:
                messages.error(request, f"❌ An error occurred while saving: {str(e)}")

        else:
            messages.error(request, "❌ Please correct the errors below.")

    else:
        initial = {
            'mobile_num': contact.mobile_num,
            'contact_name': contact.contact_name,
            'patient_name': patient.patient_name,
            'dob': patient.dob,
            'gender': patient.gender,
            'referred_by': patient.referred_by,
        }
        patient_form = PatientRegistrationForm(initial=initial, prefix='patient')
        appointment_form = AppointmentForm(prefix='appointment', instance=appt, hospital_id=hospital.id)
        txn_form = PaymentTransactionForm(prefix='txn', instance=txn, hospital_id=hospital.id)
        eta_preview = _compute_eta_preview(appointment_form, hospital)

    return render(request, 'patients/register.html', {
        'patient_form': patient_form,
        'appointment_form': appointment_form,
        'transaction_form': txn_form,
        'eta': eta_preview,
        'is_edit': True,
        'patient': patient,
    })


# --- 3. View Patient (and Print) ---
# patients/views.py



@login_required
def view_patient_view(request, patient_id):
    hospital = request.user.hospital
    patient  = get_object_or_404(Patient, pk=patient_id, hospital=hospital)

    appointments = (AppointmentDetails.objects
                    .filter(patient=patient, hospital=hospital)
                    .select_related('doctor', 'payment')
                    .order_by('-appointment_on', '-pk'))
    payments     = [appt.payment for appt in appointments if appt.payment]
    latest_appt  = appointments.first()

    # --- Build vitals URLs (robust; won’t crash if route names change) ---
    vitals_new_url = None
    vitals_new_for_appt_url = None
    try:
        vitals_new_url = reverse("vitals:create_for_patient", kwargs={"patient_id": patient.pk})
    except NoReverseMatch:
        pass
    if latest_appt:
        try:
            vitals_new_for_appt_url = reverse(
                "vitals:create_for_appointment",
                kwargs={"patient_id": patient.pk, "appointment_id": latest_appt.pk}
            )
        except NoReverseMatch:
            vitals_new_for_appt_url = vitals_new_url  # fallback to patient-scoped

    context = {
        'patient':          patient,
        'contact':          patient.contact,
        'appointments':     appointments,
        'payments':         payments,
        'latest_appt_id':   latest_appt.pk if latest_appt else None,
        'can_edit':         True,
        'can_print':        True,

        # NEW
        'vitals_new_url':           vitals_new_url,
        'vitals_new_for_appt_url':  vitals_new_for_appt_url,
    }
    return render(request, 'patients/view.html', context)


@login_required
def patient_dashboard(request):
    hospital = request.user.hospital
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '')

    # ============================================================
    # ALWAYS DEFINE patients FIRST (fixes your UnboundLocalError)
    # ============================================================
    patients = Patient.objects.filter(hospital=hospital).select_related('contact')

    # ============================================================
    # Restrict to logged-in doctor’s patients (safe reverse name)
    # ============================================================
    doctor_obj = getattr(request.user, "doctor", None)

    if doctor_obj is not None:
        patients = patients.filter(
            appointmentdetails__doctor=doctor_obj
        ).distinct()

    # ============================================================
    # Build latest doctor mapping
    # ============================================================
    appts = (
        AppointmentDetails.objects.filter(hospital=hospital)
        .order_by('patient_id', '-appointment_on')
        .select_related('doctor')
    )

    latest_doctor = {}
    for appt in appts:
        if appt.patient_id not in latest_doctor:
            latest_doctor[appt.patient_id] = appt.doctor.doctor_name

    # ============================================================
    # 🔍 Search logic
    # ============================================================
    if q:
        prefix = hospital.hospital_name[:3].upper()
        stripped = q.replace(prefix, "").replace("-", "").strip()

        filters = (
            Q(patient_name__icontains=q) |
            Q(contact__mobile_num__icontains=q) |
            Q(contact__contact_name__icontains=q)
        )

        if stripped.isdigit():
            filters |= Q(id=int(stripped))

        patients = patients.filter(filters)

    # ============================================================
    # Ordering & limit
    # ============================================================
    patients = list(patients.order_by('-id')[:100])

    if sort == 'doctor':
        patients.sort(key=lambda p: latest_doctor.get(p.id, '').lower())
    
    # ============================================================
    # Build mapping of DUE payments per patient
    # ============================================================
    due_map = {
        pt.patient_id: True
        for pt in PaymentTransaction.objects.filter(
            hospital=hospital,
            pay_type="Due"
        ).only("patient_id")
    }

    from django.urls import reverse, NoReverseMatch

    vitals_url_map = {}

    for p in patients:
        vitals_url = None

        # find latest appointment for this patient
        latest_appt = (
            AppointmentDetails.objects
            .filter(patient=p, hospital=hospital)
            .order_by('-appointment_on', '-pk')
            .first()
        )

            
    context = {
        'patients': patients,
        'latest_doctor': latest_doctor,
        'due_map': due_map,
        'q': q,
        'sort': sort,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'patients/_rows.html', context)

    return render(request, 'patients/dashboard.html', context)

# --- Print/Receipt APIs (unchanged) ---

# Allowed options (keep it tight so bad input can't break CSS)

ALLOWED_SIZES  = {"A5", "A4", "LETTER", "ROLL80"}
ALLOWED_ORIENT = {"portrait", "landscape"}


@login_required
def cash_receipt_pdf(request, appointment_id):
    """
    Generate a PDF cash receipt for a given appointment.
    Updated for DOB-based patient model.
    """
    appt = get_object_or_404(
        AppointmentDetails.objects.select_related(
            "hospital", "patient__contact", "doctor", "payment"
        ),
        pk=appointment_id,
        hospital=request.user.hospital,
    )

    if not appt.payment:
        return HttpResponse("No payment record found for this appointment.", status=404)

    # --- Consultation validity policy
    policy = get_consultation_policy(appt.hospital, appt.doctor)  # {"days", "visits", "message"}

    # --- Page setup
    pagesize = (request.GET.get("pagesize", "A5") or "A5").upper()
    orientation = (request.GET.get("orientation", "portrait") or "portrait").lower()

    if pagesize not in ALLOWED_SIZES:
        pagesize = "A5"
    if pagesize == "ROLL80":
        orientation = "portrait"
    elif orientation not in ALLOWED_ORIENT:
        orientation = "portrait"

    page_class = f"{pagesize.lower()}-{orientation}"

    # --- Transactions & total
    txns_qs = PaymentTransaction.objects.filter(payment=appt.payment).select_related("service")
    txns = list(txns_qs)
    total = getattr(appt.payment, "total_amount", None)
    if total is None:
        total = sum((Decimal(getattr(t, "amount", 0) or 0) for t in txns), Decimal("0.00"))

    receipt_no = f"RCP-{appt.hospital_id}-{date.today():%Y%m%d}-{appt.pk}"

    # --- Patient details (DOB-based)
    patient = appt.patient
    gender = patient.get_gender_display()

    if patient.dob:
        years = patient.age_years()
        months = patient.age_months() % 12 if patient.age_months() else 0
        age_str = f"{years}y {months}m" if years is not None else "-"
    else:
        age_str = "-"

    # --- Context for rendering
    context = {
        "hospital": appt.hospital,
        "patient": patient,
        "doctor": appt.doctor,
        "payment": appt.payment,
        "txns": txns,
        "amount": total,
        "total_amount": total,
        "amount_in_words": _amount_in_words_inr(Decimal(total or 0)),
        "appointment_id": appt.pk,
        "pagesize": pagesize,
        "orientation": orientation,
        "page_class": page_class,
        "for_pdf": True,
        "now": datetime.now(),
        "receipt_no": receipt_no,

        # Consultation policy info
        "consult_policy": policy,
        "consult_message": policy.get("message") if policy else "",

        # DOB-based display
        "age_display": age_str,
        "gender": gender,
    }

    # --- Render PDF
    tpl = get_template("pdf_templates/cash_receipt.html")
    html_string = tpl.render(context, request=request)

    pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="receipt_{appt.pk}.pdf"'
    return response


ALLOWED_SIZES   = {"A5", "A4", "Letter"}
ALLOWED_ORIENT  = {"portrait", "landscape"}


@login_required
def cash_receipt_preview(request, appointment_id):
    """
    Preview cash receipt for a given appointment (DOB-based patient info version).
    """
    appt = get_object_or_404(
        AppointmentDetails.objects.select_related(
            "hospital", "patient__contact", "doctor", "payment"
        ),
        pk=appointment_id,
        hospital=request.user.hospital,
    )

    # Toolbar inputs
    pagesize = request.GET.get("pagesize", "A5")
    orientation = request.GET.get("orientation", "portrait")
    if pagesize not in ALLOWED_SIZES:
        pagesize = "A5"
    if orientation not in ALLOWED_ORIENT:
        orientation = "portrait"

    payment = getattr(appt, "payment", None)
    txns_qs = PaymentTransaction.objects.filter(payment=payment).select_related("service") if payment else []
    txns = list(txns_qs) if txns_qs else []
    total = getattr(payment, "total_amount", None)

    # Fallback: compute total from txns if missing
    if total is None:
        total = sum((Decimal(getattr(t, "amount", 0)) for t in txns), Decimal("0.00"))

    # Generate a stable receipt number
    receipt_no = f"RCP-{appt.hospital_id}-{date.today():%Y%m%d}-{appt.pk}"

    # Extract patient details (DOB-based)
    patient = appt.patient
    gender = dict(Patient.GENDER_CHOICES).get(patient.gender, patient.gender)

    # ✅ Compute age dynamically
    if patient.dob:
        years = patient.age_years()
        months = patient.age_months() % 12 if patient.age_months() else 0
        age_str = f"{years}y {months}m" if years is not None else "-"
    else:
        age_str = "-"

    # Prepare context
    context = {
        "hospital": appt.hospital,
        "patient": patient,
        "doctor": appt.doctor,
        "payment": payment,
        "txns": txns,
        "amount": total,
        "total_amount": total,
        "amount_in_words": _amount_in_words_inr(Decimal(total or 0)),
        "appointment_id": appt.pk,
        "pagesize": pagesize,
        "orientation": orientation,
        "for_pdf": False,
        "now": date.today(),
        "receipt_no": receipt_no,
        # 🧾 Display values
        "age_display": age_str,
        "gender": gender,
    }

    return render(request, "pdf_templates/cash_receipt.html", context)



ALLOWED_FORMATS = {"slip", "a5"}
ALLOWED_ORIENT  = {"portrait", "landscape"}


def _age_str(patient):
    # Prefer explicit age fields
    y = getattr(patient, "age_years", None)
    m = getattr(patient, "age_months", None)

    if y is not None or m is not None:
        y = y or 0
        m = m or 0
        parts = []
        if y: parts.append(f"{y}y")
        if m: parts.append(f"{m}m")
        return " ".join(parts) if parts else "-"

    # Fallback: compute from DOB if available
    dob = getattr(patient, "dob", None)
    
    return "-"


# Use it like:
ALLOWED_FORMATS = ["slip", "a5"]
ALLOWED_ORIENT = ["portrait", "landscape"]


@login_required
def token_pdf(request, appointment_id):
    """
    Generate printable token/slip PDF for an appointment.
    Updated for DOB-based patient model.
    """
    appt = get_object_or_404(
        AppointmentDetails.objects.select_related("hospital", "patient__contact", "doctor"),
        pk=appointment_id,
        hospital=request.user.hospital,
    )

    fmt = request.GET.get("format", "slip").lower()
    if fmt not in ALLOWED_FORMATS:
        fmt = "slip"

    height_mm = request.GET.get("height_mm", "100")
    try:
        height_mm = max(50, min(200, int(height_mm)))
    except ValueError:
        height_mm = 100

    orientation = request.GET.get("orientation", "portrait")
    if orientation not in ALLOWED_ORIENT:
        orientation = "portrait"

    pagesize = f"80mm {height_mm}mm" if fmt == "slip" else f"A5 {orientation}"

    # ✅ Compute queue position
    que_pos = getattr(appt, "que_pos", "-")

    # ✅ Compute age dynamically from DOB
    patient = appt.patient
    gender = patient.get_gender_display()

    if patient.dob:
        years = patient.age_years()
        months = patient.age_months() % 12 if patient.age_months() else 0
        age_display = f"{years}y {months}m" if years is not None else "-"
    else:
        age_display = "-"

    # ✅ Preformatted date string (optional)
    appt_date_str = appt.appointment_on.strftime("%d-%m-%Y")

    # ✅ Build context for template
    context = {
    "hospital": appt.hospital,
    "patient": patient,
    "doctor": appt.doctor,
    "token": getattr(appt, "token_num", getattr(appt, "id", 0)),
    "que_pos": que_pos if que_pos else "-",
    "age_display": age_display,
    "gender": gender,

    # 🔥 FIXED — pass actual date used by template
    "appt_date": appt.appointment_on,

    # (Optional: keep if you want)
    "appt_date_str": appt_date_str,

    "appointment_id": appt.pk,
    "format": fmt,
    "height_mm": height_mm,
    "orientation": orientation,
    "pagesize": pagesize,
    "for_pdf": True,
}

    # ✅ Render PDF
    pdf_bytes = render_to_pdf("pdf_templates/token_dynamic.html", context)
    if not pdf_bytes:
        return HttpResponse("Error generating token", status=500)

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="token_{appt.pk}.pdf"'
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp["Pragma"] = "no-cache"
    return resp




ALLOWED_FORMATS = ["slip", "a5"]
ALLOWED_ORIENT = ["portrait", "landscape"]


@login_required
def token_preview(request, appointment_id):
    """HTML preview for token/slip generation (DOB-based patient info)."""
    appt = get_object_or_404(
        AppointmentDetails.objects.select_related("hospital", "patient__contact", "doctor"),
        pk=appointment_id,
        hospital=request.user.hospital,
    )

    fmt = request.GET.get("format", "slip").lower()
    if fmt not in ALLOWED_FORMATS:
        fmt = "slip"

    height_mm = request.GET.get("height_mm", "100")
    try:
        height_mm = max(50, min(200, int(height_mm)))
    except ValueError:
        height_mm = 100

    orientation = request.GET.get("orientation", "portrait")
    if orientation not in ALLOWED_ORIENT:
        orientation = "portrait"

    pagesize = f"80mm {height_mm}mm" if fmt == "slip" else f"A5 {orientation}"

    # ✅ Extract patient info with DOB-based age
    patient = appt.patient
    gender = patient.get_gender_display()

    if patient.dob:
        years = patient.age_years()
        months = patient.age_months() % 12 if patient.age_months() else 0
        age_display = f"{years}y {months}m" if years is not None else "-"
    else:
        age_display = "-"

    context = {
        "hospital": appt.hospital,
        "patient": patient,
        "doctor": appt.doctor,
        "token": getattr(appt, "token_num", getattr(appt, "id", 0)),
        "que_pos": getattr(appt, "que_pos", "-"),  # ✅ renamed from queue_position
        "appointment_id": appt.pk,
        "appt_date": appt.appointment_on,
        "format": fmt,
        "height_mm": height_mm,
        "orientation": orientation,
        "pagesize": pagesize,
        "for_pdf": False,  # show toolbar
        # 🆕 Add DOB-based details
        "age_display": age_display,
        "gender": gender,
    }

    return render(request, "pdf_templates/token_dynamic.html", context)


@login_required
def register_success(request, appointment_id):
    # Fetch appointment, patient, and payment
    appt = get_object_or_404(
        AppointmentDetails.objects.select_related('patient__contact', 'payment', 'doctor'),
        pk=appointment_id,
        hospital=request.user.hospital
    )
    payment = appt.payment
    contact = appt.patient.contact

    context = {
        'appointment': appt,
        'patient': appt.patient,
        'contact': contact,
        'payment': payment,
    }
    return render(request, 'patients/register_success.html', context)


@require_GET
@login_required
def get_patients_for_doctor(request):
    doctor_id = request.GET.get("doctor_id")
    hospital = request.user.hospital

    if not doctor_id:
        return JsonResponse({"error": "Missing doctor_id"}, status=400)

    today = date.today()

    # Queued patients: appointment today and not completed

    registered_appts = AppointmentDetails.objects.filter(
        doctor_id=doctor_id,
        hospital=hospital,
        appointment_on=today,
        completed=-1
    ).select_related("patient")
    
    queued_appts = AppointmentDetails.objects.filter(
        doctor_id=doctor_id,
        hospital=hospital,
        appointment_on=today,
        completed=0
    ).select_related("patient")

    # Completed patients: appointment today and completed
    completed_appts = AppointmentDetails.objects.filter(
        doctor_id=doctor_id,
        hospital=hospital,
        appointment_on=today,
        completed=1
    ).select_related("patient")

    def serialize(appt):
        p = appt.patient
        return {
            "id": p.id,
            "patient_name": p.patient_name,
            "age": p.age,
            "gender": p.gender
        }

    return JsonResponse({
        "registered": [serialize(a) for a in registered_appts],
        "queued": [serialize(a) for a in queued_appts],
        "completed": [serialize(a) for a in completed_appts]
    })


ALLOWED_SIZES = {"A5", "A4", "LETTER"}
ALLOWED_ORIENT = {"portrait", "landscape"}


@login_required
def combined_receipt_token_pdf(request, appointment_id):
    appt = get_object_or_404(
        AppointmentDetails.objects.select_related(
            "hospital", "patient__contact", "doctor", "payment"
        ),
        pk=appointment_id,
        hospital=request.user.hospital,
    )

    # --- Consultation policy (optional)
    policy = get_consultation_policy(appt.hospital, appt.doctor) or {}

    # --- Token & queue details
    token = getattr(appt, "token_num", appt.pk)
    que_pos = getattr(appt, "que_pos", "-")

    # --- DOB-based age + gender
    patient = appt.patient
    gender = patient.get_gender_display()
    if patient.dob:
        years = patient.age_years()
        months_total = patient.age_months() or 0
        months = months_total % 12
        age_display = f"{years}y {months}m" if years is not None else "-"
    else:
        age_display = "-"

    # --- Appointment date (string)
    appt_date_str = appt.appointment_on.strftime("%d-%m-%Y")

    # --- Receipt / payment details
    txns = list(PaymentTransaction.objects.filter(payment=appt.payment).select_related("service"))
    total = getattr(appt.payment, "total_amount", None)
    if total is None:
        total = sum((Decimal(getattr(t, "amount", 0) or 0) for t in txns), Decimal("0.00"))

    receipt_no = f"RCP-{appt.hospital_id}-{date.today():%Y%m%d}-{appt.pk}"

    # --- Page setup (with safe defaults)
    pagesize = (request.GET.get("pagesize", "A5") or "A5").upper()
    orientation = (request.GET.get("orientation", "landscape") or "landscape").lower()
    if pagesize not in ALLOWED_SIZES:
        pagesize = "A5"
    if orientation not in ALLOWED_ORIENT:
        orientation = "landscape"

    # --- Context
    context = {
        "hospital": appt.hospital,
        "patient": patient,
        "doctor": appt.doctor,
        "payment": appt.payment,
        "txns": txns,

        # token slip bits
        "token": token,
        "que_pos": que_pos or "-",
        "appt_date_str": appt_date_str,
        "age_display": age_display,
        "gender": gender,

        # receipt bits
        "total_amount": total,
        "amount_in_words": _amount_in_words_inr(Decimal(total or 0)),
        "receipt_no": receipt_no,
        "consult_message": policy.get("message", ""),

        # layout
        "pagesize": pagesize,
        "orientation": orientation,
        "for_pdf": True,
    }

    # --- Render and return PDF
    tpl = get_template("pdf_templates/combined_receipt_token.html")
    html = tpl.render(context, request=request)
    pdf_bytes = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="receipt_token_{appt.pk}.pdf"'
    return resp



from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from datetime import date
from .models import Patient
from django.db.models import Q

#patients/view.py

@login_required
def patient_search(request):
    """
    API endpoint: /patients/search/?q=<query>
    Returns lightweight JSON for patient autofill.
    """
    q = (request.GET.get("q") or "").strip()
    qs = perform_patient_search(request.user.hospital, q)

    results = []
    for p in qs:
        results.append({
            "id": p.id,
            "patient_code": p.patient_code,
            "patient_name": p.patient_name,
            "contact_name": p.contact.contact_name,
            "mobile": str(p.contact.mobile_num),
            "dob": p.dob.strftime("%d-%m-%Y") if p.dob else "",
            "dob_raw": p.dob.isoformat() if p.dob else "",   # <-- raw ISO date for <input type="date">
            "gender": p.gender,
            "referred_by": p.referred_by or "",
            "display_name": f"{p.patient_name} ({p.contact.mobile_num})"
        })

    return JsonResponse({"results": results})
