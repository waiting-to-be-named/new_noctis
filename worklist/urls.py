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
    
    # Delete worklist entry
    path('entry/<int:entry_id>/delete/', views.delete_worklist_entry, name='delete_entry'),
    
    # Report management
    path('study/<int:study_id>/report/', views.create_report, name='create_report'),
    path('report/<int:report_id>/print/', views.print_report, name='print_report'),
    
    # Notifications
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # API endpoints
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/notifications/count/', views.api_notifications_count, name='api_notifications_count'),
    path('api/notifications/<int:notification_id>/read/', views.api_notifications_mark_read, name='api_notifications_mark_read'),
    path('api/notifications/mark-all-read/', views.api_notifications_mark_all_read, name='api_notifications_mark_all_read'),
    path('api/notifications/clear-old/', views.api_notifications_clear_old, name='api_notifications_clear_old'),
    
    # Chat API endpoints
    path('api/chat/', views.api_chat_messages, name='api_chat_messages'),
    path('api/chat/send/', views.api_chat_send, name='api_chat_send'),
    path('api/chat/clear/', views.api_chat_clear, name='api_chat_clear'),
    path('api/chat/<int:message_id>/read/', views.api_chat_message_read, name='api_chat_message_read'),
]