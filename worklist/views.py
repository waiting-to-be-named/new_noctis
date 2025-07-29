from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
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
        if hasattr(self.request.user, 'facility_staff'):
            queryset = queryset.filter(facility=self.request.user.facility_staff.facility)
            print(f"Filtered by facility, count: {queryset.count()}")
        else:
            print(f"No facility filtering, showing all entries: {queryset.count()}")
        
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
    
    # Check permissions
    if not (request.user.is_superuser or 
            request.user.groups.filter(name__in=['Radiologists', 'Technicians']).exists()):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
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
        
        # Check permissions
        if not (self.request.user.is_superuser or 
                self.request.user.groups.filter(name='Radiologists').exists() or
                (hasattr(self.request.user, 'facility_staff') and 
                 self.request.user.facility_staff.facility == facility)):
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
    
    # Check permissions
    if not (request.user.is_superuser or 
            request.user.groups.filter(name='Radiologists').exists()):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
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
    
    unread_messages = ChatMessage.objects.filter(
        Q(recipient=request.user, is_read=False) |
        Q(recipient__isnull=True, facility__isnull=False, is_read=False)  # Include facility-wide unread messages
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
    facility_id = request.GET.get('facility_id')
    
    # Base query - messages where user is sender or recipient
    messages = ChatMessage.objects.select_related('sender', 'recipient', 'facility', 'related_study').filter(
        Q(sender=request.user) | Q(recipient=request.user) | 
        (Q(recipient__isnull=True) & Q(facility__isnull=False))  # Include facility-wide messages
    )
    
    # Filter by message type
    if filter_type != 'all':
        messages = messages.filter(message_type=filter_type)
    
    # Filter by facility if specified
    if facility_id:
        try:
            facility_id = int(facility_id)
            messages = messages.filter(facility_id=facility_id)
        except (ValueError, TypeError):
            pass
    
    messages = messages.order_by('-created_at')[:50]
    
    data = [{
        'id': m.id,
        'sender_name': m.sender.get_full_name() or m.sender.username,
        'recipient_name': m.recipient.get_full_name() or m.recipient.username if m.recipient else 'All',
        'message_type': m.message_type,
        'message': m.message,
        'is_read': m.is_read,
        'created_at': m.created_at.isoformat(),
        'facility_name': m.facility.name if m.facility else None,
        'related_study_id': m.related_study.id if m.related_study else None
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
        recipient_id = data.get('recipient_id')
        
        if not message_text:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        
        facility = None
        recipient = None
        
        # Handle facility-based messaging
        if facility_id:
            try:
                facility = Facility.objects.get(id=facility_id)
                # Find facility admin/staff as recipient
                if hasattr(facility, 'admin_user') and facility.admin_user:
                    recipient = facility.admin_user
            except Facility.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Facility not found'})
        
        # Handle direct user messaging
        if recipient_id:
            try:
                from django.contrib.auth.models import User
                recipient = User.objects.get(id=recipient_id)
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Recipient not found'})
        
        # Create chat message
        chat_message = ChatMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            facility=facility,
            message_type='user_chat',
            message=message_text
        )
        
        # Create notification for recipient
        if recipient:
            Notification.objects.create(
                recipient=recipient,
                notification_type='chat',
                title='New Chat Message',
                message=f'{request.user.get_full_name() or request.user.username}: {message_text[:50]}{"..." if len(message_text) > 50 else ""}'
            )
        
        # If facility message but no specific recipient, create a general notification
        elif facility:
            # Create notification for facility staff (this could be enhanced to find actual facility users)
            create_notification(
                user=None,  # Will need to be handled differently for facility-wide notifications
                notification_type='chat',
                title='New Facility Message',
                message=f'Message for {facility.name}: {message_text[:50]}{"..." if len(message_text) > 50 else ""}'
            )
        
        return JsonResponse({'success': True, 'message_id': chat_message.id})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def api_chat_clear(request):
    """Clear chat history"""
    deleted_count = ChatMessage.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).delete()[0]
    
    return JsonResponse({'success': True, 'deleted_count': deleted_count})


@login_required
@require_http_methods(['POST'])
def api_chat_message_read(request, message_id):
    """Mark a specific chat message as read"""
    try:
        message = ChatMessage.objects.get(
            id=message_id,
            recipient=request.user
        )
        message.is_read = True
        message.save()
        
        return JsonResponse({'success': True})
    except ChatMessage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Message not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def create_notification(user, notification_type, title, message, related_study=None):
    """Helper function to create notifications"""
    if user:  # Only create notification if user is specified
        Notification.objects.create(
            recipient=user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_study=related_study
        )


def create_system_upload_message(study, user):
    """Create a system upload message when a study is uploaded"""
    # Create system upload message for all radiologists
    from django.contrib.auth.models import User
    radiologists = User.objects.filter(groups__name='radiologist')
    
    message_text = f'New study uploaded: {study.patient_name} - {study.study_description or study.modality}'
    
    # Create a chat message for each radiologist
    for radiologist in radiologists:
        ChatMessage.objects.create(
            sender=user,
            recipient=radiologist,
            facility=getattr(study, 'facility', None),
            message_type='system_upload',
            message=message_text,
            related_study=study
        )
    
    # Also create a general system message if no specific radiologists
    if not radiologists.exists():
        ChatMessage.objects.create(
            sender=user,
            message_type='system_upload',
            message=message_text,
            related_study=study,
            facility=getattr(study, 'facility', None)
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