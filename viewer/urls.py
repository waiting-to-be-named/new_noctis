from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    # Landing page
    path('', views.IndexView.as_view(), name='index'),
    
    # Main viewer
    path('viewer/', views.DicomViewerView.as_view(), name='viewer'),
    
    # Worklist
    path('worklist/', views.WorklistView.as_view(), name='worklist'),
    
    # API endpoints
    path('api/studies/', views.study_list, name='api_study_list'),
    path('api/studies/<int:study_id>/images/', views.study_images, name='api_study_images'),
    path('api/images/<int:image_id>/pixel-data/', views.image_pixel_data, name='api_image_pixel_data'),
    path('api/upload/', views.upload_dicom_files, name='api_upload'),
    path('api/measurements/', views.save_measurement, name='api_save_measurement'),
    path('api/annotations/', views.save_annotation, name='api_save_annotation'),
    
    # Worklist API
    path('api/worklist/studies', views.worklist_studies, name='api_worklist_studies'),
    path('api/worklist/clinical-info', views.save_clinical_info, name='api_save_clinical_info'),
    path('api/worklist/report', views.manage_report, name='api_manage_report'),
    path('api/worklist/report/<int:study_id>', views.manage_report, name='api_get_report'),
    path('api/worklist/report/<int:study_id>/print', views.print_report, name='print_report'),
    
    # Notifications API
    path('api/worklist/notifications', views.get_notifications, name='api_notifications'),
    path('api/worklist/notifications/unread', views.get_unread_notifications, name='api_unread_notifications'),
    path('api/worklist/notifications/<int:notification_id>/read', views.mark_notification_read, name='api_mark_notification_read'),
]