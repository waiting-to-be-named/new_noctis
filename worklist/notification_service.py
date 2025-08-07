"""
Notification Service
Handles sending notifications to users based on their roles and preferences
"""

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Notification, CustomUser, UserRole
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for managing notifications"""
    
    def __init__(self):
        self.email_enabled = hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST
        
    def send_notification(self, recipients, notification_type, title, message, study=None, facility=None):
        """Send notification to multiple recipients"""
        notifications_created = []
        
        for recipient in recipients:
            # Check if user wants this type of notification
            if hasattr(recipient, 'notification_types') and recipient.notification_types:
                if notification_type not in recipient.notification_types:
                    continue
            
            # Create notification record
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                study=study,
                facility=facility
            )
            
            notifications_created.append(notification)
            
            # Send email if enabled and user wants emails
            if (self.email_enabled and 
                hasattr(recipient, 'email_notifications') and 
                recipient.email_notifications and 
                recipient.email):
                self.send_email_notification(recipient, notification)
        
        return notifications_created
    
    def send_email_notification(self, user, notification):
        """Send email notification"""
        try:
            subject = f"NOCTIS Alert: {notification.title}"
            
            context = {
                'user': user,
                'notification': notification,
                'study': notification.study,
                'facility': notification.facility
            }
            
            # Render email template
            html_message = render_to_string('emails/notification.html', context)
            plain_message = render_to_string('emails/notification.txt', context)
            
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@noctisview.duckdns.org'),
                recipient_list=[user.email],
                fail_silently=False
            )
            
            # Mark email as sent
            notification.is_email_sent = True
            notification.save(update_fields=['is_email_sent'])
            
        except Exception as e:
            logger.error(f"Failed to send email notification to {user.email}: {str(e)}")
    
    def send_report_ready_notification(self, report):
        """Send notification when a report is ready"""
        study = report.study
        
        # Notify facility users
        facility_users = CustomUser.objects.filter(
            facility=study.facility,
            role__in=[UserRole.FACILITY, UserRole.TECHNICIAN],
            is_active=True
        )
        
        if facility_users.exists():
            self.send_notification(
                recipients=facility_users,
                notification_type='report_ready',
                title=f'Report Ready - {study.patient_name}',
                message=f'Radiology report is now available for study: {study.study_description}',
                study=study,
                facility=study.facility
            )
        
        # Notify admins
        admin_users = CustomUser.objects.filter(
            role=UserRole.ADMIN,
            is_active=True
        )
        
        if admin_users.exists():
            self.send_notification(
                recipients=admin_users,
                notification_type='report_ready',
                title=f'Report Completed - {study.patient_name}',
                message=f'Dr. {report.radiologist.get_full_name()} completed report for {study.study_description}',
                study=study,
                facility=study.facility
            )
    
    def send_upload_notification(self, study, uploaded_by):
        """Send notification when new DICOM data is uploaded"""
        
        # Notify radiologists
        radiologists = CustomUser.objects.filter(
            role=UserRole.RADIOLOGIST,
            is_active=True
        )
        
        if radiologists.exists():
            self.send_notification(
                recipients=radiologists,
                notification_type='new_study',
                title=f'New Study Available - {study.patient_name}',
                message=f'New study uploaded: {study.study_description} by {uploaded_by.get_full_name()}',
                study=study,
                facility=study.facility
            )
        
        # Notify admins
        admin_users = CustomUser.objects.filter(
            role=UserRole.ADMIN,
            is_active=True
        )
        
        if admin_users.exists():
            self.send_notification(
                recipients=admin_users,
                notification_type='new_study',
                title=f'New Study Uploaded - {study.patient_name}',
                message=f'Study uploaded by {uploaded_by.get_full_name()} from {study.facility.name}',
                study=study,
                facility=study.facility
            )
    
    def send_error_notification(self, error_type, message, user=None, study=None):
        """Send error notifications to admins"""
        admin_users = CustomUser.objects.filter(
            role=UserRole.ADMIN,
            is_active=True
        )
        
        if admin_users.exists():
            title = f'System Error: {error_type}'
            full_message = f'{message}'
            if user:
                full_message += f'\nUser: {user.get_full_name()} ({user.username})'
            if study:
                full_message += f'\nStudy: {study.patient_name} - {study.study_description}'
            
            self.send_notification(
                recipients=admin_users,
                notification_type='system_alert',
                title=title,
                message=full_message,
                study=study
            )
    
    def send_quota_warning(self, facility):
        """Send quota warning notification"""
        # Calculate usage
        usage_gb = facility.get_upload_usage_gb()
        quota_gb = facility.upload_quota_gb
        usage_percent = (usage_gb / quota_gb) * 100 if quota_gb > 0 else 0
        
        if usage_percent >= 90:
            # Notify facility users
            facility_users = CustomUser.objects.filter(
                facility=facility,
                is_active=True
            )
            
            # Notify admins
            admin_users = CustomUser.objects.filter(
                role=UserRole.ADMIN,
                is_active=True
            )
            
            all_users = list(facility_users) + list(admin_users)
            
            if all_users:
                self.send_notification(
                    recipients=all_users,
                    notification_type='quota_warning',
                    title=f'Storage Quota Warning - {facility.name}',
                    message=f'Storage usage is at {usage_percent:.1f}% ({usage_gb:.1f}GB of {quota_gb}GB)',
                    facility=facility
                )
    
    def send_dicom_received_notification(self, study, source='Remote Modality'):
        """Send notification when DICOM data is received from remote modality"""
        
        # Notify facility users if study is assigned to a facility
        if study.facility:
            facility_users = CustomUser.objects.filter(
                facility=study.facility,
                role__in=[UserRole.FACILITY, UserRole.TECHNICIAN],
                is_active=True
            )
            
            if facility_users.exists():
                self.send_notification(
                    recipients=facility_users,
                    notification_type='dicom_received',
                    title=f'DICOM Received - {study.patient_name}',
                    message=f'New DICOM study received from {source}: {study.study_description}',
                    study=study,
                    facility=study.facility
                )
        
        # Notify radiologists
        radiologists = CustomUser.objects.filter(
            role=UserRole.RADIOLOGIST,
            is_active=True
        )
        
        if radiologists.exists():
            self.send_notification(
                recipients=radiologists,
                notification_type='dicom_received',
                title=f'DICOM Study Received - {study.patient_name}',
                message=f'New study from {source}: {study.study_description}',
                study=study,
                facility=study.facility
            )
        
        # Notify admins
        admin_users = CustomUser.objects.filter(
            role=UserRole.ADMIN,
            is_active=True
        )
        
        if admin_users.exists():
            self.send_notification(
                recipients=admin_users,
                notification_type='dicom_received',
                title=f'DICOM Received from {source}',
                message=f'Study: {study.patient_name} - {study.study_description}',
                study=study,
                facility=study.facility
            )