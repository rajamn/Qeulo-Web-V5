from django.db import models
from core.models import Hospital
from patients.models import Patient
from doctors.models import Doctor
from services.models import Service
from django.core.validators import RegexValidator
from datetime import date
from decimal import Decimal

# billng/models.py

class PaymentMaster(models.Model):
    paid_on = models.DateField(default=date.today)  # ✅ Ensure default is set
    mobile_num = models.CharField(max_length=10, validators=[RegexValidator(regex=r'^\d{10}$')])
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    collected_by = models.CharField(max_length=255)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Consistent datetime

    class Meta:
        indexes = [
            models.Index(fields=['paid_on']),
            models.Index(fields=['patient']),
            models.Index(fields=['hospital']),
        ]
        ordering = ['-paid_on']

    def __str__(self):
        return f"Payment #{self.id} for {self.patient} on {self.paid_on}"
    
    def recompute_total(self, save=True):
        total = sum((t.amount or Decimal("0.00")) for t in self.transactions.all())
        self.total_amount = total
        if save:
            self.save(update_fields=["total_amount"])
        return total



class PaymentTransaction(models.Model):
    PAYMENT_CHOICES = [
        ('Due', 'Due'),
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('UPI', 'UPI'),
        ('Review', 'Review'),
        ('Other', 'Other'),
    ]

    payment = models.ForeignKey(PaymentMaster, on_delete=models.CASCADE, related_name='transactions')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    pay_type = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    paid_on = models.DateField(default=date.today)
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Use DateTime for precision

    class Meta:
        unique_together = ('patient', 'doctor', 'service', 'hospital', 'paid_on')
        indexes = [
            models.Index(fields=['payment']),
            models.Index(fields=['doctor']),
            models.Index(fields=['service']),
            models.Index(fields=['paid_on']),
        ]
        ordering = ['-paid_on']

    def __str__(self):
        return f"{self.pay_type} - ₹{self.amount} to {self.doctor}"


# billing/models.py (add this inside PaymentMaster)


