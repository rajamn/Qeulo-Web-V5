from django.urls import path
from . import views

app_name = "reports"
urlpatterns = [
    path("", views.reports_home, name="home"),   # ← MUST be present
    path("daily-opd/", views.daily_opd_report, name="daily_opd"),
    path("revenue/", views.revenue_report, name="revenue"),
    path("revenue/export/", views.revenue_export_excel, name="revenue_export"),
    path("dues/", views.pending_dues_report, name="pending_dues"),
    path("dues/export/", views.pending_dues_export_excel, name="pending_dues_export"),
    path("doctor-productivity/", views.doctor_productivity_report, name="doctor_productivity"),
    path("doctor-productivity/export/", views.doctor_productivity_export_excel, name="doctor_productivity_export"),
    path("waiting-time/", views.waiting_time_report, name="waiting_time"),

]