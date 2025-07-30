from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    # Main viewer page
    path('', views.DicomViewerView.as_view(), name='viewer'),
    path('study/<int:study_id>/', views.DicomViewerView.as_view(), name='viewer_with_study'),
    
    # Admin functionality
    path('admin/facilities/', views.FacilityListView.as_view(), name='facility_list'),
    path('admin/facilities/new/', views.FacilityCreateView.as_view(), name='facility_create'),
    path('admin/facilities/<int:pk>/edit/', views.FacilityUpdateView.as_view(), name='facility_edit'),
    path('admin/facilities/<int:pk>/delete/', views.delete_facility, name='facility_delete'),
    path('admin/radiologists/', views.RadiologistListView.as_view(), name='radiologist_list'),
    path('admin/radiologists/new/', views.create_radiologist, name='radiologist_create'),
    path('admin/radiologists/<int:pk>/delete/', views.delete_radiologist, name='radiologist_delete'),
    
    # File upload
    path('api/upload/', views.upload_dicom_files, name='upload_dicom'),
    path('api/upload-folder/', views.upload_dicom_folder, name='upload_dicom_folder'),
    path('api/bulk-upload/', views.bulk_upload_dicom_folder, name='bulk_upload_dicom_folder'),
    path('api/upload-progress/<str:upload_id>/', views.get_upload_progress, name='get_upload_progress'),
    path('api/upload-result/<str:upload_id>/', views.get_upload_result, name='get_upload_result'),
    
    # Enhanced bulk upload
    path('api/enhanced-bulk-upload/', views.enhanced_bulk_upload_dicom_folder, name='enhanced_bulk_upload_dicom_folder'),
    path('api/enhanced-upload-progress/<str:upload_id>/', views.get_enhanced_upload_progress, name='get_enhanced_upload_progress'),
    path('api/enhanced-upload-result/<str:upload_id>/', views.get_enhanced_upload_result, name='get_enhanced_upload_result'),
    
    # Study and image data
    path('api/studies/', views.get_studies, name='get_studies'),
    path('api/studies/<int:study_id>/images/', views.get_study_images, name='get_study_images'),
    path('api/images/<int:image_id>/data/', views.get_image_data, name='get_image_data'),
    
    # Enhanced image processing
    path('api/images/<int:image_id>/enhanced-data/', views.get_enhanced_image_data, name='get_enhanced_image_data'),
    
    # Series selector functionality
    path('api/studies/<int:study_id>/series-selector/', views.get_series_selector_data, name='get_series_selector_data'),
    path('api/series/<int:series_id>/enhanced-images/', views.get_enhanced_series_images, name='get_enhanced_series_images'),
    
    # Measurements and annotations
    path('api/measurements/save/', views.save_measurement, name='save_measurement'),
    path('api/annotations/save/', views.save_annotation, name='save_annotation'),
    path('api/images/<int:image_id>/measurements/', views.get_measurements, name='get_measurements'),
    path('api/images/<int:image_id>/annotations/', views.get_annotations, name='get_annotations'),
    path('api/images/<int:image_id>/clear-measurements/', views.clear_measurements, name='clear_measurements'),
    path('api/measurements/hu/', views.measure_hu, name='measure_hu'),
    
    # Volume calculation
    path('api/volume/calculate/', views.calculate_volume, name='calculate_volume'),
    
    # AI Analysis
    path('api/images/<int:image_id>/ai-analysis/', views.perform_ai_analysis, name='ai_analysis'),
    
    # 3D Reconstruction
    path('api/series/<int:series_id>/3d-reconstruction/', views.get_3d_reconstruction, name='3d_reconstruction'),
    
    # Clinical Information
    path('api/study/<int:study_id>/clinical-info/', views.api_study_clinical_info, name='api_study_clinical_info'),
]