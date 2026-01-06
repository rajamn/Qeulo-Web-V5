from django.db import models
from core.models import Hospital
from doctors.models import Doctor  # ✅ Make sure this import is correct
from django.conf import settings
class Drug(models.Model):
    drug_name = models.CharField(max_length=255)
    composition = models.TextField(blank=True, null=True)
    dosage = models.CharField(max_length=100, blank=True, null=True)
    frequency = models.CharField(max_length=100, blank=True, null=True)
    duration = models.CharField(max_length=100, blank=True, null=True)
    uses = models.TextField(blank=True, null=True)
    side_effects = models.TextField(blank=True, null=True)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)

    # ✅ Optional hospital – allows shared drugs (common library)
    hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True)

    # ✅ Optional doctor tag – allows doctor-specific custom additions
    added_by_doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Normalize casing
        if self.drug_name:
            self.drug_name = self.drug_name.strip().title()

        if self.composition:
            # Proper-style: first letter uppercase, rest same
            self.composition = self.composition.strip().capitalize()

        # Prevent duplicates
        query = Drug.objects.filter(drug_name__iexact=self.drug_name.strip())

        if self.hospital:
            query = query.filter(hospital=self.hospital, added_by_doctor__isnull=True)
        elif self.added_by_doctor:
            query = query.filter(added_by_doctor=self.added_by_doctor)
        else:
            query = query.filter(hospital__isnull=True, added_by_doctor__isnull=True)

        if self.pk:
            query = query.exclude(pk=self.pk)

        if query.exists():
            raise ValueError("Duplicate drug detected in the same scope.")

        super().save(*args, **kwargs)


    def __str__(self):
        return self.drug_name
    
# models.py

class UserPreset(models.Model):
    FIELD_CHOICES = [
        ("dosage", "Dosage"),
        ("frequency", "Frequency"),
        ("duration", "Duration"),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=20, choices=FIELD_CHOICES)
    value = models.CharField(max_length=100)

    class Meta:
        unique_together = ('user', 'field_name', 'value')


class DoctorDrug(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='selected_drugs')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='selected_by_doctors')
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('doctor', 'drug')
        ordering = ['drug__drug_name']

    def __str__(self):
        return f"{self.drug.drug_name} selected by {self.doctor.doctor_name}"



class DrugTemplate(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='drug_templates')
    name = models.CharField(max_length=100)
    # drugs = models.ManyToManyField(Drug, related_name='templates')
    # created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (by {self.doctor.doctor_name})"

# NOTE:
# DrugTemplateItem is the ONLY source of truth for wizard templates.

class DrugTemplateItem(models.Model):
    template = models.ForeignKey(DrugTemplate, on_delete=models.CASCADE, related_name='items')
    drug = models.ForeignKey(Drug, null=True, blank=True, on_delete=models.SET_NULL)
    drug_name = models.CharField(max_length=255)
    composition = models.TextField(blank=True)
    dosage = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    food_order = models.CharField(max_length=50, blank=True)



class DoctorDrugUsage(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="drug_usage"
    )

    # We intentionally use drug_name (string) for now
    # to avoid refactoring Drug FK at this stage
    drug_name = models.CharField(max_length=255)

    usage_count = models.PositiveIntegerField(default=0)
    last_used_on = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("doctor", "drug_name")
        indexes = [
            models.Index(fields=["doctor", "-usage_count"]),
            models.Index(fields=["doctor", "-last_used_on"]),
        ]

    def __str__(self):
        return f"{self.doctor.doctor_name} → {self.drug_name} ({self.usage_count})"
