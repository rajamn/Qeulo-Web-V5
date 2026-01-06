from datetime import datetime, timedelta,time
from appointments.models import AppointmentDetails
from django.db.models import Max


def get_registration_queue_position(doctor, date, hospital):
    """
    Returns next queue position when a new patient is REGISTERED.
    Logic: count all appointments for doctor/date/hospital + 1
    """
    total_count = AppointmentDetails.objects.filter(
        doctor=doctor,
        appointment_on=date,
        hospital=hospital,
    ).count()

    return {
        "next_pos": total_count + 1,
        "total_count": total_count,
    }

from datetime import date as dt_date

def get_next_queue_position(doctor, date, hospital):
    """
    Returns next queue position and completed count for a doctor
    restricted to a given date (default today).
    Queue position is calculated as (in_queue_count + completed_count + 1).
    """

    # appt_date = appt_date or dt_date.today()

    # How many are in queue
    in_queue_count = AppointmentDetails.objects.filter(
        doctor=doctor,
        appointment_on=date,
        hospital=hospital,
        completed=AppointmentDetails.STATUS_IN_QUEUE,
    ).count()

    # How many are already completed
    completed_count = AppointmentDetails.objects.filter(
        doctor=doctor,
        appointment_on=date,
        hospital=hospital,
        completed=AppointmentDetails.STATUS_DONE,
    ).count()

    next_pos = in_queue_count + completed_count + 1

    return {
        "next_pos": next_pos,
        "completed_count": completed_count,
    }
