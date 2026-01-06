from django.http import JsonResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Sum
from django.utils.dateparse import parse_date, parse_datetime
from datetime import date, datetime
from appointments.utils import get_next_queue_position
from appointments.models import AppointmentDetails
from billing.utils import get_patient_queryset
from utils.eta_calculator import calculate_eta_time
from doctors.models import Doctor
from patients.models import Contact, Patient
from core.models import Hospital
from decimal import Decimal, ROUND_HALF_UP
import random
from xhtml2pdf import pisa
import string
import io
import logging


logger = logging.getLogger(__name__)

def generate_token_string(length=4):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def render_to_pdf(template_src, context):
    """
    Render given template with context to a PDF (bytes).
    Returns bytes or None on error.
    """
    template = get_template(template_src)
    html     = template.render(context)
    result   = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result)
    return result.getvalue() if not pdf.err else None



def _safe(post, prefix, keys):
    # show only a safe subset so you don’t leak PII
    data = {k: post.get(f"{prefix}-{k}") for k in keys}
    return ", ".join(f"{k}={v!r}" for k, v in data.items())


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
            que_pos_for_eta = que_pos-completed_count
            eta_t = calculate_eta_time(doc.start_time, doc.average_time_minutes, que_pos_for_eta, appointment_on=appt_date)
            return eta_t if eta_t else None

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
            pos_data = get_next_queue_position(doc, date.today(), hospital)
            que_pos = pos_data["next_pos"]
            completed_count = pos_data["completed_count"]
            que_pos_for_eta = que_pos-completed_count
            eta_t = calculate_eta_time(doc.start_time, doc.average_time_minutes, que_pos_for_eta, appointment_on=appt_date)
            return eta_t if eta_t else None
    except Exception as e:
        logger.debug("ETA preview computation skipped: %s", e)
    return None

def _render_register(request, hospital, post, *, 
                     patient_form, appointment_form, txn_form, 
                     focus: str):
    eta = _compute_eta_preview(appointment_form, hospital, post_data=post)
    return render(request, 'patients/register.html', {
        'patient_form':      patient_form,
        'appointment_form':  appointment_form,
        'transaction_form':  txn_form,
        'is_edit':           False,
        'eta':               eta,
        'focus':             focus,   # <-- tell template which block to emphasize
    })


def _amount_in_words_inr(amount: Decimal) -> str:
    """
    Convert Decimal amount to Indian currency words:
    e.g., 1234.50 -> 'Rupees One Thousand Two Hundred Thirty Four and Fifty Paise only'
    No external deps to avoid server surprises.
    """
    # Split rupees/paise safely
    amt = (amount or Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rupees = int(amt)
    paise  = int((amt - Decimal(rupees)) * 100)

    def _num_to_words(n: int) -> str:
        # Minimal Indian numbering words (0..99, hundreds, thousands, lakhs, crores)
        ones = ["Zero","One","Two","Three","Four","Five","Six","Seven","Eight","Nine",
                "Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen","Seventeen","Eighteen","Nineteen"]
        tens = ["","", "Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"]

        def two(x):
            if x < 20: return ones[x]
            t, o = divmod(x, 10)
            return tens[t] + ("" if o == 0 else " " + ones[o])

        def three(x):
            h, rem = divmod(x, 100)
            if h and rem:  return ones[h] + " Hundred " + two(rem)
            if h and not rem: return ones[h] + " Hundred"
            return two(rem)

        if n == 0: return "Zero"

        parts = []
        crore, n = divmod(n, 10_000_000)
        if crore:   parts.append(two(crore) + " Crore")
        lakh, n = divmod(n, 100_000)
        if lakh:    parts.append(two(lakh) + " Lakh")
        thousand, n = divmod(n, 1000)
        if thousand: parts.append(two(thousand) + " Thousand")
        if n: parts.append(three(n))
        return " ".join(parts)

    words = f"Rupees {_num_to_words(rupees)}"
    if paise:
        words += f" and { _num_to_words(paise) } Paise"
    words += " only"
    return words

def _queue_position_for(appt):
    # 1) Use stored position if present
    stored = getattr(appt, "que_pos", None)
    if stored not in (None, "", 0):
        return stored

    # 2) Base: same doctor, hospital, date
    qs = AppointmentDetails.objects.filter(
        doctor=appt.doctor,
        hospital=appt.hospital,
        appointment_on=appt.appointment_on,
    )

    # 3) Active only: not completed (handle bool or datetime)
    qs = qs.filter(Q(completed=False) | Q(completed__isnull=True))

    # Optional: if you want only not-yet-called, also add:
    # qs = qs.filter(Q(called=False) | Q(called__isnull=True))

    # 4) Count people ahead using canonical ordering
    if getattr(appt, "token_num", None):
        ahead = qs.filter(
            Q(token_num__lt=appt.token_num)
            | (Q(token_num=appt.token_num) & Q(pk__lt=appt.pk))  # tie-break
        ).count()
    else:
        ahead = qs.filter(
            Q(created_at__lt=appt.created_at)
            | (Q(created_at=appt.created_at) & Q(pk__lt=appt.pk))  # tie-break
        ).count()

    return ahead + 1  # position in line (drop +1 if you only want "ahead")


def _fmt_date(value):
    """Return '10 Sep 2025' style string from date/datetime/ISO string;
       return None if nothing usable."""
    if not value and value != 0:
        return None
    # Handle strings like '2025-09-10' or '2025-09-10T11:00:00Z'
    if isinstance(value, str):
        dt = parse_datetime(value) or parse_date(value)
        if dt is None:
            # If it's some other string, just return it as-is
            return value
        value = dt
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d %b %Y")
    # Fallback: stringify
    try:
        return str(value)
    except Exception:
        return None

def _appointment_date_str(appt):
    """Try appointment_on → eta → created_at → today."""
    for candidate in (
        getattr(appt, "appointment_on", None),
        getattr(appt, "eta", None),
        getattr(appt, "created_at", None),
        date.today(),
    ):
        s = _fmt_date(candidate)
        if s:
            return s
    return "-"



# patients/views.py





  # ✅ reuse your existing helper


logger = logging.getLogger(__name__)

def patient_lookup_public(request, slug=None):
    """
    Public (no login required) patient lookup used in self-registration page.
    Example URL: /h/<slug>/api/patient_lookup/?mobile=9876543210
    """
    try:
        mobile = (request.GET.get("mobile") or "").strip()
        if not mobile:
            return JsonResponse({"found": False, "error": "Mobile number required"})

        hospital = get_object_or_404(Hospital, slug=slug)

        qs = get_patient_queryset(hospital, mobile)
        p = qs.first()
        if not p:
            return JsonResponse({"found": False})

        return JsonResponse({
            "found": True,
            "id": p.id,
            "name": p.patient_name,
            "mobile": str(p.contact.mobile_num),
            "age_years": p.age_years,
            "age_months": p.age_months,
            "gender": p.gender,
            "referred_by": p.referred_by or "",
        })

    except Exception as e:
        logger.exception("❌ Patient lookup failed for hospital slug=%s", slug)
        return JsonResponse({"found": False, "error": str(e)}, status=500)

# patients/utils.py

# patients/utils.py
def perform_patient_search(hospital, query, limit=20):
    """
    Reusable search logic for patients by name, mobile, or patient_id.
    """
    if not query:
        return Patient.objects.none()

    qs = Patient.objects.filter(hospital=hospital).select_related("contact")
    tokens = [t for t in query.split() if t]
    digits = "".join(ch for ch in query if ch.isdigit())
    prefix = hospital.hospital_name[:3].upper()

    # --- Name search ---
    name_q = Q()
    for t in tokens:
        if len(t) >= 3:
            name_q &= Q(patient_name__icontains=t)

    # --- Mobile search ---
    mobile_q = Q()
    if len(digits) >= 3:
        mobile_q = Q(contact__mobile_num__icontains=digits)

    # --- Patient ID search (e.g. PRA-00042 or 42) ---
    id_q = Q()
    # remove prefix and dash if present
    stripped = query.replace(prefix, "").replace("-", "").strip()
    if stripped.isdigit():
        id_q = Q(id=int(stripped))

    # Combine all
    return qs.filter(name_q | mobile_q | id_q).order_by("patient_name")[:limit]
