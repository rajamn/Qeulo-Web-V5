from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from datetime import date
from appointments.models import AppointmentDetails
from prescription.models import PrescriptionMaster
from django.shortcuts import render, get_object_or_404
from core.models import HospitalUser
from doctors.models import Doctor
from django.db.models import OuterRef, Subquery, Case, When, IntegerField
from core.decorators import doctor_required,hospital_admin_required

@doctor_required
def doctor_dashboard(request):
    doctor = getattr(request.user, "doctor", None)
    if not doctor:
        return redirect("queue")

    today = date.today()

    # Subquery to fetch last prescription for each patient
    last_rx_subquery = (
        PrescriptionMaster.objects
        .filter(
            patient=OuterRef("patient"),
            doctor=doctor,
            hospital=doctor.hospital
        )
        .order_by("-prescribed_on")
        .values("id")[:1]
    )

    base_qs = (
        AppointmentDetails.objects
        .filter(doctor=doctor, appointment_on=today)
        .select_related("patient")
        .annotate(last_rx_id=Subquery(last_rx_subquery))
    )

    # Ordering logic: In Queue (0) → Registered (-1) → Completed (1)
    appointments = (
        base_qs
        .annotate(
            sort_order=Case(
                When(completed=0, then=0),  # In Queue
                When(completed=-1, then=1), # Registered
                When(completed=1, then=2),  # Completed
                default=3,
                output_field=IntegerField(),
            )
        )
        .order_by("sort_order", "que_pos")
    )

    # Recent 10 prescriptions
    recent_rx = (
        PrescriptionMaster.objects
        .filter(doctor=doctor)
        .select_related("patient")
        .order_by("-prescribed_on")[:10]
    )

    stats = {
        "registered": base_qs.filter(completed=-1).count(),
        "in_queue": base_qs.filter(completed=0).count(),
        "completed": base_qs.filter(completed=1).count(),
        "pending": base_qs.filter(completed__in=[-1, 0]).count(),
        "total_today": base_qs.count(),
    }

    return render(
        request,
        "doctors/dashboard.html",
        {
            "doctor": doctor,
            "appointments": appointments,
            "recent_rx": recent_rx,
            "stats": stats,
        }
    )



@login_required
def get_doctor_fee(request, doctor_id):
    """
    Returns consultation fee for the selected doctor.
    Used by Patient Registration screen.
    """
    try:
        doctor = Doctor.objects.get(id=doctor_id, hospital=request.user.hospital)
        return JsonResponse({"fee": doctor.fees}, status=200)
    except Doctor.DoesNotExist:
        return JsonResponse({"fee": 0}, status=404)



def doctor_list(request):
    doctors = Doctor.objects.filter(hospital=request.user.hospital)
    return render(request, "doctors/list.html", {"doctors": doctors})

def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor, pk=doctor_id, hospital=request.user.hospital)
    return render(request, "doctors/detail.html", {"doctor": doctor})
