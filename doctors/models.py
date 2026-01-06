from django.db import models
from core.models import Hospital
from django.core.validators import RegexValidator
from datetime import time

mobile_validator = RegexValidator(regex=r'^\d{10}$', message="Enter a valid 10-digit mobile number")


class ActiveDoctorQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class ActiveDoctorManager(models.Manager):
    def get_queryset(self):
        return ActiveDoctorQuerySet(self.model, using=self._db).filter(is_active=True)


class Doctor(models.Model):
    doctor_name = models.CharField(max_length=255)
    doc_mobile_num = models.CharField(max_length=10, validators=[mobile_validator])
    average_time_minutes = models.PositiveIntegerField()
    fees = models.PositiveIntegerField()
    start_time = models.TimeField(default=time(18, 0))  # ✅ Proper ETA calculations
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Consistency
    is_active = models.BooleanField(default=True)  # ✅ Soft delete flag
    consult_validity_days = models.PositiveIntegerField(default=6)
    consult_validity_visits = models.PositiveIntegerField(default=2)
    consult_message_template = models.CharField(
        max_length=255,
        default="Valid for {days} days or {visits} visits whichever is earlier"
    )

    # Managers
    objects = ActiveDoctorManager()      # Default → only active doctors
    all_objects = models.Manager()       # Escape hatch → includes inactive

    class Meta:
        indexes = [
            models.Index(fields=['hospital']),
            models.Index(fields=['doc_mobile_num']),
        ]
        unique_together = ('doc_mobile_num', 'hospital')
        ordering = ['doctor_name']
        verbose_name_plural = "Doctors"

    def __str__(self):
        return self.doctor_name
