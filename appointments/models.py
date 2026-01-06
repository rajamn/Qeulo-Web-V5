from django.db import models
from core.models import Hospital
from patients.models import Patient
from doctors.models import Doctor
from datetime import date
from django.core.validators import RegexValidator


class AppointmentDetails(models.Model):
    # 🔁 Status Constants
    STATUS_NO_SHOW = 2
    STATUS_REGISTERED = -1
    STATUS_IN_QUEUE = 0
    STATUS_DONE = 1

    STATUS_CHOICES = [
        (STATUS_NO_SHOW, 'No Show'),
        (STATUS_REGISTERED, 'Registered'),
        (STATUS_IN_QUEUE, 'In Queue'),
        (STATUS_DONE, 'Done'),
    ]

    @property
    def appointment_id(self):
        return self.appoint_id

    appoint_id = models.AutoField(primary_key=True)
    appointment_on = models.DateField(default=date.today)
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT)
    mobile_num = models.CharField(max_length=10,validators=[RegexValidator(regex=r'^\d{10}$')],
        help_text="10-digit mobile number")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    payment = models.ForeignKey('billing.PaymentMaster', on_delete=models.PROTECT)
    token_num = models.CharField(max_length=20)
    called = models.BooleanField(default=False)
    que_pos = models.IntegerField()
    eta = models.TimeField(null=True, blank=True)
    completed = models.SmallIntegerField(choices=STATUS_CHOICES,default=STATUS_REGISTERED,
        help_text="Appointment status")
    # appointments/models.py
    queue_start_time = models.DateTimeField(null=True, blank=True)  # When patient starts waiting
    completed_at = models.DateTimeField(null=True, blank=True)       # When doctor completes

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Use DateTimeField for audit

    class Meta:
        db_table = 'appointment_details'
        unique_together = ('appointment_on', 'patient', 'doctor', 'hospital')
        indexes = [
            models.Index(fields=['appointment_on']),
            models.Index(fields=['doctor']),
            models.Index(fields=['payment']),
        ]
        ordering = ['-appointment_on', 'doctor']
    
    

    def __str__(self):
        return (
            f"Appt #{self.appoint_id} - "
            f"{self.patient.patient_name} | "
            f"Dr. {self.doctor.doctor_name} | "
            f"{self.appointment_on} | "
            f"Token {self.token_num} | "
            f"Status {self.get_completed_display()}"
        )






class AppointmentAuditLog(models.Model):
    hospital = models.ForeignKey("core.Hospital", on_delete=models.CASCADE)
    appointment = models.ForeignKey("appointments.AppointmentDetails", on_delete=models.CASCADE)
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE)
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE)

    action = models.CharField(max_length=50)  # e.g., "queued", "completed", "cancelled"
    token_num = models.CharField(max_length=10)
    que_pos = models.IntegerField()

    eta = models.TimeField(blank=True, null=True)
    completion_time = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.appointment_id} {self.action} @ {self.created_at}"
