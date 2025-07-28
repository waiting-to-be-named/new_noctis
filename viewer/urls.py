from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    # Main viewer page
    path('', views.DicomViewerView.as_view(), name='viewer'),
    
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
    
    # AI Analysis endpoints
    path('api/images/<int:image_id>/analyze/', views.analyze_image, name='analyze_image'),
    path('api/images/<int:image_id>/predict/', views.predict_image, name='predict_image'),
    
    # Anonymization endpoints
    path('api/studies/<int:study_id>/anonymize/', views.anonymize_study, name='anonymize_study'),
    path('api/anonymize/batch/', views.anonymize_batch, name='anonymize_batch'),
    
    # Export endpoints
    path('api/export/images/', views.export_images, name='export_images'),
]