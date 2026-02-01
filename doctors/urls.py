from django.urls import path
from . import views
from prescription.views.draft import discard_draft

app_name = "doctors"

urlpatterns = [
    path("", views.doctor_dashboard, name="dashboard"),
    path("<int:doctor_id>/", views.doctor_detail, name="detail"),
    path("list/", views.doctor_list, name="list"),
    path("<int:doctor_id>/fee/", views.get_doctor_fee, name="fee"),
    path("draft/<int:draft_id>/discard/",discard_draft,name="discard_draft",),
]
