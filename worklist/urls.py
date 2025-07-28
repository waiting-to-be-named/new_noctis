from django.urls import path
from . import views

app_name = 'worklist'

urlpatterns = [
    # Main worklist pages
    path('', views.WorklistView.as_view(), name='worklist'),
    path('facility/', views.FacilityDashboardView.as_view(), name='facility_dashboard'),
    path('radiologist/', views.RadiologistDashboardView.as_view(), name='radiologist_dashboard'),
    
    # Worklist API endpoints
    path('api/worklist/', views.get_worklist, name='get_worklist'),
    path('api/worklist/create/', views.create_worklist_entry, name='create_worklist_entry'),
    path('api/worklist/<int:entry_id>/launch/', views.launch_viewer, name='launch_viewer'),
    path('api/worklist/<int:entry_id>/clinical-info/', views.update_clinical_info, name='update_clinical_info'),
    
    # Reports
    path('api/reports/', views.manage_reports, name='manage_reports'),
    path('api/worklist/<int:entry_id>/reports/', views.manage_reports, name='entry_reports'),
    path('api/reports/<int:report_id>/print/', views.print_report, name='print_report'),
    
    # Notifications
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # Facilities
    path('api/facilities/', views.get_facilities, name='get_facilities'),
    path('api/facilities/<int:facility_id>/studies/', views.get_facility_studies, name='get_facility_studies'),
    
    # DICOM SCP Server
    path('api/scp-servers/', views.get_scp_servers, name='get_scp_servers'),
    path('api/scp-servers/configure/', views.configure_scp_server, name='configure_scp_server'),
]