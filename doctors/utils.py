from datetime import date
from django.db.models import Case, When, IntegerField
from appointments.models import AppointmentDetails
from prescription.models import PrescriptionDraft



def get_doctor_today_context(doctor, limit_queue=3, limit_done=3):
    today = date.today()

    base_qs = (
        AppointmentDetails.objects
        .filter(doctor=doctor, appointment_on=today)
        .select_related("patient")
    )

    stats = {
        "total_today": base_qs.count(),
        "in_queue": base_qs.filter(completed=0).count(),
        "completed": base_qs.filter(completed=1).count(),
    }

    in_queue = (
        base_qs
        .filter(completed=0)
        .order_by("que_pos")[:limit_queue]
    )

    completed = (
        base_qs
        .filter(completed=1)
        .order_by("-completed_at")[:limit_done]
    )

    return {
        "stats": stats,
        "in_queue": in_queue,
        "completed": completed,
    }


# doctors/utils.py


def get_doctor_sidebar_ctx(user):
    if not hasattr(user, "doctor"):
        return None

    doctor = user.doctor
    today = date.today()

    in_queue = AppointmentDetails.objects.filter(
        doctor=doctor,
        appointment_on=today,
        completed=AppointmentDetails.STATUS_IN_QUEUE
    ).select_related("patient").order_by("que_pos")

    draft = (
        PrescriptionDraft.objects
        .filter(doctor=doctor, finalized=False)
        .order_by("-updated_at")
        .first()
    )

    return {
        "current_patient": getattr(draft, "patient", None),
        "next_patients": list(in_queue[1:3]),
        "all_queue": in_queue,
        "has_active_draft": bool(draft),
        "active_draft_id": draft.id if draft else None,
        "enable_discard": False,  
    }
