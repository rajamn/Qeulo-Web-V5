import requests, json
from django.utils import timezone
from .models import WhatsappMessageLog, WhatsappConfig
from django.conf import settings


#whatsapp_notifications/services.py
# Set the authorization key in env 
# Update settings file

import requests
from django.conf import settings
from whatsapp_notifications.models import WhatsappMessageLog, WhatsappConfig, WhatsappTemplate


import requests
from django.utils import timezone
from .models import WhatsappTemplate, WhatsappMessageLog

import requests
from django.utils import timezone
from .models import WhatsappTemplate, WhatsappMessageLog

import requests
from django.utils import timezone
from .models import WhatsappTemplate, WhatsappMessageLog


import requests
import json
from django.utils import timezone
from .models import WhatsappTemplate, WhatsappMessageLog


import requests
import json
from django.utils import timezone
from .models import WhatsappTemplate, WhatsappMessageLog


def send_whatsapp_template(
    hospital,
    recipient_number,
    template_type=None,
    template_name=None,
    placeholders=None,
    patient=None,
    doctor=None,
    appointment_slot=None,
    token_num=None,
    que_pos=None,
    eta=None,
    buttons=True,   # default True = include call button
):
    """
    Sends a WhatsApp template message via DoubleTick (flat JSON payload).
    Supports one PHONE_NUMBER button (Call Us).
    """

    # --- Resolve template ---
    if template_name:
        tpl = WhatsappTemplate.objects.get(hospital=hospital, template_name=template_name)
    elif template_type:
        tpl = WhatsappTemplate.objects.get(hospital=hospital, template_type=template_type)
    else:
        raise ValueError("Either template_type or template_name must be provided")

    tpl_name = tpl.template_name
    webhook_url = tpl.webhook_url
    if not webhook_url:
        raise ValueError(f"No webhook URL configured for template {tpl_name} (hospital {hospital})")

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "key_U370Xs8rSS",
    }

    # --- Build placeholders if not passed ---
    if placeholders is None:
        doctor_name = doctor.doctor_name if doctor else ""
        appointment_date = timezone.localdate().strftime("%d/%m/%Y")
        placeholders = [
            patient.patient_name if patient else "",
            appointment_slot or "",
            str(token_num or ""),
            str(que_pos or ""),
            doctor_name,
            appointment_date,
        ]
        if eta:
            placeholders.append(str(eta))

    # --- Base payload ---
    payload = {
        "recipient": f"+91{recipient_number}",
        "templateName": tpl_name,
        "language": "en_US",
        "templateData": {
            "body": {"placeholders": placeholders}
        }
    }

    # --- Add Call Us button if enabled ---
    if buttons and getattr(hospital, "phone_num", None):
        payload["templateData"]["buttons"] = [
            {
                "type": "string",
                "parameter": f"+91{hospital.phone_num}"
            }
        ]

    # --- Debug print ---
    print("📤 WhatsApp Payload:")
    print(json.dumps(payload, indent=2))

    # --- Send ---
    try:
        resp = requests.post(webhook_url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

        WhatsappMessageLog.objects.create(
            hospital=hospital,
            patient=patient,
            doctor=doctor,
            template_name=tpl_name,
            recipient_number=recipient_number,
            placeholders=placeholders,
            provider_message_id=data.get("messages", [{}])[0].get("messageId"),
            status="sent",
        )
        return data

    except Exception as e:
        WhatsappMessageLog.objects.create(
            hospital=hospital,
            patient=patient,
            doctor=doctor,
            template_name=tpl_name,
            recipient_number=recipient_number,
            placeholders=placeholders,
            status="failed",
            error_message=str(e),
        )
        raise
