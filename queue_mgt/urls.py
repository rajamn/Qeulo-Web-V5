from django.urls import path
from .views import (queue_dashboard, 
                    update_status,queue_display,
                    call_patient,
                    reschedule_page)

urlpatterns = [
    path('', queue_dashboard, name='queue'),
    path('display/', queue_display, name='queue_display'),
    path('call-patient/<int:appoint_id>/', call_patient, name='call_patient'),
    path('update-status/<int:appoint_id>/<int:new_status>/', update_status, name='update_status'),
    path("reschedule/", reschedule_page, name="reschedule_page"),

]
