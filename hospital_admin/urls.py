from django.urls import path
from . import views

app_name = "hospital_admin"

urlpatterns = [
    # ✅ Manage Doctors (already done)
    path("doctors/", views.doctor_list, name="doctor_list"),
    path("doctors/<int:doctor_id>/edit/", views.doctor_edit, name="doctor_edit"),

    # ✅ Manage Services (new)
    path("services/", views.service_list, name="service_list"),
    path("services/add/", views.service_edit, name="service_add"),
    path("services/<int:service_id>/edit/", views.service_edit, name="service_edit"),

    # ✅ Hospital Settings (new)
    path("settings/", views.hospital_settings, name="hospital_settings"),
    
]
