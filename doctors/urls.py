from django.urls import path
from . import views

app_name = "doctors"

urlpatterns = [
    path("", views.doctor_dashboard, name="dashboard"),
    path("<int:doctor_id>/", views.doctor_detail, name="detail"),
    path("list/", views.doctor_list, name="list"),
    path("<int:doctor_id>/fee/", views.get_doctor_fee, name="fee"),
]
