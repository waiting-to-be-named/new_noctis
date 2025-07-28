# dicom_viewer/urls.py
from django.urls import path
from . import views

app_name = 'dicom_viewer'

urlpatterns = [
    # Launcher
    path('', views.LauncherView.as_view(), name='launcher'),
    
    # Main viewer
    path('viewer/', views.DicomViewerView.as_view(), name='viewer'),
    
    # Worklist
    path('worklist/', views.WorklistView.as_view(), name='worklist'),
    
    # Report writing
    path('report/', views.ReportView.as_view(), name='report'),
    
    # API endpoints
    path('api/upload/', views.upload_dicom_files, name='upload_dicom'),
    path('api/studies/', views.get_studies, name='get_studies'),
    path('api/studies/<int:study_id>/images/', views.get_study_images, name='get_study_images'),
    path('api/images/<int:image_id>/', views.get_image_data, name='get_image_data'),
    
    # Measurements and annotations
    path('api/measurements/', views.save_measurement, name='save_measurement'),
    path('api/annotations/', views.save_annotation, name='save_annotation'),
    path('api/images/<int:image_id>/measurements/', views.get_measurements, name='get_measurements'),
    path('api/images/<int:image_id>/annotations/', views.get_annotations, name='get_annotations'),
    path('api/images/<int:image_id>/measurements/clear/', views.clear_measurements, name='clear_measurements'),
    path('api/measure-hu/', views.measure_hu, name='measure_hu'),
    
    # Clinical information
    path('api/studies/<int:study_id>/clinical-info/', views.get_clinical_info, name='get_clinical_info'),
    path('api/studies/<int:study_id>/clinical-info/save/', views.save_clinical_info, name='save_clinical_info'),
    
    # Reports
    path('api/studies/<int:study_id>/report/', views.get_report, name='get_report'),
    path('api/studies/<int:study_id>/report/save/', views.save_report, name='save_report'),
    
    # Notifications
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # 3D and AI features
    path('api/3d-reconstruction-types/', views.get_3d_reconstruction_types, name='get_3d_reconstruction_types'),
    path('api/ai-analysis-types/', views.get_ai_analysis_types, name='get_ai_analysis_types'),
]