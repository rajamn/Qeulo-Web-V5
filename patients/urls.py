from django.urls import path
from .views import( cash_receipt_pdf,token_pdf,
                   view_patient_view,combined_receipt_token_pdf,
                   edit_patient_view,patient_dashboard,
                   register_patient_view,token_preview,
                   patient_search)
from .ajax import get_eta_ajax

# patients/urls.py
from django.urls import path
app_name = 'patients'


urlpatterns = [
    path('', patient_dashboard, name='dashboard'),
    path('register/', register_patient_view, name='register'),
    path('<int:patient_id>/edit/', edit_patient_view, name='edit'),
    path('<int:patient_id>/view/', view_patient_view, name='view'),
    path('get-eta/', get_eta_ajax, name='get_eta'),
    path('receipt/<int:appointment_id>/', cash_receipt_pdf, name='cash_receipt_pdf'),
    path('token/<int:appointment_id>/', token_pdf, name='token_pdf'),
    path("receipt-token/<int:appointment_id>/pdf/",combined_receipt_token_pdf, name="combined_receipt_token_pdf"),
    path("search/", patient_search, name="patient_search"),
    path("queue/token/<int:appointment_id>/preview/", token_preview, name="token_preview"),
    
]


