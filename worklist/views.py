from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from datetime import datetime, date
import json

from .models import WorklistEntry, DicomSCPServer, StudyAssignment
from viewer.models import DicomStudy, Facility, UserProfile, Notification
from viewer.serializers import DicomStudySerializer


class WorklistView(TemplateView):
    """Main worklist page"""
    template_name = 'worklist/worklist.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user's facility if available
        user_facility = None
        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            user_facility = self.request.user.profile.facility
            context['user_facility'] = user_facility
            context['user_role'] = self.request.user.profile.role
        
        return context


class FacilityDashboardView(TemplateView):
    """Facility-specific dashboard"""
    template_name = 'facility/dashboard.html'
    
    @login_required
    def dispatch(self, request, *args, **kwargs):
        # Ensure user has facility role
        if not (hasattr(request.user, 'profile') and 
                request.user.profile.role == 'facility'):
            return redirect('viewer:viewer')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['facility'] = self.request.user.profile.facility
        return context


class RadiologistDashboardView(TemplateView):
    """Radiologist dashboard with notifications"""
    template_name = 'radiologist/dashboard.html'
    
    @login_required
    def dispatch(self, request, *args, **kwargs):
        # Ensure user has radiologist or admin role
        if not (hasattr(request.user, 'profile') and 
                request.user.profile.role in ['radiologist', 'admin']):
            return redirect('viewer:viewer')
        return super().dispatch(request, *args, **kwargs)


@api_view(['GET'])
def get_worklist(request):
    """Get patient worklist with filtering"""
    user = request.user
    worklist_entries = WorklistEntry.objects.all()
    
    # Apply facility filtering based on user role
    if user.is_authenticated and hasattr(user, 'profile'):
        profile = user.profile
        if profile.role == 'facility':
            # Facility users only see their own facility's entries
            worklist_entries = worklist_entries.filter(facility=profile.facility)
        elif profile.role == 'radiologist':
            # Radiologists see all entries or assigned ones
            pass  # No filtering for now
        # Admins see all entries
    
    # Apply filters from request
    status_filter = request.GET.get('status')
    if status_filter:
        worklist_entries = worklist_entries.filter(status=status_filter)
    
    priority_filter = request.GET.get('priority')
    if priority_filter:
        worklist_entries = worklist_entries.filter(priority=priority_filter)
    
    date_filter = request.GET.get('date')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            worklist_entries = worklist_entries.filter(study_date=filter_date)
        except ValueError:
            pass
    
    search_query = request.GET.get('search')
    if search_query:
        worklist_entries = worklist_entries.filter(
            Q(patient_name__icontains=search_query) |
            Q(patient_id__icontains=search_query) |
            Q(accession_number__icontains=search_query)
        )
    
    # Serialize the data
    worklist_data = []
    for entry in worklist_entries:
        worklist_data.append({
            'id': entry.id,
            'patient_id': entry.patient_id,
            'patient_name': entry.patient_name,
            'patient_dob': entry.patient_dob.strftime('%Y-%m-%d') if entry.patient_dob else '',
            'patient_sex': entry.patient_sex,
            'study_date': entry.study_date.strftime('%Y-%m-%d'),
            'study_time': entry.study_time.strftime('%H:%M') if entry.study_time else '',
            'modality': entry.modality,
            'study_description': entry.study_description,
            'body_part': entry.body_part,
            'referring_physician': entry.referring_physician,
            'priority': entry.priority,
            'status': entry.status,
            'has_images': entry.has_images,
            'accession_number': entry.accession_number,
            'institution_name': entry.institution_name,
            'facility_name': entry.facility.name if entry.facility else '',
            'created_at': entry.created_at.isoformat(),
        })
    
    return Response(worklist_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_worklist_entry(request):
    """Create a new worklist entry"""
    try:
        data = request.data
        
        # Get user's facility
        user_facility = None
        if hasattr(request.user, 'profile'):
            user_facility = request.user.profile.facility
        
        # Generate study instance UID if not provided
        study_uid = data.get('study_instance_uid')
        if not study_uid:
            study_uid = f"1.2.826.0.1.3680043.8.498.{int(datetime.now().timestamp() * 1000000)}"
        
        entry = WorklistEntry.objects.create(
            patient_id=data.get('patient_id', ''),
            patient_name=data.get('patient_name', ''),
            patient_dob=datetime.strptime(data['patient_dob'], '%Y-%m-%d').date() if data.get('patient_dob') else None,
            patient_sex=data.get('patient_sex', ''),
            study_instance_uid=study_uid,
            accession_number=data.get('accession_number', ''),
            study_date=datetime.strptime(data['study_date'], '%Y-%m-%d').date(),
            study_time=datetime.strptime(data['study_time'], '%H:%M').time() if data.get('study_time') else None,
            modality=data.get('modality', ''),
            study_description=data.get('study_description', ''),
            body_part=data.get('body_part', ''),
            referring_physician=data.get('referring_physician', ''),
            institution_name=data.get('institution_name', ''),
            facility=user_facility,
            priority=data.get('priority', 'normal'),
            created_by=request.user
        )
        
        return Response({
            'success': True,
            'entry_id': entry.id,
            'message': 'Worklist entry created successfully'
        }, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
def launch_viewer(request, entry_id):
    """Launch DICOM viewer for a worklist entry"""
    entry = get_object_or_404(WorklistEntry, id=entry_id)
    
    # Check permissions
    if not can_access_worklist_entry(request.user, entry):
        return Response({'error': 'Access denied'}, status=403)
    
    if entry.dicom_study:
        # Redirect to viewer with study ID
        return Response({
            'success': True,
            'viewer_url': f'/viewer/?study_id={entry.dicom_study.id}',
            'study_id': entry.dicom_study.id
        })
    else:
        return Response({
            'error': 'No DICOM images available for this entry'
        }, status=404)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_clinical_info(request, entry_id):
    """Update clinical information for a worklist entry"""
    entry = get_object_or_404(WorklistEntry, id=entry_id)
    
    # Check permissions
    if not can_access_worklist_entry(request.user, entry):
        return Response({'error': 'Access denied'}, status=403)
    
    data = request.data
    
    # Update the worklist entry
    if 'referring_physician' in data:
        entry.referring_physician = data['referring_physician']
    if 'study_description' in data:
        entry.study_description = data['study_description']
    if 'body_part' in data:
        entry.body_part = data['body_part']
    
    entry.save()
    
    # Also update the linked DICOM study if it exists
    if entry.dicom_study:
        study = entry.dicom_study
        if 'clinical_history' in data:
            study.clinical_history = data['clinical_history']
        if 'indication' in data:
            study.indication = data['indication']
        study.save()
    
    return Response({'success': True, 'message': 'Clinical information updated'})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_reports(request, entry_id=None):
    """Manage reports for worklist entries"""
    if request.method == 'GET':
        if entry_id:
            entry = get_object_or_404(WorklistEntry, id=entry_id)
            if not can_access_worklist_entry(request.user, entry):
                return Response({'error': 'Access denied'}, status=403)
            
            if entry.dicom_study:
                reports = entry.dicom_study.reports.all()
                from viewer.serializers import ReportSerializer
                serializer = ReportSerializer(reports, many=True)
                return Response(serializer.data)
            else:
                return Response([])
        else:
            # Get all reports for user's facility
            from viewer.models import Report
            reports = Report.objects.all()
            if hasattr(request.user, 'profile') and request.user.profile.role == 'facility':
                reports = reports.filter(study__facility=request.user.profile.facility)
            
            from viewer.serializers import ReportSerializer
            serializer = ReportSerializer(reports, many=True)
            return Response(serializer.data)
    
    elif request.method == 'POST':
        entry = get_object_or_404(WorklistEntry, id=entry_id)
        
        # Check if user can create reports (radiologist or admin)
        if not (hasattr(request.user, 'profile') and 
                request.user.profile.role in ['radiologist', 'admin']):
            return Response({'error': 'Permission denied'}, status=403)
        
        if not entry.dicom_study:
            return Response({'error': 'No DICOM study linked to this entry'}, status=400)
        
        data = request.data
        from viewer.models import Report
        report = Report.objects.create(
            study=entry.dicom_study,
            report_text=data.get('report_text', ''),
            impression=data.get('impression', ''),
            status=data.get('status', 'draft'),
            created_by=request.user
        )
        
        from viewer.serializers import ReportSerializer
        serializer = ReportSerializer(report)
        return Response(serializer.data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def print_report(request, report_id):
    """Generate printable report with facility letterhead"""
    from viewer.models import Report
    report = get_object_or_404(Report, id=report_id)
    
    # Check permissions
    if not can_access_study(request.user, report.study):
        return Response({'error': 'Access denied'}, status=403)
    
    # Get facility for letterhead
    facility = report.study.facility
    
    # Generate print-ready HTML
    from django.template.loader import render_to_string
    html_content = render_to_string('reports/print_report.html', {
        'report': report,
        'facility': facility,
        'study': report.study
    })
    
    return HttpResponse(html_content, content_type='text/html')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """Get notifications for radiologists and admins"""
    if not (hasattr(request.user, 'profile') and 
            request.user.profile.role in ['radiologist', 'admin']):
        return Response([])
    
    notifications = request.user.notifications.filter(is_read=False).order_by('-created_at')[:20]
    from viewer.serializers import NotificationSerializer
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    from viewer.models import Notification
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_facilities(request):
    """Get list of facilities for admin/radiologist view"""
    if not (hasattr(request.user, 'profile') and 
            request.user.profile.role in ['radiologist', 'admin']):
        return Response({'error': 'Access denied'}, status=403)
    
    facilities = Facility.objects.all()
    from viewer.serializers import FacilitySerializer
    serializer = FacilitySerializer(facilities, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_facility_studies(request, facility_id):
    """Get studies for a specific facility"""
    if not (hasattr(request.user, 'profile') and 
            request.user.profile.role in ['radiologist', 'admin']):
        return Response({'error': 'Access denied'}, status=403)
    
    facility = get_object_or_404(Facility, id=facility_id)
    studies = DicomStudy.objects.filter(facility=facility)
    
    serializer = DicomStudySerializer(studies, many=True)
    return Response(serializer.data)


# Helper functions
def can_access_worklist_entry(user, entry):
    """Check if user can access a worklist entry"""
    if not user.is_authenticated:
        return False
    
    if not hasattr(user, 'profile'):
        return True  # Admin users without profile
    
    profile = user.profile
    if profile.role in ['radiologist', 'admin']:
        return True
    elif profile.role == 'facility':
        return entry.facility == profile.facility
    
    return False


def can_access_study(user, study):
    """Check if user can access a study"""
    if not user.is_authenticated:
        return False
    
    if not hasattr(user, 'profile'):
        return True  # Admin users without profile
    
    profile = user.profile
    if profile.role in ['radiologist', 'admin']:
        return True
    elif profile.role == 'facility':
        return study.facility == profile.facility
    
    return False


# DICOM SCP Server functions (placeholder for future implementation)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_scp_servers(request):
    """Get configured DICOM SCP servers"""
    servers = DicomSCPServer.objects.filter(is_active=True)
    
    # Filter by facility if user is facility role
    if hasattr(request.user, 'profile') and request.user.profile.role == 'facility':
        servers = servers.filter(facility=request.user.profile.facility)
    
    server_data = []
    for server in servers:
        server_data.append({
            'id': server.id,
            'name': server.name,
            'ae_title': server.ae_title,
            'port': server.port,
            'host': server.host,
            'is_active': server.is_active,
            'facility_name': server.facility.name if server.facility else 'All Facilities'
        })
    
    return Response(server_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def configure_scp_server(request):
    """Configure a new DICOM SCP server"""
    if not (hasattr(request.user, 'profile') and 
            request.user.profile.role in ['admin']):
        return Response({'error': 'Permission denied'}, status=403)
    
    try:
        data = request.data
        server = DicomSCPServer.objects.create(
            name=data.get('name'),
            ae_title=data.get('ae_title', 'NOCTISVIEW'),
            port=data.get('port', 11112),
            host=data.get('host', '0.0.0.0'),
            facility_id=data.get('facility_id'),
            auto_route_to_worklist=data.get('auto_route_to_worklist', True),
            storage_path=data.get('storage_path', 'dicom_storage/')
        )
        
        return Response({
            'success': True,
            'server_id': server.id,
            'message': 'SCP server configured successfully'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)