from django.urls import path, re_path,include
from django.shortcuts import redirect
from core.models import Hospital
from core.views import CustomLoginView
from queue_mgt.views import queue_display
from patients.views import register_patient_view   # ✅ import your hybrid register view
from . import views


def hospital_root_redirect(request, slug):
    """
    Redirect bare /h/<slug>/ to /h/<slug>/login/.
    If hospital not found, fall back to /login/.
    """
    try:
        Hospital.objects.get(slug=slug)
        return redirect("hospital_login", slug=slug)
    except Hospital.DoesNotExist:
        return redirect("login")


urlpatterns = [
    # 🧭 Handle both /h/<slug> and /h/<slug>/ with or without trailing slash
    re_path(r'^(?P<slug>[-\w]+)/?$', hospital_root_redirect, name="hospital_root_redirect"),

    # 🔐 Hospital-branded login page
    path("<slug:slug>/login/", CustomLoginView.as_view(), name="hospital_login"),

    # 🧾 Patient self-registration (kiosk / QR)
    path("<slug:slug>/display/", queue_display, name="hospital_display"),

    # 🖥️ Queue display (public)
    path("<slug:slug>/self_register/", views.self_register_view, name="hospital_self_register"),
    path("<slug:slug>/api/doctor_info/<int:doctor_id>/", views.doctor_info_api, name="doctor_info_api"),
]
