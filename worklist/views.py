from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
import os
import mimetypes
from .models import Study, Series, DICOMImage, Report, Notification, AuditLog, Facility, CustomUser, UserRole, StudyAttachment
from .notification_service import NotificationService
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)

# Initialize notification service
notification_service = NotificationService()

@login_required
def worklist_view(request):
    """Main worklist view with role-based filtering"""
    # Get studies based on user role
    if hasattr(request.user, 'role'):
        accessible_studies = request.user.get_accessible_studies()
    else:
        # Fallback for existing users without roles
        accessible_studies = Study.objects.all()
    
    # Apply filters
    status_filter = request.GET.get('status')
    modality_filter = request.GET.get('modality')
    date_filter = request.GET.get('date')
    search_query = request.GET.get('search')
    
    if status_filter:
        accessible_studies = accessible_studies.filter(status=status_filter)
    
    if modality_filter:
        accessible_studies = accessible_studies.filter(series__modality=modality_filter).distinct()
    
    if date_filter:
        accessible_studies = accessible_studies.filter(study_date=date_filter)
    
    if search_query:
        accessible_studies = accessible_studies.filter(
            patient_name__icontains=search_query
        ).union(
            accessible_studies.filter(patient_id__icontains=search_query)
        ).union(
            accessible_studies.filter(accession_number__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(accessible_studies.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    studies = paginator.get_page(page_number)
    
    # Get user's unread notifications
    unread_notifications = 0
    if hasattr(request.user, 'notifications'):
        unread_notifications = request.user.notifications.filter(is_read=False).count()
    
    context = {
        'studies': studies,
        'unread_notifications': unread_notifications,
        'user_role': getattr(request.user, 'role', None),
        'user_facility': getattr(request.user, 'facility', None),
        'current_filters': {
            'status': status_filter,
            'modality': modality_filter,
            'date': date_filter,
            'search': search_query,
        }
    }
    
    return render(request, 'worklist/worklist.html', context)

@login_required
def study_detail(request, study_id):
    """Study detail view with role-based access"""
    study = get_object_or_404(Study, id=study_id)
    
    # Check access permissions
    if hasattr(request.user, 'can_view_study'):
        if not request.user.can_view_study(study):
            return HttpResponse('Access denied. You do not have permission to view this study.', status=403)
    
    # Log access
    AuditLog.objects.create(
        user=request.user,
        action='view_study',
        description=f"Viewed study {study.study_instance_uid}",
        study=study,
        facility=getattr(request.user, 'facility', None),
        ip_address=get_client_ip(request)
    )
    
    # Get related data
    series_list = study.series_set.all().order_by('series_number')
    reports = study.reports.all().order_by('-created_at')
    
    # Filter reports based on user role
    if hasattr(request.user, 'role'):
        if request.user.role in [UserRole.FACILITY, UserRole.TECHNICIAN]:
            reports = reports.filter(status__in=['final', 'amended'])
    
    context = {
        'study': study,
        'series_list': series_list,
        'reports': reports,
        'can_edit': hasattr(request.user, 'can_edit_study') and request.user.can_edit_study(study),
        'can_create_report': hasattr(request.user, 'role') and request.user.role in [UserRole.RADIOLOGIST, UserRole.ADMIN],
    }
    
    return render(request, 'worklist/study_detail.html', context)

@login_required
def create_edit_report(request, study_id):
    """Create or edit radiology report - Enhanced version"""
    study = get_object_or_404(Study, id=study_id)
    
    # Check permissions - only radiologists and admins can create/edit reports
    if not (hasattr(request.user, 'role') and request.user.role in [UserRole.RADIOLOGIST, UserRole.ADMIN]):
        return HttpResponse('Access denied. Only radiologists and administrators can create reports.', status=403)
    
    # Check if user can view this study
    if hasattr(request.user, 'can_view_study') and not request.user.can_view_study(study):
        return HttpResponse('Access denied. You do not have permission to access this study.', status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        
        # Get or create report
        report, created = Report.objects.get_or_create(
            study=study,
            status__in=['draft', 'preliminary'],
            defaults={
                'radiologist': request.user,
                'clinical_history': data.get('clinical_history', ''),
                'technique': data.get('technique', ''),
                'findings': data.get('findings', ''),
                'impression': data.get('impression', ''),
                'recommendations': data.get('recommendations', ''),
                'comparison_studies': data.get('comparison_studies', ''),
                'limitations': data.get('limitations', ''),
                'status': 'draft'
            }
        )
        
        # Update existing report if not created
        if not created and report.can_edit(request.user):
            report.clinical_history = data.get('clinical_history', report.clinical_history)
            report.technique = data.get('technique', report.technique)
            report.findings = data.get('findings', report.findings)
            report.impression = data.get('impression', report.impression)
            report.recommendations = data.get('recommendations', report.recommendations)
            report.comparison_studies = data.get('comparison_studies', report.comparison_studies)
            report.limitations = data.get('limitations', report.limitations)
        elif not created:
            return JsonResponse({'success': False, 'error': 'Cannot edit this report'})
        
        # Handle finalization
        if data.get('finalize') and report.radiologist == request.user:
            success = report.finalize(request.user)
            if success:
                # Update study status
                study.status = 'reviewed'
                study.reviewed_at = timezone.now()
                study.save()
                
                # Send notifications
                notification_service.send_report_ready_notification(report)
        
        report.save()
        
        # Log the action
        action = 'create_report' if created else 'edit_report'
        AuditLog.objects.create(
            user=request.user,
            action=action,
            description=f"{'Created' if created else 'Updated'} report for study {study.study_instance_uid}",
            study=study,
            facility=getattr(request.user, 'facility', None),
            ip_address=get_client_ip(request)
        )
        
        return JsonResponse({
            'success': True,
            'report_id': report.id,
            'status': report.status,
            'created': created
        })
    
    else:
        # GET request
        try:
            report = Report.objects.filter(study=study).latest('created_at')
        except Report.DoesNotExist:
            report = None
        
        # Get previous studies for comparison
        previous_studies = Study.objects.filter(
            patient_id=study.patient_id,
            study_date__lt=study.study_date
        ).order_by('-study_date')[:5]
        
        context = {
            'study': study,
            'report': report,
            'previous_studies': previous_studies,
            'is_radiologist': hasattr(request.user, 'role') and request.user.role == UserRole.RADIOLOGIST,
            'is_admin': hasattr(request.user, 'role') and request.user.role == UserRole.ADMIN,
            'can_edit': report is None or (report and report.can_edit(request.user)),
        }
        return render(request, 'worklist/report.html', context)

@login_required
def attach_files(request, study_id):
    """Attach files to a study - Available to everyone"""
    study = get_object_or_404(Study, id=study_id)
    
    # Everyone can attach files, but check basic study access
    if hasattr(request.user, 'can_view_study') and not request.user.can_view_study(study):
        return HttpResponse('Access denied. You do not have permission to access this study.', status=403)
    
    if request.method == 'POST':
        try:
            uploaded_files = request.FILES.getlist('attachments')
            attachment_notes = request.POST.get('notes', '')
            
            attachments_created = []
            
            for file in uploaded_files:
                # Validate file
                if file.size > 100 * 1024 * 1024:  # 100MB limit
                    return JsonResponse({
                        'success': False, 
                        'error': f'File {file.name} is too large. Maximum size is 100MB.'
                    })
                
                # Determine file type
                file_type = 'other'
                content_type = file.content_type or mimetypes.guess_type(file.name)[0]
                
                if content_type:
                    if content_type.startswith('application/dicom') or file.name.lower().endswith(('.dcm', '.dicom')):
                        file_type = 'dicom'
                    elif content_type.startswith('application/pdf'):
                        file_type = 'report'
                    elif content_type.startswith('image/'):
                        file_type = 'image'
                
                # Save file
                filename = f"attachments/{study.id}/{file.name}"
                file_path = default_storage.save(filename, ContentFile(file.read()))
                
                # Create attachment record
                attachment = StudyAttachment.objects.create(
                    study=study,
                    uploaded_by=request.user,
                    file_name=file.name,
                    file_path=file_path,
                    file_type=file_type,
                    file_size=file.size,
                    notes=attachment_notes
                )
                
                attachments_created.append({
                    'id': attachment.id,
                    'name': attachment.file_name,
                    'type': attachment.file_type,
                    'size': attachment.file_size,
                    'uploaded_at': attachment.uploaded_at.isoformat()
                })
            
            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='attach_files',
                description=f"Attached {len(uploaded_files)} files to study {study.study_instance_uid}",
                study=study,
                facility=getattr(request.user, 'facility', None),
                ip_address=get_client_ip(request)
            )
            
            return JsonResponse({
                'success': True,
                'attachments': attachments_created,
                'message': f'Successfully attached {len(uploaded_files)} files'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error uploading files: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def view_attachment(request, attachment_id):
    """View attached files - Enhanced for DICOM and reports"""
    attachment = get_object_or_404(StudyAttachment, id=attachment_id)
    study = attachment.study
    
    # Check access permissions
    if hasattr(request.user, 'can_view_study') and not request.user.can_view_study(study):
        return HttpResponse('Access denied. You do not have permission to view this attachment.', status=403)
    
    # Enhanced access for admin/radiologist
    can_view_all = hasattr(request.user, 'role') and request.user.role in [UserRole.ADMIN, UserRole.RADIOLOGIST]
    
    try:
        file_path = attachment.file_path
        
        if attachment.file_type == 'dicom' and can_view_all:
            # Redirect to DICOM viewer for DICOM files
            return redirect(f'/viewer/?dicom_file={attachment.id}')
        
        elif attachment.file_type == 'report' and can_view_all:
            # Open PDF reports in browser
            with default_storage.open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'inline; filename="{attachment.file_name}"'
                return response
        
        elif attachment.file_type == 'image':
            # Display images
            with default_storage.open(file_path, 'rb') as f:
                content_type = mimetypes.guess_type(attachment.file_name)[0] or 'application/octet-stream'
                response = HttpResponse(f.read(), content_type=content_type)
                response['Content-Disposition'] = f'inline; filename="{attachment.file_name}"'
                return response
        
        else:
            # Download other files
            with default_storage.open(file_path, 'rb') as f:
                content_type = mimetypes.guess_type(attachment.file_name)[0] or 'application/octet-stream'
                response = HttpResponse(f.read(), content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{attachment.file_name}"'
                return response
    
    except FileNotFoundError:
        return HttpResponse('File not found', status=404)
    except Exception as e:
        return HttpResponse(f'Error accessing file: {str(e)}', status=500)

@login_required
def print_report(request, report_id):
    """Generate printable report with enhanced access control"""
    report = get_object_or_404(Report, id=report_id)
    study = report.study
    
    # Check if user can print this report
    if not report.can_print(request.user):
        return HttpResponse('Access denied. You do not have permission to print this report.', status=403)
    
    # Record print action
    report.record_print(request.user)
    
    # Get printable content
    content = report.get_printable_content()
    content['metadata']['_printed_by'] = request.user
    
    # Return HTML for printing (you can also generate PDF here)
    return render(request, 'worklist/report_print.html', {
        'content': content,
        'report': report,
        'study': study
    })

@login_required
def get_notifications(request):
    """Get user notifications"""
    if not hasattr(request.user, 'notifications'):
        return JsonResponse({'notifications': []})
    
    notifications = request.user.notifications.filter(is_read=False).order_by('-created_at')[:10]
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'created_at': notification.created_at.isoformat(),
            'study_id': notification.study.id if notification.study else None
        })
    
    return JsonResponse({'notifications': notifications_data})

@login_required
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    if request.method == 'POST':
        try:
            notification = request.user.notifications.get(id=notification_id)
            notification.mark_as_read()
            return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False, 'error': 'Notification not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# New API endpoints for enhanced functionality

@login_required
def api_notifications(request):
    """API endpoint for notifications with filtering"""
    filter_type = request.GET.get('filter', 'all')
    
    notifications = Notification.objects.filter(recipient=request.user)
    
    if filter_type != 'all':
        notifications = notifications.filter(notification_type=filter_type)
    
    notifications = notifications.order_by('-created_at')[:50]
    
    data = [{
        'id': n.id,
        'notification_type': n.notification_type,
        'title': n.title,
        'message': n.message,
        'is_read': n.is_read,
        'created_at': n.created_at.isoformat(),
        'related_study_id': n.related_study.id if n.related_study else None
    } for n in notifications]
    
    return JsonResponse({'notifications': data})


@login_required
def api_notifications_count(request):
    """Get count of unread notifications and messages"""
    unread_notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    # Count unread messages including facility-wide messages
    unread_messages = ChatMessage.objects.filter(
        Q(recipient=request.user, is_read=False) |
        Q(recipient__isnull=True, is_read=False)  # Facility-wide messages
    ).count()
    
    return JsonResponse({
        'unread_notifications': unread_notifications,
        'unread_messages': unread_messages
    })


@login_required
@require_http_methods(['POST'])
def api_notifications_mark_read(request, notification_id):
    """Mark specific notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})


@login_required
@require_http_methods(['POST'])
def api_notifications_mark_all_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
@require_http_methods(['POST'])
def api_notifications_clear_old(request):
    """Clear old read notifications"""
    from datetime import timedelta
    week_ago = timezone.now() - timedelta(days=7)
    
    deleted_count = Notification.objects.filter(
        recipient=request.user,
        is_read=True,
        created_at__lt=week_ago
    ).delete()[0]
    
    return JsonResponse({'success': True, 'deleted_count': deleted_count})


@login_required
def api_chat_messages(request):
    """API endpoint for chat messages with filtering"""
    filter_type = request.GET.get('filter', 'all')
    
    # Get messages where user is sender, recipient, or facility-wide messages
    messages = ChatMessage.objects.filter(
        Q(sender=request.user) | 
        Q(recipient=request.user) |
        Q(recipient__isnull=True)  # Facility-wide messages
    )
    
    if filter_type != 'all':
        messages = messages.filter(message_type=filter_type)
    
    messages = messages.order_by('-created_at')[:50]
    
    data = [{
        'id': m.id,
        'sender_name': m.sender.get_full_name() or m.sender.username,
        'recipient_name': m.recipient.get_full_name() or m.recipient.username if m.recipient else 'Facility',
        'message_type': m.message_type,
        'message': m.message,
        'is_read': m.is_read,
        'created_at': m.created_at.isoformat(),
        'facility_name': m.facility.name if m.facility else None
    } for m in messages]
    
    return JsonResponse({'messages': data})


@login_required
@require_http_methods(['POST'])
def api_chat_send(request):
    """Send a new chat message"""
    try:
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        facility_id = data.get('facility_id')
        
        if not message_text:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        
        facility = None
        recipients = []
        
        if facility_id:
            try:
                facility = Facility.objects.get(id=facility_id)
                
                # Check if user can send messages to this facility
                if not (request.user.is_superuser or 
                        request.user.groups.filter(name='Radiologists').exists() or
                        (hasattr(request.user, 'facility') and 
                         request.user.facility == facility)):
                    return JsonResponse({'success': False, 'error': 'Access denied. You can only send messages to your own facility.'}, status=403)
                
                # Find facility staff to send message to
                # Get all users associated with this facility
                if facility.user:
                    recipients.append(facility.user)
                # Also get any users who have this facility assigned
                facility_users = User.objects.filter(worklistentry__facility=facility).distinct()
                recipients.extend(facility_users)
            except Facility.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Facility not found'})
        
        # Create chat message (facility-wide message)
        chat_message = ChatMessage.objects.create(
            sender=request.user,
            recipient=None,  # None means facility-wide message
            facility=facility,
            message_type='user_chat',
            message=message_text
        )
        
        # Create notifications for all facility recipients
        for recipient in recipients:
            if recipient != request.user:  # Don't notify self
                Notification.objects.create(
                    recipient=recipient,
                    notification_type='chat',
                    title='New Chat Message',
                    message=f'{request.user.get_full_name() or request.user.username}: {message_text[:50]}...'
                )
        
        return JsonResponse({'success': True})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def api_chat_clear(request):
    """Clear chat history"""
    deleted_count = ChatMessage.objects.filter(
        Q(sender=request.user) | 
        Q(recipient=request.user) |
        Q(recipient__isnull=True)  # Also clear facility-wide messages
    ).delete()[0]
    
    return JsonResponse({'success': True, 'deleted_count': deleted_count})


def create_notification(user, notification_type, title, message, related_study=None):
    """Helper function to create notifications"""
    Notification.objects.create(
        recipient=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_study=related_study
    )


def create_system_upload_message(study, user):
    """Create a system upload message when a study is uploaded"""
    ChatMessage.objects.create(
        sender=user,
        message_type='system_upload',
        message=f'New study uploaded: {study.patient_name} - {study.study_description or study.modality}',
        related_study=study
    )


@login_required
@require_http_methods(['DELETE'])
def delete_worklist_entry(request, entry_id):
    """Delete a worklist entry - admin only"""
    # Check if user is admin
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied. Admin access required.'}, status=403)
    
    try:
        entry = get_object_or_404(WorklistEntry, id=entry_id)
        entry_name = f"{entry.patient_name} - {entry.accession_number}"
        
        # Delete the entry
        entry.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Worklist entry "{entry_name}" has been deleted successfully.'
        })
    except Exception as e:
        return JsonResponse({'error': f'Failed to delete worklist entry: {str(e)}'}, status=500)

@csrf_exempt
def api_studies(request):
    """Enhanced API endpoint for worklist studies"""
    try:
        # Get all studies with enhanced data
        studies = DicomStudy.objects.select_related('facility').all().order_by('-created_at')
        
        studies_data = []
        for study in studies:
            study_data = {
                'id': study.id,
                'patient_name': study.patient_name,
                'patient_id': study.patient_id,
                'patient_birth_date': study.patient_birth_date.isoformat() if hasattr(study, 'patient_birth_date') and study.patient_birth_date else None,
                'accession_number': study.accession_number,
                'study_date': study.study_date.isoformat() if study.study_date else None,
                'study_description': study.study_description,
                'modality': study.modality,
                'status': getattr(study, 'status', 'completed'),  # Default status if not available
                'facility_name': study.facility.name if study.facility else 'Unknown',
                'facility_id': study.facility.id if study.facility else None,
                'image_count': study.dicomseries_set.aggregate(
                    total_images=Count('dicomimage')
                )['total_images'] or 0,
                'series_count': study.dicomseries_set.count(),
                'created_at': study.created_at.isoformat(),
            }
            studies_data.append(study_data)
        
        return JsonResponse({
            'success': True,
            'studies': studies_data,
            'total_count': len(studies_data)
        })
        
    except Exception as e:
        logger.error(f"Error in api_studies: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt  
def api_notifications(request):
    """API endpoint for notifications"""
    try:
        # In a real implementation, this would check for actual notifications
        # For now, return a simple response
        return JsonResponse({
            'success': True,
            'count': 0,
            'notifications': []
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
