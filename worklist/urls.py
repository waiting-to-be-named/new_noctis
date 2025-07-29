from django.urls import path
from . import views

app_name = 'worklist'

urlpatterns = [
    # Main worklist
    path('', views.WorklistView.as_view(), name='worklist'),
    
    # Facility-specific worklist
    path('facility/<int:facility_id>/', views.FacilityWorklistView.as_view(), name='facility_worklist'),
    
    # Clinical info
    path('entry/<int:entry_id>/clinical-info/', views.add_clinical_info, name='add_clinical_info'),
    
    # View study from worklist
    path('entry/<int:entry_id>/view/', views.view_study_from_worklist, name='view_study'),
    
    # Report management
    path('study/<int:study_id>/report/', views.create_report, name='create_report'),
    path('report/<int:report_id>/print/', views.print_report, name='print_report'),
    
    # Notifications
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notification/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # Chat
    path('chat/messages/', views.get_chat_messages, name='get_chat_messages'),
    path('chat/send/', views.send_chat_message, name='send_chat_message'),
    path('chat/clear/', views.clear_old_chat_messages, name='clear_old_chat_messages'),
]