# visit_workspace/urls.py

from django.urls import path
from .views import (
    visit_workspace_view, upload_document,
    process_document, patient_history,
    ocr_text_upload, save_summary,summary_view
)

app_name = "visit_workspace"

# visit_workspace/urls.py

from django.urls import path
from .views import (
    visit_workspace_view, upload_document,
    ocr_text_upload, process_document,
    summary_view, save_summary,
    patient_history,)

app_name = "visit_workspace"

urlpatterns = [
    path("patient/<int:patient_id>/", visit_workspace_view, name="visit_workspace"),
    # Document workflow
    path("upload/<int:pk>/", upload_document, name="upload_document"),
    path("ocr_text/<int:pk>/", ocr_text_upload, name="ocr_text_upload"),
    path("process/<int:doc_id>/", process_document, name="process_document"),
    path("summary/<int:doc_id>/", summary_view, name="summary"),
    path("save/<int:doc_id>/", save_summary, name="save_summary"),

    # Other
    path("history/<int:pk>/", patient_history, name="patient_history"),
]
