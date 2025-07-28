from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    # Main viewer pages
    path('', views.viewer_home, name='home'),
    path('viewer/', views.viewer_page, name='viewer'),
    path('worklist/', views.worklist, name='worklist'),
    path('launch-viewer/', views.launch_viewer, name='launch_viewer'),
    
    # Print functionality
    path('reports/print/<int:patient_id>/', views.print_report, name='print_report'),
    
    # API endpoints - Studies and Images
    path('api/studies/', views.api_studies, name='api_studies'),
    path('api/studies/<int:study_id>/images/', views.api_study_images, name='api_study_images'),
    path('api/images/<int:image_id>/data/', views.api_image_data, name='api_image_data'),
    
    # API endpoints - Worklist
    path('api/worklist/patients/', views.api_worklist_patients, name='api_worklist_patients'),
    
    # API endpoints - Measurements and Annotations
    path('api/measurements/save/', views.api_save_measurement, name='api_save_measurement'),
    path('api/annotations/save/', views.api_save_annotation, name='api_save_annotation'),
    
    # API endpoints - Clinical Information and Reports
    path('api/patients/<int:patient_id>/clinical-info/', views.api_save_clinical_info, name='api_save_clinical_info'),
    path('api/patients/<int:patient_id>/report/', views.api_save_report, name='api_save_report'),
    
    # API endpoints - Notifications and AI
    path('api/check-new-uploads/', views.api_check_new_uploads, name='api_check_new_uploads'),
    path('api/ai-analysis/', views.api_ai_analysis, name='api_ai_analysis'),
    
    # API endpoints - File Upload
    path('api/upload/', views.upload_dicom, name='upload_dicom'),
]