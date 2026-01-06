# billing/urls.py
from django.urls import path
from . import views
from django.views.generic import RedirectView


# billing/urls.py
app_name = "billing"

urlpatterns = [
    # Core workflow
    path("", views.finance_dashboard, name="dashboard"),
    path("new/", views.new_bill, name="new"),
    path("list/", views.bill_list, name="list"),
    path("edit/<int:pk>/", views.edit_bill, name="edit"),

    # Receipts (view & print)
    path("receipt/<int:pk>/", views.bill_receipt, name="receipt"),
    path("receipt/<int:pk>/pdf/", views.bill_receipt_pdf, name="receipt_pdf"),

    # APIs (used by forms & dashboards)
    path("search/", views.patient_search, name="patient_search"),
    path("lookup/", views.patient_lookup, name="patient_lookup"),

    path("api/services/", views.services_api, name="services_api"),
    path("api/summary/", views.api_finance_summary, name="api_finance_summary"),
    path("api/revenue_timeseries/", views.api_revenue_timeseries, name="api_revenue_timeseries"),
    path("api/top_services/", views.api_top_services, name="api_top_services"),
    path("api/pay_type_split/", views.api_pay_type_split, name="api_pay_type_split"),
    path("api/doctor_collections/", views.api_doctor_collections, name="api_doctor_collections"),

    # Reports / Collections
    path("collections/", views.todays_collection, name="todays_collection_today"),
    path("collections/<slug:date_str>/", views.todays_collection, name="todays_collection"),
    path("collections/doctors/", views.collections_doctors, name="collections_doctors"),
    path("collections/doctors/data/", views.collections_doctors_data, name="collections_doctors_data"),
    
    # Export
    path("export/revenue.csv", views.export_revenue_csv, name="export_revenue_csv"),
]

