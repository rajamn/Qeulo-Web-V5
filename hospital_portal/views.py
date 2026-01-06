from decimal import Decimal
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q, Sum
from django.http import JsonResponse

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
from utils.eta_calculator import predict_eta_for_registration
from doctors.models import Doctor
from datetime import datetime

import logging


def hospital_root_redirect(request, slug):
    """
    Redirect /h/<slug>/ → /h/<slug>/login/ if valid hospital exists,
    otherwise redirect to standard /login/.
    """
    if Hospital.objects.filter(slug=slug).exists():
        return redirect("hospital_login", slug=slug)
    return redirect("login")

def slug_root_redirect(request, slug):
    # send unauthenticated users to branded login
    return redirect("hospital_portal:hospital_login", slug=slug)


logger = logging.getLogger(__name__)

def self_register_view(request, slug=None):
    """
    Handles both staff (logged-in) and public (slug-based) registration.
    If slug is provided, registration defaults to DUE payment.
    """
    appt_obj = None

    # --- 1️⃣ Determine hospital context ---
    if slug:
        hospital = get_object_or_404(Hospital, slug=slug)
        is_public = True
    else:
        if not request.user.is_authenticated:
            return redirect("/login/")
        hospital = getattr(request.user, "hospital", None)
        if hospital is None:
            messages.error(request, "No hospital is linked to your account.")
            return redirect("/login/")
        is_public = False

    today = date.today()

    # --- 2️⃣ Handle POST submission ---
    if request.method == "POST":
        post = request.POST.copy()
        post.setdefault("appointment-appointment_on", today.isoformat())

        patient_form = PatientRegistrationForm(post, prefix="patient")
        appointment_form = AppointmentForm(post, prefix="appointment", hospital_id=hospital.id)
        txn_form = SelfPaymentTransactionForm(
            post, prefix="txn", hospital_id=hospital.id, public=is_public
        )

        if all([patient_form.is_valid(), appointment_form.is_valid(), txn_form.is_valid()]):
            try:
                with transaction.atomic():
                    # ✅ Step 1: Save Contact & Patient
                    contact, patient = patient_form.save(hospital=hospital)

                    # ✅ Step 2: Create PaymentMaster
                    pay = PaymentMaster.objects.create(
                        paid_on=appointment_form.cleaned_data["appointment_on"],
                        mobile_num=contact.mobile_num,
                        patient=patient,
                        hospital=hospital,
                        collected_by=(
                            getattr(request.user, "user_name", "Online")
                            if not is_public else "Online"
                        ),
                        total_amount=Decimal("0.00"),
                    )

                    # ✅ Step 3: Create or reuse PaymentTransaction
                    txn = txn_form.save(commit=False)
                    txn.patient = patient
                    txn.payment = pay
                    txn.hospital = hospital
                    txn.doctor = appointment_form.cleaned_data["doctor"]
                    txn.service = txn_form.cleaned_data["service"]
                    txn.amount = txn_form.cleaned_data["amount"]
                    txn.paid_on = pay.paid_on

                    existing_txn = PaymentTransaction.objects.filter(
                        patient=patient,
                        doctor=txn.doctor,
                        service=txn.service,
                        hospital=hospital,
                        paid_on=txn.paid_on,
                    ).first()

                    if existing_txn:
                        logger.warning("⚠️ Duplicate PaymentTransaction detected; reusing existing one.")
                        txn = existing_txn
                    else:
                        txn.save()

                    # ✅ Step 4: Update PaymentMaster total
                    total = (
                        PaymentTransaction.objects.filter(payment=pay)
                        .aggregate(total=Sum("amount"))
                        .get("total") or Decimal("0.00")
                    )
                    pay.total_amount = total
                    pay.save(update_fields=["total_amount"])

                    # ✅ Step 5: Create AppointmentDetails
                    appt_obj = appointment_form.save(commit=False)
                    appt_obj.doctor = appointment_form.cleaned_data["doctor"]
                    appt_obj.patient = patient
                    appt_obj.mobile_num = contact.mobile_num
                    appt_obj.hospital = hospital
                    appt_obj.payment = pay
                    appt_obj.token_num = generate_token_string()

                    # Compute queue position
                    pos_data = get_registration_queue_position(
                        doctor=appt_obj.doctor,
                        date=appt_obj.appointment_on,
                        hospital=hospital,
                    )
                    appt_obj.que_pos = pos_data["next_pos"]

                    # Compute ETA using standard function
                    appt_obj.eta = calculate_eta_time(
                        appt_obj.doctor.start_time,
                        appt_obj.doctor.average_time_minutes,
                        appt_obj.que_pos,
                        appointment_on=appt_obj.appointment_on,
                    )
                    appt_obj.completed = AppointmentDetails.STATUS_REGISTERED
                    appt_obj.save()

                # ✅ Commit successful
                messages.success(request, "✅ Patient registration completed successfully.")
                if is_public:
                    return redirect(f"/h/{hospital.slug}/display/")
                return redirect(reverse("patients:view", args=[patient.pk]))

            except Exception as e:
                logger.exception("❌ Error during patient registration/save")
                messages.error(request, f"❌ An error occurred while saving: {e}")
        else:
            # Log form validation errors
            def _errs(f):
                return {k: [str(e) for e in v] for k, v in f.errors.items()}
            logger.warning(
                "❌ Validation failed: patient=%s appointment=%s txn=%s",
                _errs(patient_form),
                _errs(appointment_form),
                _errs(txn_form),
            )
            messages.error(request, "Please correct the errors below.")

    else:
        # --- 3️⃣ Handle GET (blank forms) ---
        patient_form = PatientRegistrationForm(prefix="patient")
        appointment_form = AppointmentForm(prefix="appointment", hospital_id=hospital.id)
        txn_form = SelfPaymentTransactionForm(
            prefix="txn", hospital_id=hospital.id, public=is_public
        )

    # --- 4️⃣ Render page ---
    eta_value = getattr(appt_obj, "eta", None)
    que_pos = getattr(appt_obj, "que_pos", None)
    consultation_fee = getattr(txn_form, "consultation_fee", Decimal("0.00"))

    return render(
        request,
        "hospital_portal/self_register.html",
        {
            "patient_form": patient_form,
            "appointment_form": appointment_form,
            "transaction_form": txn_form,
            "is_edit": False,
            "eta": eta_value,
            "que_pos": que_pos,
            "slug_mode": is_public,
            "hospital": hospital,
            "consultation_fee": consultation_fee,
        },
    )


# hospital_portal/views.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from core.models import Hospital
from doctors.models import Doctor
from appointments.models import AppointmentDetails
from utils.eta_calculator import calculate_eta_time
from datetime import date

def doctor_info_api(request, doctor_id, slug=None):
    """
    Returns doctor's current ETA and queue count.
    Works both for slug-based (/h/<slug>/api/...) and global (/api/...) routes.
    """
    try:
        # Determine hospital context
        if slug:
            hospital = get_object_or_404(Hospital, slug=slug)
        else:
            # fallback for receptionist login: derive from logged-in user
            if hasattr(request.user, "hospital") and request.user.hospital:
                hospital = request.user.hospital
            else:
                return JsonResponse({"error": "Hospital context not found"}, status=400)

        doctor = get_object_or_404(Doctor, id=doctor_id, hospital=hospital)

        today = date.today()
        queued = AppointmentDetails.objects.filter(
            doctor=doctor,
            appointment_on=today,
            completed=AppointmentDetails.STATUS_IN_QUEUE,  # 0
            hospital=hospital
        ).count()

        eta = calculate_eta_time(
            doctor.start_time,
            doctor.average_time_minutes,
            queued + 1,  # next patient
            appointment_on=today
        )

        return JsonResponse({
            "doctor": doctor.doctor_name,
            "queued": queued,
            "eta": eta.strftime("%H:%M") if eta else None
        })

    except Exception as e:
        import traceback, logging
        logging.getLogger(__name__).exception("❌ Doctor info API failed")
        return JsonResponse({"error": str(e)}, status=500)
