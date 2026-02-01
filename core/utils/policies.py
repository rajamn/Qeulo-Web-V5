# core/utils/policies.py
def get_consultation_policy(hospital, doctor=None):
    days = (doctor.consult_validity_days
            if doctor and doctor.consult_validity_days is not None
            else hospital.consult_validity_days)

    visits = (doctor.consult_validity_visits
              if doctor and doctor.consult_validity_visits is not None
              else hospital.consult_validity_visits)

    template = (doctor.consult_message_template or "").strip() if doctor else ""
    if not template:
        template = hospital.consult_message_template

    try:
        message = template.format(days=days, visits=visits)
    except Exception:
        message = f"Valid for {days} days or {visits} visits whichever is earlier"

    return {"days": days, "visits": visits, "message": message}
