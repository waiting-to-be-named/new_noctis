from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    # Main viewer pages
    path('', views.DicomViewerView.as_view(), name='viewer'),
    path('worklist/', views.WorklistView.as_view(), name='worklist'),
    path('facility/', views.FacilityView.as_view(), name='facility'),
    
    # File upload
    path('api/upload/', views.upload_dicom_files, name='upload_dicom'),
    
    # Study and image data
    path('api/studies/', views.get_studies, name='get_studies'),
    path('api/studies/<int:study_id>/images/', views.get_study_images, name='get_study_images'),
    path('api/images/<int:image_id>/data/', views.get_image_data, name='get_image_data'),
    
    # Measurements and annotations
    path('api/measurements/save/', views.save_measurement, name='save_measurement'),
    path('api/annotations/save/', views.save_annotation, name='save_annotation'),
    path('api/images/<int:image_id>/measurements/', views.get_measurements, name='get_measurements'),
    path('api/images/<int:image_id>/annotations/', views.get_annotations, name='get_annotations'),
    path('api/images/<int:image_id>/clear-measurements/', views.clear_measurements, name='clear_measurements'),
    
    # AI Analysis
    path('api/images/<int:image_id>/ai-analysis/', views.ai_analysis, name='ai_analysis'),
    
    # 3D Reconstruction
    path('api/studies/<int:study_id>/reconstruction/', views.create_3d_reconstruction, name='create_3d_reconstruction'),
    
    # Notifications
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # Reports
    path('api/reports/', views.reports, name='reports'),
    path('api/studies/<int:study_id>/reports/', views.reports, name='study_reports'),
    
    # Clinical Notes
    path('api/studies/<int:study_id>/clinical-notes/', views.update_clinical_notes, name='update_clinical_notes'),
]