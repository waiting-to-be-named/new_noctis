from django.urls import path
from . import views

app_name = 'dicom_server'

urlpatterns = [
    # Main configuration view
    path('config/', views.DicomServerConfigView.as_view(), name='config'),
    
    # API endpoints
    path('api/config/update/', views.update_server_config, name='update_config'),
    path('api/facility/<int:facility_id>/generate-ae-title/', views.generate_facility_ae_title, name='generate_ae_title'),
    path('api/ae-title/<int:ae_title_id>/delete/', views.delete_facility_ae_title, name='delete_ae_title'),
    path('api/logs/', views.get_transfer_logs, name='get_logs'),
    path('api/status/', views.server_status, name='server_status'),
]