from django.urls import path
from .views import create_vitals, api_latest_vitals

app_name = "vitals"

urlpatterns = [
    path("patients/<int:patient_id>/vitals/new/", create_vitals, name="create_for_patient"),
    path("patients/<int:patient_id>/appointments/<int:appointment_id>/vitals/new/", create_vitals, name="create_for_appointment"),
    path("api/latest/", api_latest_vitals, name="api_latest"),
]

