from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    # Main viewer
    path('', views.DicomViewerView.as_view(), name='dicom_viewer'),
    
    # File upload
    path('upload-dicom/', views.upload_dicom_files, name='upload_dicom'),
    
    # API endpoints
    path('api/studies/', views.get_studies, name='get_studies'),
    path('api/studies/<int:study_id>/images/', views.get_study_images, name='get_study_images'),
    path('api/images/<int:image_id>/', views.get_image_data, name='get_image_data'),
    
    # Measurements and annotations
    path('api/measurements/', views.save_measurement, name='save_measurement'),
    path('api/annotations/', views.save_annotation, name='save_annotation'),
    path('api/images/<int:image_id>/measurements/', views.get_measurements, name='get_measurements'),
    path('api/images/<int:image_id>/annotations/', views.get_annotations, name='get_annotations'),
    path('api/images/<int:image_id>/measurements/', views.clear_measurements, name='clear_measurements'),
    
    # Worklist functionality
    path('api/worklist/', views.get_worklist, name='get_worklist'),
    
    # Hounsfield units
    path('api/images/<int:image_id>/hounsfield/', views.get_hounsfield_units, name='get_hounsfield_units'),
    
    # Notifications
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    
    # Reports
    path('api/reports/', views.save_report, name='save_report'),
    path('api/studies/<int:study_id>/report/', views.get_report, name='get_report'),
]