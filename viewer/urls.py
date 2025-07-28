from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    # Landing page
    path('', views.HomeView.as_view(), name='home'),
    
    # Main viewer page
    path('viewer/', views.DicomViewerView.as_view(), name='viewer'),
    
    # Worklist
    path('worklist/', views.WorklistView.as_view(), name='worklist'),
    path('worklist/<int:patient_id>/launch/', views.launch_viewer_from_worklist, name='launch_from_worklist'),
    
    # Facility views
    path('facility/<int:facility_id>/', views.FacilityView.as_view(), name='facility_view'),
    
    # File upload
    path('api/upload/', views.upload_dicom_files, name='upload_dicom'),
    
    # Study and image data
    path('api/studies/', views.get_studies, name='get_studies'),
    path('api/studies/<int:study_id>/images/', views.get_study_images, name='get_study_images'),
    path('api/studies/<int:study_id>/clinical-info/', views.create_clinical_info, name='create_clinical_info'),
    path('api/studies/<int:study_id>/report/', views.create_report, name='create_report'),
    path('api/studies/<int:study_id>/report/get/', views.get_report, name='get_report'),
    path('api/images/<int:image_id>/data/', views.get_image_data, name='get_image_data'),
    
    # Measurements and annotations
    path('api/measurements/save/', views.save_measurement, name='save_measurement'),
    path('api/annotations/save/', views.save_annotation, name='save_annotation'),
    path('api/annotations/<int:annotation_id>/update-position/', views.update_annotation_position, name='update_annotation_position'),
    path('api/images/<int:image_id>/measurements/', views.get_measurements, name='get_measurements'),
    path('api/images/<int:image_id>/annotations/', views.get_annotations, name='get_annotations'),
    path('api/images/<int:image_id>/clear-measurements/', views.clear_measurements, name='clear_measurements'),
    
    # Notifications
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
]