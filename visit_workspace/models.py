from django.db import models

# Create your models here.
# visit_workspace/models.py

from django.conf import settings
from django.db import models

from core.models import Hospital
from patients.models import Patient
from appointments.models import AppointmentDetails
from doctors.models import Doctor
from drugs.models import Drug  # or DrugMaster – adjust to your actual model name


class VisitDocument(models.Model):
    """
    Stores uploaded reports / old prescriptions / discharge summaries etc.
    Linked to patient + (optionally) an appointment.
    """

    DOCUMENT_TYPES = [
        ("LAB", "Lab Report"),
        ("RAD", "Radiology Report"),
        ("RX_OLD", "Old Prescription"),
        ("DISCH", "Discharge Summary"),
        ("OTHER", "Other"),
    ]

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    summary_data = models.JSONField(null=True, blank=True)
    ai_summary_data = models.JSONField(null=True, blank=True)
    appointment = models.ForeignKey(
        AppointmentDetails,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visit_documents",
    )

    doc_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to="visit_documents/%Y/%m/%d/", blank=True, null=True)
    description = models.CharField(max_length=255, blank=True)
    ocr_text = models.TextField(blank=True)  
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_visit_documents",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["hospital", "patient"]),
            models.Index(fields=["appointment"]),
        ]

    def __str__(self):
        return f"{self.patient} | {self.get_doc_type_display()} | {self.created_at.date()}"


class VisitNote(models.Model):
    """
    Stores clinical notes, summaries, AI summaries, etc. for a visit.
    """

    NOTE_TYPES = [
        ("CLINICAL", "Clinical Notes"),
        ("SUMMARY", "Summary"),
        ("AI_SUMMARY", "AI-Generated Summary"),
    ]

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    appointment = models.ForeignKey(
        AppointmentDetails,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visit_notes",
    )

    note_type = models.CharField(max_length=20, choices=NOTE_TYPES)
    text = models.TextField()
    source = models.CharField(max_length=50, blank=True, null=True)
    # e.g., "OCR", "Manual", "AI"


    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_visit_notes",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["hospital", "patient"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient} | {self.get_note_type_display()} | {self.created_at}"


class PrescriptionTemplate(models.Model):
    """
    Doctor-specific saved prescription templates.
    In Phase 1 we store items as JSON for simplicity.
    """

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)  # e.g. "Viral Fever Standard"
    notes = models.TextField(blank=True)  # optional header notes

    # Phase 1: simple JSON structure, e.g.:
    # [{ "drug_id": 1, "strength": "650 mg", "freq": "TID", "duration": "5 days", "instructions": "After food" }]
    items_json = models.JSONField()

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("hospital", "doctor", "name")
        ordering = ["doctor", "name"]

    def __str__(self):
        return f"{self.doctor} | {self.name}"


class FavoriteDrug(models.Model):
    """
    Per-doctor favorite drugs for quick selection in the prescription UI.
    """

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("hospital", "doctor", "drug")
        indexes = [
            models.Index(fields=["hospital", "doctor"]),
        ]

    def __str__(self):
        return f"{self.doctor} - {self.drug}"
