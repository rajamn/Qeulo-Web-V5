from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal, ROUND_HALF_UP

from core.models import Hospital, HospitalUser
from patients.models import Patient
from appointments.models import AppointmentDetails  # if optional, keep null=True below

class PatientVital(models.Model):
    hospital    = models.ForeignKey(Hospital, on_delete=models.CASCADE, db_index=True)
    patient     = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="vitals", db_index=True)
    appointment = models.ForeignKey(AppointmentDetails, on_delete=models.SET_NULL, null=True, blank=True)

    height_cm   = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal("30.00"))])
    weight_kg   = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal("1.00"))])
    bmi         = models.DecimalField(max_digits=5, decimal_places=2, editable=False)

    temperature_c = models.DecimalField(max_digits=4, decimal_places=1,
                                        validators=[MinValueValidator(Decimal("30.0")), MaxValueValidator(Decimal("45.0"))],
                                        help_text="°C")
    bp_systolic   = models.PositiveSmallIntegerField(validators=[MinValueValidator(50), MaxValueValidator(260)], help_text="mmHg")
    bp_diastolic  = models.PositiveSmallIntegerField(validators=[MinValueValidator(30), MaxValueValidator(180)], help_text="mmHg")
    spo2_percent  = models.PositiveSmallIntegerField(validators=[MinValueValidator(50), MaxValueValidator(100)], help_text="%")
    pulse_bpm     = models.PositiveSmallIntegerField(null=True, blank=True,
                                                    validators=[MinValueValidator(20), MaxValueValidator(220)])

    notes       = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(HospitalUser, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["hospital", "patient", "recorded_at"])]

    def __str__(self):
        return f"Vitals for {self.patient} @ {self.recorded_at:%Y-%m-%d %H:%M}"

    def _compute_bmi(self) -> Decimal:
        h_m = (self.height_cm or Decimal("0")) / Decimal("100")
        if h_m <= 0:
            return Decimal("0.00")
        bmi = (self.weight_kg or Decimal("0")) / (h_m * h_m)
        return bmi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.bmi = self._compute_bmi()
        super().save(*args, **kwargs)

