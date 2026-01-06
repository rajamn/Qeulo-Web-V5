from datetime import date
from django.db import models
from core.models import Hospital

GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
]

class Contact(models.Model):
    mobile_num = models.BigIntegerField()
    contact_name = models.CharField(max_length=255)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('mobile_num', 'hospital')
        indexes = [models.Index(fields=['mobile_num'])]

    def __str__(self):
        return f"{self.contact_name} ({self.mobile_num})"


class Patient(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="patients")
    patient_name = models.CharField(max_length=255)
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    referred_by = models.CharField(max_length=100, blank=True, null=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('contact', 'patient_name', 'hospital')
        indexes = [
            models.Index(fields=['contact']),
            models.Index(fields=['hospital']),
        ]

    def age_years(self):
        if not self.dob:
            return None
        today = date.today()
        return today.year - self.dob.year - (
            (today.month, today.day) < (self.dob.month, self.dob.day)
        )

    def age_months(self):
        """Return age months (remainder after extracting full years)."""
        if not self.dob:
            return None

        today = date.today()

        # Total months difference first
        total_months = (today.year - self.dob.year) * 12 + (today.month - self.dob.month)
        if today.day < self.dob.day:
            total_months -= 1

        # Remainder months
        return total_months % 12

    
    @property
    def age_display(self):
        """Return age in years and months (e.g., '2y 3m')."""
        if not self.dob:
            return None

        years = self.age_years()
        total_months = self.age_months()

        # Convert surplus months into years
        extra_years = total_months // 12
        remainder_months = total_months % 12

        years += extra_years

        # Formatting
        if remainder_months == 0:
            return f"{years}y"
        return f"{years}y {remainder_months}m"

    
    @property
    def patient_code(self):
        prefix = self.hospital.hospital_name[:3].upper()
        return f"{prefix}-{self.id:05d}"


    def __str__(self):
        return self.patient_name
