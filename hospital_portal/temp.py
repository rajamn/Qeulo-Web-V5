from decimal import Decimal
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q, Sum
logger = logging.getLogger(__name__)
# hospital_portal/views.py
from datetime import date
from billing.forms.self_registration import SelfPaymentTransactionForm
from billing.models import PaymentTransaction, PaymentMaster
from appointments.models import AppointmentDetails
from appointments.forms import AppointmentForm
from core.models import Hospital
from patients.forms import PatientRegistrationForm
from patients.utils import generate_token_string
from appointments.utils import get_registration_queue_position
from utils.eta_calculator import calculate_eta_time
import logging

def self_register_view(request, slug=None):
    # ----- Setup / context -----
    appt_obj = None  # <-- prevent NameError later
    if slug:
        hospital = get_object_or_404(Hospital, slug=slug)
        is_public = True
    else:
        if not request.user.is_authenticated:
            return redirect('/login/')
        # Guard: some users may not have hospital attached
        hospital = getattr(request.user, "hospital", None)
        if hospital is None:
            messages.error(request, "No hospital is linked to your account.")
            return redirect('/login/')
        is_public = False

    today = date.today()

    if request.method == 'POST':
        post = request.POST.copy()
        post.setdefault('appointment-appointment_on', today.isoformat())

        patient_form     = PatientRegistrationForm(post, prefix='patient')
        appointment_form = AppointmentForm(post, prefix='appointment', hospital_id=hospital.id)
        txn_form         = SelfPaymentTransactionForm(post, prefix='txn', hospital_id=hospital.id, public=is_public)

        if patient_form.is_valid() and appointment_form.is_valid() and txn_form.is_valid():
            try:
                with transaction.atomic():
                    # 1) Patient + contact
                    contact, patient = patient_form.save(hospital=hospital)

                    # 2) Payment master
                    pay = PaymentMaster(
                        paid_on      = appointment_form.cleaned_data["appointment_on"],
                        mobile_num   = contact.mobile_num,
                        patient      = patient,
                        hospital     = hospital,
                        # If FK: collected_by=request.user if request.user.is_authenticated else None
                        collected_by = getattr(request.user, "user_name", "Online") if not is_public else "Online",
                        total_amount = Decimal("0.00"),
                    )
                    pay.full_clean()
                    pay.save()

                    # 3) Payment transaction (dedupe)
                    txn = txn_form.save(commit=False)
                    txn.patient  = patient
                    txn.payment  = pay
                    txn.hospital = hospital
                    txn.doctor   = appointment_form.cleaned_data["doctor"]
                    txn.service  = txn_form.cleaned_data["service"]
                    txn.amount   = txn_form.cleaned_data["amount"]
                    txn.paid_on  = pay.paid_on

                    existing_txn = PaymentTransaction.objects.filter(
                        patient=patient, doctor=txn.doctor, service=txn.service,
                        hospital=hospital, paid_on=txn.paid_on
                    ).first()
                    if existing_txn:
                        logger.warning("Duplicate PaymentTransaction detected, reusing existing one.")
                        txn = existing_txn
                    else:
                        txn.save()

                    # 4) Recalc master total (keep inside atomic)
                    total = PaymentTransaction.objects.filter(payment=pay)\
                            .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
                    pay.total_amount = total
                    pay.save(update_fields=["total_amount"])

                    # 5) Appointment
                    appt_obj = appointment_form.save(commit=False)
                    appt_obj.doctor      = appointment_form.cleaned_data['doctor']
                    appt_obj.patient     = patient
                    appt_obj.mobile_num  = contact.mobile_num
                    appt_obj.hospital    = hospital
                    appt_obj.payment     = pay
                    appt_obj.token_num   = generate_token_string()

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

                    # 6) Final consistency (optional)
                    final_total = PaymentTransaction.objects.filter(payment=pay)\
                                   .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
                    if final_total != pay.total_amount:
                        pay.total_amount = final_total
                        pay.save(update_fields=["total_amount"])

                messages.success(request, "✅ Patient registration completed successfully.")
                return redirect(f"/h/{hospital.slug}/display/") if is_public else redirect(
                    reverse('patients:view', args=[patient.pk])
                )

            except Exception as e:
                logger.exception("❌ Error during patient registration/save")
                messages.error(request, f"❌ An error occurred while saving: {e}")

        else:
            def _errors(form): return {k: [str(e) for e in v] for k, v in form.errors.items()}
            logger.warning(
                "Form validation failed: patient=%s, appointment=%s, txn=%s",
                _errors(patient_form), _errors(appointment_form), _errors(txn_form)
            )
            messages.error(request, "❌ Please correct the errors below.")
    else:
        # GET
        patient_form     = PatientRegistrationForm(prefix='patient')
        appointment_form = AppointmentForm(prefix='appointment', hospital_id=hospital.id)
        txn_form         = SelfPaymentTransactionForm(prefix='txn', hospital_id=hospital.id, public=is_public)

    # ---- Safe context build (no NameError) ----
    eta_value        = getattr(appt_obj, "eta", None)
    que_pos          = getattr(appt_obj, "que_pos", None)
    consultation_fee = getattr(txn_form, 'consultation_fee', Decimal("0.00"))
    total_amount     = consultation_fee

    return render(request, 'hospital_portal/self_register.html', {
        'patient_form': patient_form,
        'appointment_form': appointment_form,
        'transaction_form': txn_form,
        'is_edit': False,
        'eta': eta_value,
        'que_pos': que_pos,
        'slug_mode': is_public,
        'hospital': hospital,
        'consultation_fee': consultation_fee,
        'total_amount': total_amount,
    })
