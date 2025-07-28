from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    # Main viewer page
    path('', views.DicomViewerView.as_view(), name='viewer'),
    path('viewer/', views.DicomViewerView.as_view(), name='viewer_main'),
    
    # Worklist and facility management
    path('worklist/', views.WorklistView.as_view(), name='worklist'),
    path('facility/', views.FacilityDashboardView.as_view(), name='facility_dashboard'),
    path('launch-viewer/<int:study_id>/', views.launch_viewer, name='launch_viewer'),
    
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
    path('api/measurements/hu/', views.measure_hu, name='measure_hu'),
    
    # Clinical information and reports
    path('api/studies/<int:study_id>/clinical-info/', views.save_clinical_info, name='save_clinical_info'),
    path('api/studies/<int:study_id>/report/', views.save_report, name='save_report'),
    
    # Notifications
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # AI and 3D features
    path('api/ai/analysis/', views.ai_analysis, name='ai_analysis'),
    path('api/3d/reconstruction/', views.reconstruction_3d, name='reconstruction_3d'),
]