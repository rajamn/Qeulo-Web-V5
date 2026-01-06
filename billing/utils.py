# billing/views.py
from datetime import date, datetime, timedelta, time
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404, redirect, render
from patients.models import Patient
from .models import PaymentMaster, PaymentTransaction
from decimal import Decimal
from django.db.models import Q
from typing import Tuple
try:
    from num2words import num2words
except ImportError:
    num2words = None


# -------------------------------------------------------------------
# Reporting & API Views
# -------------------------------------------------------------------

def _parse_range(request):
    today = date.today()
    start = parse_date(request.GET.get("start") or "") or (today - timedelta(days=29))
    end = parse_date(request.GET.get("end") or "") or today
    if start > end: start, end = end, start
    return start, end

def _parse_range_qp(request):
    today = date.today()
    dfrom = parse_date(request.GET.get("from") or "") or (today - timedelta(days=6))
    dto = parse_date(request.GET.get("to") or "") or today
    if dfrom > dto: dfrom, dto = dto, dfrom
    return dfrom, dto

def _get_patient_mobile(p):
    return (
        getattr(p, "mobile_num", None)
        or getattr(p, "mobile", None)
        or getattr(getattr(p, "contact", None), "mobile_num", None)
    )


def _normalize_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        s = value.strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M", "%Y-%m-%d",
            "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"
        ):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
    return None

def _receipt_context(request, pk: int):
    bill = get_object_or_404(
        PaymentMaster.objects
        .select_related("patient", "patient__contact", "hospital")
        .prefetch_related("transactions__service", "transactions__doctor"),
        pk=pk,
        hospital=request.user.hospital,
    )
    paid_dt = _normalize_dt(getattr(bill, "paid_on", None) or getattr(bill, "created_at", None)) or datetime.now()
    txns = list(bill.transactions.all().order_by("id"))
    primary_doctor = next((t.doctor for t in txns if getattr(t, "doctor_id", None)), None)
    if txns:
        first_tx = txns[0]
        pay_type = first_tx.get_pay_type_display() if hasattr(first_tx, "get_pay_type_display") else getattr(first_tx, "pay_type", "")
    else:
        pay_type = ""
    payment_ctx = {"paid_on": paid_dt, "pay_type": pay_type}

    total_amount = bill.total_amount
    if total_amount is None:
        total_amount = sum((t.amount or Decimal("0.00")) for t in txns)

    if num2words:
        try:
            rupees = Decimal(total_amount).quantize(Decimal("0.01"))
            rupee_int = int(rupees)
            paise_int = int((rupees - rupee_int) * 100)
            if paise_int:
                amount_in_words = f"{num2words(rupee_int, lang='en_IN').title()} Rupees And {num2words(paise_int, lang='en_IN').title()} Paise Only"
            else:
                amount_in_words = f"{num2words(rupee_int, lang='en_IN').title()} Rupees Only"
        except Exception:
            amount_in_words = ""
    else:
        amount_in_words = ""

    raw_pagesize = (request.GET.get("pagesize") or "A5").upper()
    pagesize = raw_pagesize if raw_pagesize in {"A5", "A4", "LETTER"} else "A5"
    raw_orientation = (request.GET.get("orientation") or "portrait").lower()
    orientation = raw_orientation if raw_orientation in {"portrait", "landscape"} else "portrait"

    return {
        "hospital": bill.hospital,
        "patient": bill.patient,
        "doctor": primary_doctor,
        "payment": payment_ctx,
        "txns": txns,
        "total_amount": total_amount,
        "amount": total_amount,
        "amount_in_words": amount_in_words,
        "receipt_no": str(bill.pk),
        "bill_pk": bill.pk,
        "now": datetime.now(),
        "pagesize": pagesize,
        "orientation": orientation,
        "for_pdf": bool(request.GET.get("for_pdf") or request.GET.get("inline")),
    }


def _flatten_errors(form, formset):
    lines = []
    if form.errors:
        for k, errs in form.errors.items():
            for e in errs:
                lines.append(f"[FORM] {k}: {e}")
    for e in form.non_field_errors():
        lines.append(f"[FORM] non_field: {e}")
    for e in formset.non_form_errors():
        lines.append(f"[FORMSET] non_form: {e}")
    for i, f in enumerate(formset.forms):
        if f.errors:
            for k, errs in f.errors.items():
                for e in errs:
                    lines.append(f"[ROW {i}] {k}: {e}")
    return lines

def pdf_supported() -> bool:
    try:
        import weasyprint; return True
    except Exception:
        try:
            import xhtml2pdf; return True
        except Exception:
            return False

# billing/utils.py

MOBILE_LENGTH = 10          # adjust if needed
MIN_NAME_CHARS = 3
MIN_MOBILE_PREFIX = 3



def _mobile_prefix_range(digits: str) -> Tuple[int, int]:
    """
    Convert a prefix like '98765' into a numeric range [low, high]
    for efficient BigInteger index scans.
    """
    L = len(digits)
    if L == MOBILE_LENGTH:
        n = int(digits)
        return n, n
    # L < MOBILE_LENGTH
    factor = 10 ** (MOBILE_LENGTH - L)
    low = int(digits) * factor
    high = low + factor - 1
    return low, high

def get_patient_queryset(hospital, query):
    """
    Returns a filtered queryset of patients for a given hospital and search query.
    Matches both patient name and mobile number (exact or prefix).
    """
    query = (query or "").strip()
    qs = Patient.objects.filter(hospital=hospital).select_related("contact")

    if not query:
        return qs.none()

    tokens = [t for t in query.split() if t]
    digits = "".join(ch for ch in query if ch.isdigit())

    name_q = Q()
    for t in tokens:
        if len(t) >= MIN_NAME_CHARS:
            name_q &= Q(patient_name__icontains=t)

    mobile_q = Q()
    if len(digits) == MOBILE_LENGTH:
        # exact 10-digit match
        mobile_q = Q(contact__mobile_num=int(digits))
    elif len(digits) >= MIN_MOBILE_PREFIX:
        # prefix match via numeric range
        low, high = _mobile_prefix_range(digits)
        mobile_q = Q(contact__mobile_num__range=(low, high))

    return qs.filter(name_q | mobile_q)



def get_patient_queryset(hospital, query):
    """Reusable helper for search & lookup."""
    query = (query or "").strip()
    qs = Patient.objects.filter(hospital=hospital).select_related("contact")
    if not query:
        return qs.none()

    tokens = [t for t in query.split() if t]
    digits = "".join(ch for ch in query if ch.isdigit())

    name_q = Q()
    for t in tokens:
        if len(t) >= MIN_NAME_CHARS:
            name_q &= Q(patient_name__icontains=t)

    mobile_q = Q()
    if len(digits) == MOBILE_LENGTH:
        mobile_q = Q(contact__mobile_num=int(digits))
    elif len(digits) >= MIN_MOBILE_PREFIX:
        low, high = _mobile_prefix_range(digits)
        mobile_q = Q(contact__mobile_num__range=(low, high))

    if name_q and mobile_q:
        return qs.filter(name_q | mobile_q)
    elif name_q:
        return qs.filter(name_q)
    elif mobile_q:
        return qs.filter(mobile_q)
    return qs.none()
