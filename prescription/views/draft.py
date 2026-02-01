from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from prescription.models import PrescriptionDraft

def discard_draft(request, draft_id):
    draft = get_object_or_404(PrescriptionDraft, id=draft_id)

    # Safety: ensure doctor owns this draft
    if draft.doctor_id != request.user.doctor_id:
        messages.error(request, "Unauthorized action.")
        return redirect("doctors:dashboard")

    draft.delete()
    messages.success(request, "Prescription draft discarded.")

    return redirect("doctors:dashboard")
