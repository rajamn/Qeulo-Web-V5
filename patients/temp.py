from django.forms import modelformset_factory
from django.db import transaction
from django.db.models import Q, Sum
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from decimal import Decimal
from datetime import date, datetime
from django.http import JsonResponse
from patients.forms import PatientRegistrationForm,PatientSearchForm
from appointments.forms import AppointmentForm
from billing.forms import PaymentMasterForm, PaymentTransactionForm
from billing.models import PaymentTransaction
from appointments.models import AppointmentDetails
from doctors.models import Doctor
from patients.utils import generate_token_string
from appointments.utils import get_next_queue_position
from utils.eta_calculator import calculate_eta_time
from .models import Patient
from django.urls import reverse
from .utils import render_to_pdf
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
import logging
from django.utils.timezone import now
# patients/views.py

# --- 1. New Patient Registration ---

logger = logging.getLogger(__name__)

def _parse_date_flexible(d, default_date: date) -> date:
    if not d:
        return default_date
    if isinstance(d, date):
        return d
    s = str(d).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return default_date

def _compute_eta_preview(appointment_form, hospital, post_data=None):
    """
    Try to compute an ETA preview for display in the form.
    Works when:
      - appointment_form is valid (preferred), OR
      - we can minimally parse doctor, date, and queue pos from post_data.
    Returns a string like '14:35' or None.
    """
    try:
        # Preferred: if the appointment form validated, use cleaned_data
        if appointment_form.is_bound and appointment_form.is_valid():
            appt_date = appointment_form.cleaned_data.get("appointment_on") or date.today()
            doc = appointment_form.cleaned_data.get("doctor")
            if not doc:
                return None
            # Compute the *next* queue position for preview
            pos_data = get_next_queue_position(doc, date.today(), hospital)
            que_pos = pos_data["next_pos"]
            completed_count = pos_data["completed_count"]
            eta_t = calculate_eta_time(doc.start_time, doc.average_time_minutes, que_pos, appointment_on=appt_date)
            return eta_t.strftime("%H:%M")

        # Fallback: try to pull from incoming POST (when the form has errors elsewhere)
        if post_data:
            doc_id = post_data.get("appointment-doctor") or post_data.get("doctor")
            if not doc_id:
                return None
            try:
                doc = Doctor.objects.get(pk=doc_id)
            except Doctor.DoesNotExist:
                return None

            appt_date = _parse_date_flexible(
                post_data.get("appointment-appointment_on"),
                default_date=date.today()
            )
            que_pos,completed_count = get_next_queue_position(doctor=doc, date=appt_date, hospital=hospital)
            eta_t = calculate_eta_time(doc.start_time, doc.average_time_minutes, que_pos, appointment_on=appt_date)
            return eta_t.strftime("%H:%M")
    except Exception as e:
        logger.debug("ETA preview computation skipped: %s", e)
    return None

@login_required
def register_patient_view(request):
    hospital = request.user.hospital
    today = now().date()
    eta_preview = None  # <- will pass this to the template as 'eta'

    if request.method == 'POST':
        post = request.POST.copy()
        # Default/normalize dates (handles missing picker)
        def _norm_date(s, default_iso):
            if not s:
                return default_iso
            for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt).date().isoformat()
                except ValueError:
                    pass
            return s

        post.setdefault('payment-paid_on', today.isoformat())
        post['appointment-appointment_on'] = _norm_date(post.get('appointment-appointment_on'), today.isoformat())

        patient_form     = PatientRegistrationForm(post, prefix='patient')
        appointment_form = AppointmentForm(post, prefix='appointment', hospital_id=hospital.id)
        payment_form     = PaymentMasterForm(post, prefix='payment')
        txn_form         = PaymentTransactionForm(post, prefix='txn', hospital_id=hospital.id)

        # Compute ETA preview even if some forms are invalid
        eta_preview = _compute_eta_preview(appointment_form, hospital, post_data=post)

        if (patient_form.is_valid() and appointment_form.is_valid()
            and payment_form.is_valid() and txn_form.is_valid()):
            try:
                with transaction.atomic():
                    contact, patient = patient_form.save(hospital=hospital)

                    pay = payment_form.save(commit=False)
                    pay.patient      = patient
                    pay.mobile_num   = contact.mobile_num
                    pay.hospital     = hospital
                    pay.total_amount = Decimal('0.00')
                    pay.save()

                    txn = txn_form.save(commit=False)
                    txn.patient  = patient
                    txn.payment  = pay
                    txn.hospital = hospital
                    txn.doctor   = appointment_form.cleaned_data['doctor']
                    txn.paid_on  = pay.paid_on
                    txn.save()

                    total = PaymentTransaction.objects.filter(payment=pay)\
                                .aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                    if pay.total_amount != total:
                        pay.total_amount = total
                        pay.save(update_fields=['total_amount'])

                    appt_obj = appointment_form.save(commit=False)
                    appt_obj.patient    = patient
                    appt_obj.mobile_num = contact.mobile_num
                    appt_obj.hospital   = hospital
                    appt_obj.payment    = pay
                    appt_obj.token_num  = generate_token_string()
                    appt_obj.que_pos    = get_next_queue_position(
                        doctor=appt_obj.doctor,
                        date=appt_obj.appointment_on,
                        hospital=hospital
                    )
                    doc = appt_obj.doctor
                    appt_obj.eta = calculate_eta_time(
                        doc.start_time,
                        doc.average_time_minutes,
                        appt_obj.que_pos,
                        appointment_on=appt_obj.appointment_on
                    )
                    # Use your actual status/boolean:
                    appt_obj.status = AppointmentDetails.STATUS_REGISTERED
                    # appt_obj.completed = False
                    appt_obj.save()

                messages.success(request, "✅ Patient registration completed successfully.")
                try:
                    return redirect(reverse('patients:view', args=[patient.pk]))
                except Exception:
                    return redirect('patients:detail', pk=patient.pk)

            except Exception as e:
                logger.exception("Error during patient registration/save")
                messages.error(request, f"❌ An error occurred while saving: {e}")
        else:
            # surface errors to logs (and optionally to UI)
            def _err(f): return {k: [str(e) for e in v] for k, v in f.errors.items()}
            logger.warning("Form validation failed: patient=%s, appt=%s, pay=%s, txn=%s",
                           _err(patient_form), _err(appointment_form), _err(payment_form), _err(txn_form))
            messages.error(request, "❌ Please correct the errors below.")
    else:
        # GET: blank forms + ETA preview (if doctor initial is set)
        patient_form     = PatientRegistrationForm(prefix='patient')
        appointment_form = AppointmentForm(prefix='appointment', hospital_id=hospital.id)
        payment_form     = PaymentMasterForm(prefix='payment')
        txn_form         = PaymentTransactionForm(prefix='txn', hospital_id=hospital.id)

        eta_preview = _compute_eta_preview(appointment_form, hospital)

    return render(request, 'patients/register.html', {
        'patient_form':        patient_form,
        'appointment_form':    appointment_form,
        'payment_form':        payment_form,
        'transaction_form':    txn_form,
        'is_edit':             False,
        'eta':                 eta_preview,   # ← back in the context
    })


# --- 2. Edit Existing Patient ---
@login_required
def edit_patient_view(request, patient_id):
    eta_preview = None  
    hospital = request.user.hospital
    today    = date.today()
    patient  = get_object_or_404(Patient, pk=patient_id, hospital=hospital)
    contact  = patient.contact
    appt     = AppointmentDetails.objects.filter(patient=patient, hospital=hospital).order_by('-appointment_on').first()
    payment  = appt.payment if appt and appt.payment else None
    txn      = PaymentTransaction.objects.filter(payment=payment).first() if payment else None

    if request.method == 'POST':
        post = request.POST.copy()
        post.setdefault('payment-paid_on', today.isoformat())
        post.setdefault('appointment-appointment_on', today.isoformat())
        patient_form     = PatientRegistrationForm(post, prefix='patient')
        appointment_form = AppointmentForm(post, prefix='appointment', instance=appt, hospital_id=hospital.id)
        payment_form     = PaymentMasterForm(post, prefix='payment', instance=payment)
        txn_form         = PaymentTransactionForm(post, prefix='txn', instance=txn, hospital_id=hospital.id)
        eta_preview = _compute_eta_preview(appointment_form, hospital, post_data=post)
        if (patient_form.is_valid() and appointment_form.is_valid()
            and payment_form.is_valid() and txn_form.is_valid()):
            try:
                with transaction.atomic():
                    contact, patient = patient_form.save(hospital=hospital)
                    pay = payment_form.save(commit=False)
                    pay.patient      = patient
                    pay.mobile_num   = contact.mobile_num
                    pay.hospital     = hospital
                    pay.total_amount = Decimal(0)
                    pay.save()
                    

                    # Single PaymentTransaction
                    txn = txn_form.save(commit=False)
                    txn.patient  = patient
                    txn.payment  = pay
                    txn.hospital = hospital
                    txn.doctor   = appointment_form.cleaned_data['doctor']
                    txn.paid_on  = pay.paid_on
                    txn.save()

                    pay.total_amount += txn.amount
                    pay.save()
                    appt_obj = appointment_form.save(commit=False)
                    appt_obj.patient    = patient
                    appt_obj.mobile_num = contact.mobile_num
                    appt_obj.hospital   = hospital
                    appt_obj.payment    = pay
                    if not appt_obj.token_num:
                        appt_obj.token_num = generate_token_string()
                    if not appt_obj.que_pos:
                        appt_obj.que_pos = get_next_queue_position(
                            doctor=appt_obj.doctor,
                            date=appt_obj.appointment_on,
                            hospital=hospital
                        )
                    doc = Doctor.objects.get(pk=appt_obj.doctor.pk)
                    appt_obj.eta = calculate_eta_time(
                        doc.start_time,
                        doc.average_time_minutes,
                        appt_obj.que_pos,
                        appointment_on=appt_obj.appointment_on  # <-- important
                    )
                    
                    appt_obj.completed = appt.completed if appt else AppointmentDetails.STATUS_REGISTERED
                    appt_obj.save()
                messages.success(request, "✅ Patient Updated  successfully.")
                return redirect(reverse('patients:view', args=[patient.pk]))
            except Exception:
                messages.error(request, "❌ An error occurred while saving.")
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        initial = {
            'mobile_num':   contact.mobile_num,
            'contact_name': contact.contact_name,
            'patient_name': patient.patient_name,
            'age_years':    patient.age_years,
            'age_months':   patient.age_months,
            'gender':       patient.gender,
            'referred_by':  patient.referred_by,
        }
        patient_form     = PatientRegistrationForm(initial=initial, prefix='patient')
        appointment_form = AppointmentForm(prefix='appointment', instance=appt, hospital_id=hospital.id)
        payment_form     = PaymentMasterForm(prefix='payment', instance=payment)
        txn_form         = PaymentTransactionForm(prefix='txn', instance=txn, hospital_id=hospital.id)
        eta_preview = _compute_eta_preview(appointment_form, hospital, post_data=post)
    return render(request, 'patients/register.html', {
        'patient_form':        patient_form,
        'appointment_form':    appointment_form,
        'payment_form':        payment_form,
        'transaction_form':    txn_form,
        'is_edit':             True,
        'patient':             patient,
        'eta': eta_preview,
    })



# --- 3. View Patient (and Print) ---
@login_required
def view_patient_view(request, patient_id):
    hospital = request.user.hospital
    patient  = get_object_or_404(Patient, pk=patient_id, hospital=hospital)
    appointments = AppointmentDetails.objects.filter(patient=patient, hospital=hospital).select_related('doctor', 'payment')
    payments     = [appt.payment for appt in appointments if appt.payment]
    contact      = patient.contact
    latest_appt  = appointments.first()
    context = {
        'patient':      patient,
        'contact':      contact,
        'appointments': appointments,
        'payments':     payments,
        'latest_appt_id': latest_appt.pk if latest_appt else None,
        'can_edit':     True,   # for showing 'Edit' button
        'can_print':    True,   # for showing print/download buttons
    }
    return render(request, 'patients/view.html', context)



@login_required
def patient_dashboard(request):
    hospital = request.user.hospital
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '')

    patients = Patient.objects.filter(hospital=hospital).select_related('contact')

    # Build latest doctor mapping (kept as-is)
    appts = (
        AppointmentDetails.objects.filter(hospital=hospital)
        .order_by('patient_id', '-appointment_on')
        .select_related('doctor')
    )
    latest_doctor = {}
    for appt in appts:
        if appt.patient_id not in latest_doctor:
            latest_doctor[appt.patient_id] = appt.doctor.doctor_name

    # Search
    if q:
        patients = patients.filter(
            Q(patient_name__icontains=q) |
            Q(contact__mobile_num__icontains=q) |
            Q(contact__contact_name__icontains=q)
        )

    patients = list(patients.order_by('-id')[:100])

    # Sort by latest doctor (client asked for this)
    if sort == 'doctor':
        patients.sort(key=lambda p: latest_doctor.get(p.id, '').lower())

    ctx = {
        'patients': patients,
        'latest_doctor': latest_doctor,
        'q': q,
        'sort': sort,
    }

    # If AJAX, return rows only
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'patients/_rows.html', ctx)

    return render(request, 'patients/dashboard.html', ctx)


# --- Print/Receipt APIs (unchanged) ---

@login_required
def cash_receipt_pdf(request, appointment_id):
    appt = get_object_or_404(
        AppointmentDetails.objects.select_related('hospital', 'patient__contact', 'doctor', 'payment'),
        pk=appointment_id,
        hospital=request.user.hospital
    )
    # --- Defensive: Ensure there is a payment object ---
    if not appt.payment:
        return HttpResponse("No payment record found for this appointment.", status=404)

    context = {
        'hospital': appt.hospital,
        'patient':  appt.patient,
        'doctor':   appt.doctor,
        'amount':   appt.payment.total_amount,
    }
    pdf_bytes = render_to_pdf('pdf_templates/cash_receipt.html', context)
    if not pdf_bytes:
        return HttpResponse("Error generating receipt", status=500)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=\"receipt_{appt.pk}.pdf\"'
    return response


@login_required 
def token_pdf(request, appointment_id):
    appt = get_object_or_404(
        AppointmentDetails.objects.select_related('hospital', 'patient__contact', 'doctor'),
        pk=appointment_id,
        hospital=request.user.hospital
    )

    # Optional: Defensive check (not strictly needed)
    if not appt.token_num:
        return HttpResponse("No token number found for this appointment.", status=404)

    context = {
        'hospital': appt.hospital,
        'patient':  appt.patient,
        'token':    appt.token_num,
        'que_pos':  appt.que_pos,
        'doctor':   appt.doctor,
    }

    pdf_bytes = render_to_pdf('pdf_templates/queue_token.html', context)
    if not pdf_bytes:
        return HttpResponse("Error generating token", status=500)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="token_{appt.pk}.pdf"'
    return response

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
