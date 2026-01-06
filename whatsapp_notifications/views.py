import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts       import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import WhatsappMessageLog, WhatsappInboundMessage
from .utils import classify_inbound_message  # move classifier into utils.py if you like
from core.models import Hospital  # if you want hospital fallback mapping



# @csrf_exempt
# def whatsapp_webhook(request):
#     """
#     Webhook to receive DoubleTick events:
#     - messageStatus → updates outbound logs
#     - messageReceived → saves inbound patient replies
#     """
#     if request.method != "POST":
#         return JsonResponse({"error": "Only POST allowed"}, status=405)

#     try:
#         payload = json.loads(request.body.decode("utf-8"))

#         # DoubleTick can send a single event or batch
#         events = payload if isinstance(payload, list) else [payload]

#         for evt in events:
#             event_type = evt.get("event")   # "messageStatus" | "messageReceived"
#             dt_id = evt.get("dtMessageId")
#             from_number = evt.get("from")
#             to_number = evt.get("to")

#             # --- 1️⃣ Status update for outbound
#             if event_type == "messageStatus" and dt_id:
#                 status = evt.get("status")
#                 WhatsappMessageLog.objects.filter(
#                     provider_message_id=dt_id
#                 ).update(status=status)

#             # --- 2️⃣ Inbound message (patient reply)
#             elif event_type == "messageReceived" and from_number:
#                 message_obj = evt.get("message", {})
#                 text_body = message_obj.get("text", "")

#                 classification = classify_inbound_message(text_body)

#                 # Find matching outbound log by provider_message_id
#                 log = WhatsappMessageLog.objects.filter(
#                     provider_message_id=dt_id
#                 ).first()

#                 hospital = log.hospital if log else None
#                 patient = log.patient if log else None

#                 WhatsappInboundMessage.objects.create(
#                     hospital=hospital,
#                     patient=patient,
#                     provider_message_id=dt_id,
#                     from_number=from_number,
#                     message_text=text_body,
#                     event_type=classification,
#                     in_reply_to=log,
#                 )

#         return JsonResponse({"ok": True})

#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=400)



logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def whatsapp_webhook(request):
    """
    Handles DoubleTick webhooks:
    - Inbound message: payload contains dtMessageId + message + from
    - Status update: payload contains status + messageId (+ to)
    DoubleTick may send a single object or a list.
    """
    try:
        raw = request.body.decode("utf-8") or "{}"
        payload = json.loads(raw)
    except Exception:
        logger.exception("DoubleTick webhook: invalid JSON")
        return JsonResponse({"error": "invalid_json"}, status=400)

    events = payload if isinstance(payload, list) else [payload]

    inbound_created = 0
    status_updated = 0
    unhandled = 0

    for evt in events:
        # ---------------------------
        # 1) Sent message status update
        # ---------------------------
        # DoubleTick "Sent Message Status" uses: status + messageId (+ to + statusTimestamp)
        # messageId == dtMessageId from receive payload (per docs)
        if "status" in evt and "messageId" in evt:
            msg_id = evt.get("messageId")
            status = evt.get("status")

            if msg_id and status:
                updated = WhatsappMessageLog.objects.filter(
                    provider_message_id=msg_id
                ).update(status=status)
                status_updated += int(updated)
            else:
                logger.warning("Status webhook missing messageId/status: %s", evt)
            continue

        # ---------------------------
        # 2) Inbound message received
        # ---------------------------
        # Receive payload contains dtMessageId + from + to + message{...}
        if "dtMessageId" in evt and "from" in evt and "message" in evt:
            dt_id = evt.get("dtMessageId")
            from_number = evt.get("from")
            to_number = evt.get("to")

            msg = evt.get("message") or {}
            msg_type = msg.get("type")  # TEXT / BUTTON / IMAGE / DOCUMENT etc.
            text_body = (
                msg.get("text") or
                msg.get("payload") or    # button replies
                msg.get("caption") or    # media captions
                ""
            )

            # Classify safely
            try:
                classification = classify_inbound_message(text_body) if text_body else (msg_type or "UNKNOWN")
            except Exception:
                logger.exception("Inbound classify failed (dtMessageId=%s)", dt_id)
                classification = msg_type or "UNKNOWN"

            # Link to previous outbound message if it is a reply:
            # payload may include dtPairedMessageId (reply to your previous msg)
            paired_dt_id = evt.get("dtPairedMessageId") or evt.get("pairedMessageId")

            log = None
            if paired_dt_id:
                log = WhatsappMessageLog.objects.filter(provider_message_id=paired_dt_id).first()

            # If no paired id, try matching latest outbound to this number (optional heuristic)
            if not log and from_number:
                log = (
                    WhatsappMessageLog.objects
                    .filter(to_number=from_number)  # change field name if yours differs
                    .order_by("-created_at")
                    .first()
                )

            hospital = getattr(log, "hospital", None)
            patient = getattr(log, "patient", None)

            # Optional fallback: infer hospital from "to" number (if your Hospital.phone_num stores your WA API number)
            if hospital is None and to_number:
                hospital = Hospital.objects.filter(phone_num=to_number).first()

            # IMPORTANT:
            # If your WhatsappInboundMessage.hospital/patient fields are NOT nullable,
            # you MUST ensure hospital is resolved OR make those fields null=True.
            WhatsappInboundMessage.objects.create(
                hospital=hospital,
                patient=patient,
                provider_message_id=dt_id,
                from_number=from_number,
                message_text=text_body,
                event_type=classification,
                in_reply_to=log,
            )

            inbound_created += 1
            continue

        # ---------------------------
        # 3) Anything else: log it
        # ---------------------------
        unhandled += 1
        logger.info("Unhandled DoubleTick webhook payload: keys=%s evt=%s", list(evt.keys()), evt)

    return JsonResponse({
        "ok": True,
        "inbound_created": inbound_created,
        "status_updated": status_updated,
        "unhandled": unhandled,
    })



@login_required
def hospital_messages(request):
    hospital = request.user.hospital
    outbound_logs = (
        WhatsappMessageLog.objects.filter(hospital=hospital)   # ✅ only this hospital
        .select_related("patient")
        .prefetch_related("replies")
        .order_by("-created_at")[:100]
    )
    return render(request, "whatsapp_notifications/hospital_messages.html", {
        "outbound_logs": outbound_logs
    })



@login_required
def hospital_inbound_messages(request):
    hospital = request.user.hospital
    logs = WhatsappInboundMessage.objects.filter(
        hospital=hospital
    ).order_by("-created_at")[:50]

    return render(request, "whatsapp_notifications/inbound_list.html", {"logs": logs})

