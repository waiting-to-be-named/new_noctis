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
    Notification, DicomSeries, DicomImage
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
        # Update status to in_progress when a radiologist (or anyone with access) opens the study
        # Do not overwrite a completed study
        if entry.status != 'completed':
            entry.status = 'in_progress'
            entry.save(update_fields=['status'])

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
            
        # Track whether the report has been finalized in this request
        report_finalized = False

        if data.get('finalize'):
            report.status = 'finalized'
            report.finalized_at = timezone.now()
            report_finalized = True

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

        # ----------------------------------------------------------------------------
        # Update related WorklistEntry status
        # ----------------------------------------------------------------------------
        try:
            worklist_entry = WorklistEntry.objects.filter(study=study).first()
            if worklist_entry:
                if report_finalized:
                    # Mark as completed when the report is finalized/saved.
                    worklist_entry.status = 'completed'
                else:
                    # A draft save counts as in-progress.
                    if worklist_entry.status != 'completed':
                        worklist_entry.status = 'in_progress'
                worklist_entry.save(update_fields=['status'])
        except Exception as e:
            # Log the error but do not break the response flow
            print(f"Error updating worklist entry status: {e}")
        
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
    
    # Check permissions
    if not (request.user.is_superuser or 
            request.user.groups.filter(name='Radiologists').exists() or
            (hasattr(request.user, 'facility_staff') and 
             request.user.facility_staff.facility == study.facility)):
        return HttpResponse('Permission denied', status=403)
    
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