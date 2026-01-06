from django.db import models

from django.db import models

from django.db import models

class WhatsappConfig(models.Model):
    hospital = models.OneToOneField("core.Hospital", on_delete=models.CASCADE)
    active = models.BooleanField(default=True)

    send_on_registration = models.BooleanField(default=True)
    send_reminders = models.BooleanField(default=True)
    send_followups = models.BooleanField(default=True)
    send_reschedules = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"WhatsApp Config for {self.hospital}"


class WhatsappTemplate(models.Model):
    TEMPLATE_TYPES = [
        ("confirmation", "Confirmation"),
        ("reschedule", "Reschedule"),
        ("followup", "Follow-up"),
    ]

    hospital = models.ForeignKey("core.Hospital", on_delete=models.CASCADE)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    template_name = models.CharField(max_length=150)
    webhook_url = models.URLField(max_length=500, blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("hospital", "template_type")

    def __str__(self):
        return f"{self.hospital} – {self.template_type}"


class WhatsappMessageLog(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("read", "Read"),
        ("failed", "Failed"),
    ]

    hospital = models.ForeignKey("core.Hospital", on_delete=models.CASCADE)
    patient = models.ForeignKey("patients.Patient", on_delete=models.SET_NULL, null=True, blank=True)
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.SET_NULL, null=True, blank=True)

    template_name = models.CharField(max_length=100)
    recipient_number = models.CharField(max_length=20)

    placeholders = models.JSONField()          # body placeholders
    buttons = models.JSONField(blank=True, null=True)  # CTA buttons if any

    provider_message_id = models.CharField(
        max_length=255,
        unique=True,               # 🔑 outbound/inbound message IDs from DoubleTick
        blank=True,
        null=True,
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.template_name} → {self.recipient_number} ({self.status})"


class WhatsappInboundMessage(models.Model):
    hospital = models.ForeignKey("core.Hospital", on_delete=models.CASCADE)
    patient = models.ForeignKey("patients.Patient", null=True, blank=True, on_delete=models.SET_NULL)

    provider_message_id = models.CharField(
        max_length=255,
        unique=True,  # inbound message’s DoubleTick/WA ID
    )
    from_number = models.CharField(max_length=20)
    message_text = models.TextField()

    event_type = models.CharField(
        max_length=20,
        choices=[
            ("ACCEPTED", "Accepted"),
            ("CANCELLED", "Cancelled"),
            ("QUERY", "Query"),
            ("UNKNOWN", "Unknown"),
        ],
        default="UNKNOWN",
    )

    in_reply_to = models.ForeignKey(
        "WhatsappMessageLog",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
        help_text="Links inbound to original outbound via context.message_id",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_number} → {self.event_type} ({self.created_at:%d-%m %H:%M})"
