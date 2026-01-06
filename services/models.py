from django.db import models
from core.models import Hospital


class Service(models.Model):
    service_name = models.CharField(max_length=255)
    service_fees = models.PositiveIntegerField()
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Use DateTimeField for consistency

    class Meta:
        indexes = [
            models.Index(fields=['hospital']),
        ]
        unique_together = ('service_name', 'hospital')  # ✅ Prevent duplicate services in same hospital
        ordering = ['service_name']
        verbose_name_plural = "Services"

    def __str__(self):
        return self.service_name
