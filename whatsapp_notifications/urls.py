from django.urls import path
from .views import whatsapp_webhook,hospital_messages

app_name = "whatsapp_notifications"

urlpatterns = [
    path("messages/", hospital_messages, name="hospital_messages"),
    path("webhooks/whatsapp/<int:hospital_id>/", whatsapp_webhook, name="whatsapp_webhook"),
]