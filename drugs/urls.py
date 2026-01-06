from django.urls import path
from .views import drug_autocomplete, drug_library, drug_templates,lib_add_drug
from .views import drug_library_edit,add_drug_template, view_drug_template,delete_drug_template

urlpatterns = [
    path("api/autocomplete/", drug_autocomplete, name="drug_autocomplete"),
    path('library/', drug_library, name='drug_library'),
    path('add/', lib_add_drug, name='lib_add_drug'),
    path('library/edit/', drug_library_edit, name='drug_library_edit'),
    path('templates/', drug_templates, name='drug_templates'),
    # Add new template
    path('templates/add/', add_drug_template, name='add_drug_template'),
    path('templates/view/<int:template_id>/', view_drug_template, name='view_drug_template'),
    path('templates/delete/<int:template_id>/', delete_drug_template, name='delete_drug_template'),

]
    


