from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q, Count
from django.contrib.auth.models import User
from viewer.models import (
    DicomStudy, WorklistEntry, Facility, Report, 
    Notification, DicomSeries, DicomImage, ChatMessage
)
import json
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import io
import logging

logger = logging.getLogger(__name__)


class WorklistView(LoginRequiredMixin, ListView):
    """Main worklist view showing all patients"""
    model = WorklistEntry
    template_name = 'worklist/worklist.html'
    context_object_name = 'entries'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Debug: Print total count before filtering
        total_count = WorklistEntry.objects.count()
        print(f"Total worklist entries in database: {total_count}")
        
        # Filter by facility if user is facility staff
        if hasattr(self.request.user, 'facility') and self.request.user.facility:
            # Facility users see only their facility's worklist entries
            queryset = queryset.filter(facility=self.request.user.facility)
            print(f"Filtered by facility, count: {queryset.count()}")
        elif self.request.user.groups.filter(name='Facilities').exists():
            # Facility group members without specific facility see nothing
            queryset = queryset.none()
            print(f"No facility assigned, showing no entries")
        else:
            # Admin and radiologists see all worklist entries
            print(f"Admin/Radiologist access, showing all entries: {queryset.count()}")
        
        # Apply search filters
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(patient_name__icontains=search) |
                Q(patient_id__icontains=search) |
                Q(accession_number__icontains=search)
            )
            print(f"After search filter '{search}': {queryset.count()}")
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            print(f"After status filter '{status}': {queryset.count()}")
            
        # Filter by modality
        modality = self.request.GET.get('modality')
        if modality:
            queryset = queryset.filter(modality=modality)
            print(f"After modality filter '{modality}': {queryset.count()}")
        
        # Filter by date range
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            queryset = queryset.filter(scheduled_procedure_step_start_date__gte=start_date)
            print(f"After start date filter '{start_date}': {queryset.count()}")
        if end_date:
            queryset = queryset.filter(scheduled_procedure_step_start_date__lte=end_date)
            print(f"After end date filter '{end_date}': {queryset.count()}")
        
        print(f"Final queryset count: {queryset.count()}")
        return queryset.order_by('-scheduled_procedure_step_start_date', '-scheduled_procedure_step_start_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['facilities'] = Facility.objects.all()
        context['modalities'] = ['CT', 'MR', 'CR', 'DX', 'US', 'MG', 'PT', 'NM']
        context['is_radiologist'] = self.request.user.groups.filter(name='Radiologists').exists()
        context['is_admin'] = self.request.user.is_superuser
        return context


@login_required
@require_http_methods(['POST'])
def add_clinical_info(request, entry_id):
    """Add clinical information to a worklist entry"""
    entry = get_object_or_404(WorklistEntry, id=entry_id)
    
    # Check permissions - only radiologists, technicians, and admins can add clinical info
    if not (request.user.is_superuser or 
            request.user.groups.filter(name__in=['Radiologists', 'Technicians']).exists()):
        return JsonResponse({'error': 'Permission denied. Only radiologists, technicians, and administrators can add clinical information.'}, status=403)
    
    # Check if user can access this worklist entry
    if not (request.user.is_superuser or 
            request.user.groups.filter(name='Radiologists').exists() or
            (hasattr(request.user, 'facility') and 
             request.user.facility == entry.facility)):
        return JsonResponse({'error': 'Access denied. You do not have permission to access this worklist entry.'}, status=403)
    
    data = json.loads(request.body)
    clinical_info = data.get('clinical_info', '')
    
    # Update associated study if exists
    if entry.study:
        entry.study.clinical_info = clinical_info
        entry.study.save()
    
    return JsonResponse({'success': True})


@login_required
def view_study_from_worklist(request, entry_id):
    """Launch viewer with images from worklist entry"""
    entry = get_object_or_404(WorklistEntry, id=entry_id)
    
    # Check if user can access this worklist entry
    if not (request.user.is_superuser or 
            request.user.groups.filter(name='Radiologists').exists() or
            (hasattr(request.user, 'facility') and 
             request.user.facility == entry.facility)):
        return JsonResponse({'error': 'Access denied. You do not have permission to view this study.'}, status=403)
    
    if entry.study:
        # Redirect to viewer with study ID
        return redirect('viewer:viewer_with_study', study_id=entry.study.id)
    else:
        return JsonResponse({'error': 'No images available for this entry'}, status=404)


class FacilityWorklistView(LoginRequiredMixin, ListView):
    """Facility-specific worklist view"""
    model = WorklistEntry
    template_name = 'worklist/facility_worklist.html'
    context_object_name = 'entries'
    paginate_by = 20
    
    def get_queryset(self):
        facility_id = self.kwargs.get('facility_id')
        facility = get_object_or_404(Facility, id=facility_id)
        
        # Check permissions using the new access control system
        if not (self.request.user.is_superuser or 
                self.request.user.groups.filter(name='Radiologists').exists() or
                (hasattr(self.request.user, 'facility') and 
                 self.request.user.facility == facility)):
            return WorklistEntry.objects.none()
        
        return WorklistEntry.objects.filter(facility=facility)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['facility'] = get_object_or_404(Facility, id=self.kwargs.get('facility_id'))
        context['can_write_report'] = (
            self.request.user.is_superuser or 
            self.request.user.groups.filter(name='Radiologists').exists()
        )
        return context


@login_required
def create_report(request, study_id):
    """Create or edit a radiology report"""
    study = get_object_or_404(DicomStudy, id=study_id)
    
    # Check permissions - only radiologists and admins can create reports
    if not (request.user.is_superuser or 
            request.user.groups.filter(name='Radiologists').exists()):
        return JsonResponse({'error': 'Permission denied. Only radiologists and administrators can create reports.'}, status=403)
    
    # Check if user can access this study
    if not (request.user.is_superuser or 
            request.user.groups.filter(name='Radiologists').exists() or
            (hasattr(request.user, 'facility') and 
             request.user.facility == study.facility)):
        return JsonResponse({'error': 'Access denied. You do not have permission to access this study.'}, status=403)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        
        # Get or create report
        report, created = Report.objects.get_or_create(
            study=study,
            radiologist=request.user,
            defaults={
                'findings': data.get('findings', ''),
                'impression': data.get('impression', ''),
                'recommendations': data.get('recommendations', ''),
                'status': 'draft'
            }
        )
        
        if not created:
            report.findings = data.get('findings', report.findings)
            report.impression = data.get('impression', report.impression)
            report.recommendations = data.get('recommendations', report.recommendations)
            
        if data.get('finalize'):
            report.status = 'finalized'
            report.finalized_at = timezone.now()
            
            # Update worklist entry status to completed
            worklist_entries = WorklistEntry.objects.filter(study=study)
            for entry in worklist_entries:
                entry.status = 'completed'
                entry.save()
            
            # Create notification for facility
            if study.facility:
                facility_users = study.facility.staff.all()
                for user in facility_users:
                    Notification.objects.create(
                        recipient=user,
                        notification_type='report_ready',
                        title=f'Report Ready: {study.patient_name}',
                        message=f'The radiology report for {study.patient_name} is now available.',
                        related_study=study
                    )
        
        report.save()
        
        return JsonResponse({
            'success': True,
            'report_id': report.id,
            'status': report.status
        })
    
    else:
        # GET request - check if it's an AJAX request or regular page load
        if request.headers.get('Content-Type') == 'application/json' or request.headers.get('Accept') == 'application/json':
            # AJAX request - return existing report if any
            try:
                report = Report.objects.filter(study=study).latest('created_at')
                return JsonResponse({
                    'findings': report.findings,
                    'impression': report.impression,
                    'recommendations': report.recommendations,
                    'status': report.status,
                    'radiologist': report.radiologist.get_full_name() or report.radiologist.username,
                    'created_at': report.created_at.isoformat(),
                    'finalized_at': report.finalized_at.isoformat() if report.finalized_at else None
                })
            except Report.DoesNotExist:
                return JsonResponse({})
        else:
            # Regular page request - render report creation template
            try:
                report = Report.objects.filter(study=study).latest('created_at')
            except Report.DoesNotExist:
                report = None
            
            context = {
                'study': study,
                'report': report,
                'is_radiologist': request.user.groups.filter(name='Radiologists').exists(),
                'is_admin': request.user.is_superuser
            }
            return render(request, 'worklist/report.html', context)


@login_required
def print_report(request, report_id):
    """Generate PDF report with facility letterhead"""
    report = get_object_or_404(Report, id=report_id)
    study = report.study
    
    # Check if user can access this study
    if not (request.user.is_superuser or 
            request.user.groups.filter(name='Radiologists').exists() or
            (hasattr(request.user, 'facility') and 
             request.user.facility == study.facility)):
        return HttpResponse('Access denied. You do not have permission to access this report.', status=403)
    
    # Check permissions - allow all authenticated users to print finalized reports
    if report.status not in ['finalized', 'printed']:
        return HttpResponse('Report is not finalized yet', status=403)
    
    # Create PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Add letterhead if facility has logo
    if study.facility and study.facility.letterhead_logo:
        # This is simplified - in production you'd properly handle the logo
        p.drawString(inch, height - inch, study.facility.name)
        p.drawString(inch, height - 1.5*inch, study.facility.address)
        p.drawString(inch, height - 1.75*inch, f"Phone: {study.facility.phone}")
        y_position = height - 2.5*inch
    else:
        y_position = height - inch
    
    # Report header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(inch, y_position, "RADIOLOGY REPORT")
    y_position -= 0.5*inch
    
    # Patient information
    p.setFont("Helvetica", 12)
    p.drawString(inch, y_position, f"Patient: {study.patient_name}")
    y_position -= 0.25*inch
    p.drawString(inch, y_position, f"Patient ID: {study.patient_id}")
    y_position -= 0.25*inch
    p.drawString(inch, y_position, f"Study Date: {study.study_date}")
    y_position -= 0.25*inch
    p.drawString(inch, y_position, f"Modality: {study.modality}")
    y_position -= 0.5*inch
    
    # Clinical Information
    if study.clinical_info:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(inch, y_position, "CLINICAL INFORMATION:")
        y_position -= 0.25*inch
        p.setFont("Helvetica", 10)
        # Wrap text - simplified version
        lines = study.clinical_info.split('\n')
        for line in lines[:5]:  # Limit lines for simplicity
            p.drawString(inch, y_position, line[:80])
            y_position -= 0.2*inch
        y_position -= 0.3*inch
    
    # Findings
    p.setFont("Helvetica-Bold", 12)
    p.drawString(inch, y_position, "FINDINGS:")
    y_position -= 0.25*inch
    p.setFont("Helvetica", 10)
    lines = report.findings.split('\n')
    for line in lines[:10]:  # Limit lines for simplicity
        p.drawString(inch, y_position, line[:80])
        y_position -= 0.2*inch
    y_position -= 0.3*inch
    
    # Impression
    p.setFont("Helvetica-Bold", 12)
    p.drawString(inch, y_position, "IMPRESSION:")
    y_position -= 0.25*inch
    p.setFont("Helvetica", 10)
    lines = report.impression.split('\n')
    for line in lines[:5]:
        p.drawString(inch, y_position, line[:80])
        y_position -= 0.2*inch
    y_position -= 0.3*inch
    
    # Recommendations
    if report.recommendations:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(inch, y_position, "RECOMMENDATIONS:")
        y_position -= 0.25*inch
        p.setFont("Helvetica", 10)
        lines = report.recommendations.split('\n')
        for line in lines[:5]:
            p.drawString(inch, y_position, line[:80])
            y_position -= 0.2*inch
    
    # Signature
    y_position -= 0.5*inch
    p.setFont("Helvetica", 10)
    p.drawString(inch, y_position, f"Reported by: {report.radiologist.get_full_name() or report.radiologist.username}")
    y_position -= 0.2*inch
    p.drawString(inch, y_position, f"Date: {report.finalized_at or report.created_at}")
    
    p.showPage()
    p.save()
    
    # Return PDF
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report_{study.patient_name}_{study.study_date}.pdf"'
    
    # Update report status
    if report.status == 'finalized':
        report.status = 'printed'
        report.save()
    
    return response


@login_required
def get_notifications(request):
    """Get unread notifications for the current user"""
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    )[:10]
    
    data = [{
        'id': n.id,
        'type': n.notification_type,
        'title': n.title,
        'message': n.message,
        'study_id': n.related_study.id if n.related_study else None,
        'created_at': n.created_at.isoformat()
    } for n in notifications]
    
    return JsonResponse({'notifications': data})


@login_required
@require_http_methods(['POST'])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})


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


@login_required
def api_worklist(request):
    """API endpoint to get worklist data as JSON"""
    # Get the same queryset as the main worklist view
    queryset = WorklistEntry.objects.all()
    
    # Apply the same filtering logic as WorklistView
    if hasattr(request.user, 'facility') and request.user.facility:
        queryset = queryset.filter(facility=request.user.facility)
    elif request.user.groups.filter(name='Facilities').exists():
        queryset = queryset.none()
    
    # Apply search filters
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(patient_name__icontains=search) |
            Q(patient_id__icontains=search) |
            Q(accession_number__icontains=search)
        )
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        queryset = queryset.filter(status=status)
        
    # Filter by modality
    modality = request.GET.get('modality')
    if modality:
        queryset = queryset.filter(modality=modality)
    
    # Filter by priority (if we add it to the model later)
    priority = request.GET.get('priority')
    
    # Filter by facility (for admins/radiologists)
    facility_id = request.GET.get('facility')
    if facility_id and (request.user.is_superuser or request.user.groups.filter(name='Radiologists').exists()):
        queryset = queryset.filter(facility_id=facility_id)
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        queryset = queryset.filter(scheduled_procedure_step_start_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(scheduled_procedure_step_start_date__lte=end_date)
    
    # Order the results
    queryset = queryset.order_by('-scheduled_procedure_step_start_date', '-scheduled_procedure_step_start_time')
    
    # Convert to JSON format
    patients = []
    for entry in queryset:
        # Determine priority based on status and urgency (simple logic for now)
        if entry.status == 'in_progress':
            priority = 'high'
        elif 'urgent' in entry.procedure_description.lower() or 'emergency' in entry.procedure_description.lower():
            priority = 'high'
        elif 'routine' in entry.procedure_description.lower():
            priority = 'low'
        else:
            priority = 'medium'
        
        patient_data = {
            'id': entry.id,
            'patient_name': entry.patient_name,
            'patient_id': entry.patient_id,
            'modality': entry.modality,
            'study_date': entry.scheduled_procedure_step_start_date.isoformat() if entry.scheduled_procedure_step_start_date else None,
            'study_time': entry.scheduled_procedure_step_start_time.strftime('%H:%M') if entry.scheduled_procedure_step_start_time else None,
            'status': entry.status,
            'priority': priority,
            'facility': entry.facility.name if entry.facility else 'Unknown',
            'facility_id': entry.facility.id if entry.facility else None,
            'accession': entry.accession_number,
            'study_description': entry.procedure_description,
            'physician': entry.scheduled_performing_physician,
            'has_study': bool(entry.study),
            'study_id': entry.study.id if entry.study else None,
            'total_images': entry.study.total_images if entry.study else 0,
            'series_count': entry.study.series_count if entry.study else 0,
        }
        patients.append(patient_data)
    
    # Get statistics
    today = timezone.now().date()
    stats = {
        'total_patients': queryset.count(),
        'scheduled_today': queryset.filter(
            scheduled_procedure_step_start_date=today, 
            status='scheduled'
        ).count(),
        'in_progress': queryset.filter(status='in_progress').count(),
        'completed_today': queryset.filter(
            scheduled_procedure_step_start_date=today, 
            status='completed'
        ).count(),
    }
    
    return JsonResponse({
        'success': True,
        'patients': patients,
        'stats': stats,
        'total_count': queryset.count(),
        'facilities': list(Facility.objects.values('id', 'name')) if request.user.is_superuser or request.user.groups.filter(name='Radiologists').exists() else [],
        'modalities': ['CT', 'MR', 'CR', 'DX', 'US', 'MG', 'PT', 'NM'],
    })
