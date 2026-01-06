import logging
from appointments.models import AppointmentDetails
from doctors.models import Doctor
from datetime import datetime, date, time, timedelta
import logging


def _parse_date_flexible(d) -> date:
    if isinstance(d, date):
        return d
    if not d:
        return date.today()
    s = str(d).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # fallback: today
    return date.today()


def normalize_time_input(start_time_input) -> time:
    """
    Converts input to a clean time object.
    Handles:
      - time object
      - string in formats like '9:30', '09:30 AM', '0930', etc.
    """
    if isinstance(start_time_input, time):
        return start_time_input.replace(second=0, microsecond=0)
    
    if not start_time_input:
        return time(18, 0)  # fallback
    
    s = str(start_time_input).strip()

    for fmt in ("%H:%M", "%I:%M %p", "%H.%M", "%I.%M %p", "%H%M", "%I%M%p"):
        try:
            return datetime.strptime(s, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            continue

    # If nothing works, log and return fallback
    logging.getLogger(__name__).warning(f"⚠️ Unable to parse start_time: {s}")
    return time(18, 0)


def round_time_to_nearest_5min(t: time) -> time:
    dt = datetime.combine(date.today(), t)
    minutes = (dt.minute + 2) // 5 * 5
    rounded = dt.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)
    return rounded.time()

def calculate_eta_time(start_time_input, avg_minutes, que_pos, appointment_on=None) -> time | None:
    """
    Calculate ETA for a given doctor, average time, and queue position.
    Returns a time object rounded to nearest 5 minutes or None on failure.
    """
    try:
        start_time = normalize_time_input(start_time_input)
        appt_date = _parse_date_flexible(appointment_on)
        now = datetime.now()

        # Validate and coerce to int safely
        avg_minutes = int(avg_minutes)
        que_pos = int(que_pos)
        if avg_minutes <= 0 or que_pos < 0:
            raise ValueError("Invalid avg_minutes or que_pos")

        effective_start = max(now.time(), start_time) if appt_date == now.date() else start_time
        base = datetime.combine(appt_date, effective_start)
        eta = base + timedelta(minutes=avg_minutes * que_pos)
        return round_time_to_nearest_5min(eta.time().replace(second=0, microsecond=0))

    except Exception as e:
        logging.getLogger(__name__).warning(f"⚠️ ETA calculation failed: {e}")
        return None


def predict_eta_for_registration(doctor, hospital, appointment_on=None):
    """
    Predict ETA and queue length for a new patient registering with the given doctor.
    Works entirely in local time (no UTC).
    If appointment_on is today, includes both REGISTERED and IN_QUEUE patients.
    """
    try:
        from appointments.models import AppointmentDetails

        appt_date = appointment_on or date.today()
        today = date.today()

        # Determine which statuses to include
        if appt_date == today:
            status_filter = [AppointmentDetails.STATUS_REGISTERED, AppointmentDetails.STATUS_IN_QUEUE]
        else:
            status_filter = [AppointmentDetails.STATUS_REGISTERED]

        # Count patients still waiting
        queued = AppointmentDetails.objects.filter(
            doctor=doctor,
            hospital=hospital,
            appointment_on=appt_date,
            completed__in=status_filter
        ).count()

        # Compute ETA based on queue position
        eta = calculate_eta_time(
            doctor.start_time,
            doctor.average_time_minutes,
            queued + 1,             # next patient
            appointment_on=appt_date
        )

        return eta, queued

    except Exception as e:
        logging.getLogger(__name__).warning(f"⚠️ ETA prediction failed: {e}")
        return None, 0
