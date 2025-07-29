from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    path('', views.DicomViewerView.as_view(), name='viewer'),
    path('study/<int:study_id>/', views.DicomViewerView.as_view(), name='viewer_with_study'),
    
    # Upload endpoints
    path('upload/', views.upload_dicom_files, name='upload_dicom'),
    path('upload/folder/', views.upload_dicom_folder, name='upload_dicom_folder'),
    
    # API endpoints
    path('api/studies/', views.get_studies, name='api_studies'),
    path('api/studies/<int:study_id>/images/', views.get_study_images, name='api_study_images'),
    path('api/images/<int:image_id>/data/', views.get_image_data, name='api_image_data'),
    path('api/images/<int:image_id>/measurements/', views.get_measurements, name='api_measurements'),
    path('api/images/<int:image_id>/annotations/', views.get_annotations, name='api_annotations'),
    path('api/images/<int:image_id>/measurements/clear/', views.clear_measurements, name='api_clear_measurements'),
    path('api/images/<int:image_id>/ai-analysis/', views.perform_ai_analysis, name='api_ai_analysis'),
    path('api/series/<int:series_id>/3d-reconstruction/', views.get_3d_reconstruction, name='api_3d_reconstruction'),
    path('api/study/<int:study_id>/clinical-info/', views.api_study_clinical_info, name='api_clinical_info'),
    
    # Notification endpoints
    path('api/notifications/', views.get_notifications, name='api_notifications'),
    path('api/notifications/unread-count/', views.get_unread_notification_count, name='api_unread_count'),
    path('api/notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='api_mark_read'),
    path('api/notifications/clear-all/', views.clear_all_notifications, name='api_clear_notifications'),
    
    # Measurement endpoints
    path('api/measurements/save/', views.save_measurement, name='api_save_measurement'),
    path('api/measurements/hu/', views.measure_hu, name='api_measure_hu'),
    path('api/annotations/save/', views.save_annotation, name='api_save_annotation'),
    path('api/volume/calculate/', views.calculate_volume, name='api_calculate_volume'),
    
    # Admin endpoints
    path('admin/facilities/', views.FacilityListView.as_view(), name='facility_list'),
    path('admin/facilities/create/', views.FacilityCreateView.as_view(), name='facility_create'),
    path('admin/facilities/<int:pk>/edit/', views.FacilityUpdateView.as_view(), name='facility_edit'),
    path('admin/facilities/<int:pk>/delete/', views.delete_facility, name='facility_delete'),
    path('admin/radiologists/', views.RadiologistListView.as_view(), name='radiologist_list'),
    path('admin/radiologists/create/', views.create_radiologist, name='radiologist_create'),
    path('admin/radiologists/<int:pk>/delete/', views.delete_radiologist, name='radiologist_delete'),
]