from django.db.models import Case, When, Value, IntegerField
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from datetime import datetime,date
from doctors.models import Doctor
from .forms import AppointmentFilterForm
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from utils.eta_calculator import calculate_eta_time
from appointments.utils import get_next_queue_position
from django.contrib import messages
from appointments.models import AppointmentDetails, AppointmentAuditLog
from core.models import Hospital
from whatsapp_notifications.models import WhatsappConfig
from whatsapp_notifications.services import send_whatsapp_template
from whatsapp_notifications.utils import send_reschedule_notifications
from django.db.models import Exists, OuterRef, Value, BooleanField
from billing.models import PaymentTransaction
from prescription.models import PrescriptionDraft

@login_required
def queue_dashboard(request):
    hospital = getattr(request.user, "hospital", None)
    today = date.today()

    # Base queryset: today's appointments
    qs = AppointmentDetails.objects.filter(appointment_on=today)
    
    if hospital:
        qs = qs.filter(hospital=hospital)

    # ---------------------------
    # Doctor view restriction
    # ---------------------------
    doctor_obj = getattr(request.user, "doctor", None)
    if doctor_obj:
        # Doctor sees ALL his patients (no status filter)
        qs = qs.filter(doctor=doctor_obj)
    # Admin/Receptionist sees all → no change

    # ---------------------------
    # Filters – applied ONLY for admin/receptionist
    # ---------------------------
    form = AppointmentFilterForm(request.GET or None, hospital=hospital)
    if form.is_valid() and not doctor_obj:
        doctor = form.cleaned_data.get("doctor")
        if doctor:
            qs = qs.filter(doctor=doctor)

        status = form.cleaned_data.get("status")
        if status != "":
            qs = qs.filter(completed=int(status))

        patient = form.cleaned_data.get("patient")
        if patient:
            qs = qs.filter(patient__patient_name__icontains=patient)

    # --------------------------------
    # Mark due (for highlighting)
    # --------------------------------
    due_subquery = PaymentTransaction.objects.filter(
        payment=OuterRef('payment'),
        pay_type='Due'
    )
    qs = qs.annotate(is_due=Exists(due_subquery))

    # --------------------------------
    # Order table rows
    # --------------------------------
    status_order = Case(
        When(completed=-1, then=Value(1)),  # Registered
        When(completed=0,  then=Value(2)),  # In Queue
        When(completed=1,  then=Value(3)),  # Completed
        When(completed=2,  then=Value(4)),  # Cancelled
        output_field=IntegerField(),
    )

    appointments = qs.select_related("doctor", "patient") \
                     .order_by(status_order, "que_pos")

    return render(request, "queue_mgt/queue.html", {
        "form": form,
        "appointments": appointments,
    })



def format_eta_window(eta_time):
    """Return a string like '06:00 PM – 06:30 PM' from a time object."""
    if not eta_time:
        return "N/A"
    from datetime import datetime, timedelta, date
    dt = datetime.combine(date.today(), eta_time)
    start = dt.replace(minute=(dt.minute // 30) * 30, second=0, microsecond=0)
    end = start + timedelta(minutes=30)
    return f"{start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p')}"




from datetime import datetime


def update_status(request, appoint_id, new_status):
    
    now_local = datetime.now()   # <-- NAIVE LOCAL TIME, SAFE WITH USE_TZ=False



    qs   = request.GET.urlencode()
    appt = get_object_or_404(AppointmentDetails, appoint_id=appoint_id)
    appt.queue_start_time = datetime.now()
    old_status = appt.completed
    appt.completed = new_status

    doctor   = appt.doctor
    patient  = appt.patient
    hospital = appt.hospital

    # 🚫 Prevent skipping queue
    if old_status == AppointmentDetails.STATUS_REGISTERED and new_status == AppointmentDetails.STATUS_DONE:
        messages.error(request, "⚠️ You must move the patient to Queue before marking as Completed.")
        return redirect(reverse("queue"))

    # 🚫 Prevent Completed → Cancelled
    if old_status == AppointmentDetails.STATUS_DONE and new_status == AppointmentDetails.STATUS_NO_SHOW:
        messages.error(request, "⚠️ A completed appointment cannot be cancelled.")
        return redirect(reverse("queue"))

    # ===============================
    # 1️⃣ REGISTERED → IN_QUEUE
    # ===============================
    if old_status == -1 and new_status == 0:

        # 🟦 Queue position
        pos_info = get_next_queue_position(
            doctor, 
            appt.appointment_on or date.today(), 
            hospital
        )
        appt.que_pos = pos_info["next_pos"]

        # 🟦 ETA calculation
        ahead = pos_info["next_pos"] - pos_info["completed_count"]
        appt.eta = calculate_eta_time(
            doctor.start_time,
            doctor.average_time_minutes,
            ahead,
            appt.appointment_on or date.today()
        )

        # ⭐ RECORD QUEUE START TIME (NATIVE TIME)
        if not appt.queue_start_time:
            appt.queue_start_time = datetime.now()
            


        # Audit
        AppointmentAuditLog.objects.create(
            hospital=hospital,
            appointment=appt,
            doctor=doctor,
            patient=patient,
            action="queued",
            token_num=appt.token_num,
            que_pos=appt.que_pos,
            eta=appt.eta,
        )
        # (WhatsApp logic unchanged)

    # ===============================
    # 2️⃣ IN_QUEUE → DONE
    # ===============================
    elif old_status == 0 and new_status == 1:

        # ⭐ RECORD COMPLETION TIME
        appt.completed_at = datetime.now()
        
        AppointmentAuditLog.objects.create(
            hospital=hospital,
            appointment=appt,
            doctor=doctor,
            patient=patient,
            action="completed",
            token_num=appt.token_num,
            que_pos=appt.que_pos,
            eta=appt.eta,
            completion_time=appt.completed_at,
        )

    # ===============================
    # 3️⃣ ANY → CANCELLED
    # ===============================
    elif new_status == 2:
        AppointmentAuditLog.objects.create(
            hospital=hospital,
            appointment=appt,
            doctor=doctor,
            patient=patient,
            action="cancelled",
            token_num=appt.token_num,
            que_pos=appt.que_pos,
            eta=appt.eta,
        )

    # ===============================
    # SAVE EVERYTHING
    # ===============================
    appt.save(update_fields=[
        "completed",
        "eta",
        "que_pos",
        "queue_start_time",
        "completed_at",
    ])

    # redirect
    base = reverse("queue")
    return redirect(f"{base}?{qs}") if qs else redirect(base)



 
# quelo_backend/views.py

def queue_display(request, slug=None):
    """
    Hybrid queue display view.
    - /display/ → staff version (login required)
    - /h/<slug>/display/ → hospital-specific public display
    """
    if slug:
        # Slug-based (public)
        hospital = get_object_or_404(Hospital, slug=slug)
    else:
        # Staff (requires login)
        if not request.user.is_authenticated:
            return redirect('/login/')
        hospital = getattr(request.user, 'hospital', None)

    if not hospital:
        return render(request, 'errors/no_hospital.html', status=404)

    today = date.today()
    appointments = (
        AppointmentDetails.objects
        .filter(hospital=hospital, appointment_on=today, completed=0)
        .select_related('doctor', 'patient')
        .order_by('doctor__doctor_name', 'que_pos')
    )

    return render(request, 'queue/queue_display.html', {
        'appointments': appointments,
        'hospital': hospital,
        'slug_mode': bool(slug),
    })




@require_POST
@login_required
def call_patient(request, appoint_id):
    appt = get_object_or_404(AppointmentDetails, appoint_id=appoint_id)
    appt.called = True
    appt.save(update_fields=['called'])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "ok"})
    else:
        qs = request.GET.urlencode()
        base = reverse("queue")
        return redirect(f"{base}?{qs}") if qs else redirect(base)

    qs = request.GET.urlencode()
    base = reverse('queue')
    return redirect(f"{base}?{qs}") if qs else redirect(base)




@login_required
def reschedule_page(request):
    hospital = request.user.hospital

    if request.method == "POST":
        doctor_id = request.POST.get("doctor_id")
        delay = int(request.POST.get("delay", 0))

        try:
            doctor = Doctor.objects.get(id=doctor_id, hospital=hospital)
            results = send_reschedule_notifications(hospital, doctor, delay)

            sent = sum(1 for r in results if r["status"] == "sent")
            failed = sum(1 for r in results if r["status"] == "failed")

            messages.success(request, f"Reschedule sent: {sent} messages, {failed} failed.")
            return redirect("queue")  # or stay on reschedule_page
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor not found.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

    doctors = Doctor.objects.filter(hospital=hospital, is_active=True)
    return render(request, "queue_mgt/reschedule.html", {"doctors": doctors})


