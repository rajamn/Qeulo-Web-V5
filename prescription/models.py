from django.db import models

# Create your models here.
# prescription/models.py
from django.db import models
from core.models import Hospital
from patients.models import Patient
from appointments.models import AppointmentDetails
from doctors.models import Doctor
from billing.models import PaymentMaster
from drugs.models import Drug  # This was in prescription.models



# prescription/models.py

class PrescriptionMaster(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)

    appointment = models.ForeignKey(AppointmentDetails,on_delete=models.SET_NULL,null=True,
        blank=True,help_text="Prescription is not strictly tied to an appointment",)

    # Notes
    notes_history = models.TextField(blank=True)
    notes_symptoms = models.TextField(blank=True)
    notes_findings = models.TextField(blank=True)
    general_advice = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)

    prescribed_on = models.DateTimeField(auto_now_add=True)

    # NEW FIELD — links to previous Rx
    previous_rx = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="followups",
        help_text="If this prescription continues a previous one",
    )

    # Optional — may help analytics later
    is_revisit = models.BooleanField(default=False)

    class Meta:
        db_table = "prescription_master"
        ordering = ["-prescribed_on"]
    # def __str__(self):
    #     return f"Rx #{self.prescription_id} - {self.patient.patient_name} by {self.doctor.doctor_name}"
    def __str__(self):
        return f"Rx #{self.id} - {self.patient.patient_name} by {self.doctor.doctor_name}"




class PrescriptionDetails(models.Model):
    prescription = models.ForeignKey(
        'PrescriptionMaster',
        on_delete=models.CASCADE,
        related_name='details'
    )
    drug_name = models.CharField(max_length=255)
    composition = models.TextField(blank=True)
    dosage = models.CharField(max_length=100, blank=True)  # ✅ New field
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    # ── New food_order field ─────────────────────────────────────────
    FOOD_CHOICES = [
        ('before', 'Before Meal'),
        ('after',  'After Meal'),
    ]
    food_order = models.CharField(
    max_length=6,
    choices=FOOD_CHOICES,
    default='after',
    blank=True,
    help_text="Take before or after meals"
    )

    class Meta:
        db_table = 'prescription_details'
        unique_together = ('prescription', 'drug_name')
        ordering = ['drug_name']

    def __str__(self):
        return f"{self.drug_name} ({self.dosage}) - {self.frequency} × {self.duration}"



# prescription/models.py

class PrescriptionDraft(models.Model):
    """
    Stores an in-progress AI-assisted (or manual) prescription
    for a given appointment + doctor.
    Not visible to patients; used only during the drafting flow.
    """

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    appointment = models.ForeignKey(AppointmentDetails, null=True, blank=True, on_delete=models.SET_NULL)


    # Current wizard step: 'history', 'symptoms', 'findings', 'diagnosis', 'prescription', 'review'
    current_step = models.CharField(max_length=50, default="history")

    # Doctor-entered + UI state content
    data = models.JSONField(default=dict, blank=True)

    # AI-generated suggestions, safety checks, etc. (for audit + transparency)
    ai_suggestions = models.JSONField(default=dict, blank=True)

    # Marked True after we convert this draft into PrescriptionMaster + PrescriptionDetails
    finalized = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "prescription_draft"
        unique_together = ("doctor", "appointment")   # one active draft per doctor+appointment
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Draft for Appt {self.appointment_id} by Dr. {self.doctor.doctor_name}"

# prescription/models.py

class DoctorHistoryTemplate(models.Model):
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE)
    label = models.CharField(max_length=255)     # Name shown in dropdown
    content = models.TextField()                 # Text inserted into history
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return f"{self.doctor} - {self.label}"


# prescription/models.py

class PrescriptionLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]

    log_id = models.AutoField(primary_key=True)
    prescription = models.ForeignKey('PrescriptionMaster', on_delete=models.CASCADE)
    hospital = models.ForeignKey('core.Hospital', on_delete=models.CASCADE)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE)
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.SET_NULL, null=True, blank=True)

    drug_name = models.CharField(max_length=255)
    composition = models.TextField(blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    changed_by = models.CharField(max_length=100)
    changed_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    FOOD_CHOICES = [
        ('before', 'Before Meal'), ('after',  'After Meal'),
        ]
    food_order = models.CharField(
        max_length=6,
        choices=FOOD_CHOICES,
        blank=True,
        null=True,                 # ← allow NULL in the DB
        default='after',
        help_text="Take before or after meals"
    )    
    


    class Meta:
        db_table = 'prescription_log'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.action.upper()} by {self.changed_by} on {self.changed_at}"


