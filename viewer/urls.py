from django.urls import path
from . import views

app_name = 'viewer'

urlpatterns = [
    # Home page
    path('home/', views.HomeView.as_view(), name='home'),
    
    # Main viewer page
    path('', views.DicomViewerView.as_view(), name='viewer'),
    path('study/<int:study_id>/', views.DicomViewerView.as_view(), name='viewer_with_study'),
    
    # File upload
    path('api/upload/', views.upload_dicom_files, name='upload_dicom'),
    path('api/upload/folder/', views.upload_dicom_folder, name='upload_dicom_folder'),
    
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
    
    # AI Analysis
    path('api/images/<int:image_id>/ai-analysis/', views.perform_ai_analysis, name='ai_analysis'),
    
    # 3D Reconstruction
    path('api/series/<int:series_id>/3d-reconstruction/', views.get_3d_reconstruction, name='3d_reconstruction'),
]