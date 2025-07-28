# dicom_viewer/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
import os
import pydicom
from datetime import datetime
import numpy as np
from .models import DicomStudy, DicomSeries, DicomImage, Measurement, Annotation, Report, Notification, Facility, UserProfile
from .serializers import DicomStudySerializer, DicomImageSerializer
from django.db.models import Q
from django.core.paginator import Paginator
from django.template.response import TemplateResponse


class IndexView(TemplateView):
    """Landing page"""
    template_name = 'dicom_viewer/index.html'


class DicomViewerView(TemplateView):
    """Main DICOM viewer page"""
    template_name = 'dicom_viewer/viewer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['studies'] = DicomStudy.objects.all()[:10]  # Recent studies
        return context


class WorklistView(TemplateView):
    """DICOM Worklist page"""
    template_name = 'dicom_viewer/worklist.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user profile info
        if self.request.user.is_authenticated:
            try:
                context['user_profile'] = self.request.user.profile
            except:
                pass
        return context


@api_view(['GET'])
def worklist_studies(request):
    """API endpoint for worklist studies with filtering"""
    # Get filter parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    modality = request.GET.get('modality')
    status = request.GET.get('status')
    urgency = request.GET.get('urgency')
    page = int(request.GET.get('page', 1))
    per_page = 20
    
    # Base query
    studies = DicomStudy.objects.all()
    
    # Apply user facility filter
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_profile = request.user.profile
        if user_profile.role not in ['radiologist', 'admin']:
            # Non-radiologists/admins can only see their facility's studies
            if user_profile.facility:
                studies = studies.filter(facility=user_profile.facility)
    
    # Apply filters
    if date_from:
        studies = studies.filter(study_date__gte=date_from)
    if date_to:
        studies = studies.filter(study_date__lte=date_to)
    if modality:
        studies = studies.filter(modality=modality)
    if status:
        studies = studies.filter(report_status=status)
    if urgency:
        studies = studies.filter(urgency=urgency)
    
    # Order by urgency and date
    studies = studies.order_by('-urgency', '-study_date', '-created_at')
    
    # Paginate
    paginator = Paginator(studies, per_page)
    page_obj = paginator.get_page(page)
    
    # Serialize studies
    studies_data = []
    for study in page_obj:
        study_dict = {
            'id': study.id,
            'patient_name': study.patient_name,
            'patient_id': study.patient_id,
            'study_date': study.study_date,
            'modality': study.modality,
            'study_description': study.study_description,
            'urgency': study.urgency,
            'report_status': study.report_status,
            'facility_name': study.facility.name if study.facility else None,
            'clinical_history': study.clinical_history,
            'indication': study.indication,
            'referring_physician': study.referring_physician,
        }
        
        # Add facility logo URL if exists
        if study.facility and study.facility.letterhead_logo:
            study_dict['facility_logo'] = study.facility.letterhead_logo.url
            study_dict['facility_address'] = study.facility.address
        
        studies_data.append(study_dict)
    
    return Response({
        'studies': studies_data,
        'total_pages': paginator.num_pages,
        'current_page': page,
        'total_count': paginator.count
    })


@api_view(['POST'])
@login_required
def save_clinical_info(request):
    """Save clinical information for a study"""
    study_id = request.POST.get('study_id')
    
    try:
        study = DicomStudy.objects.get(id=study_id)
        
        # Update clinical information
        study.clinical_history = request.POST.get('clinical_history', '')
        study.indication = request.POST.get('indication', '')
        study.referring_physician = request.POST.get('referring_physician', '')
        study.urgency = request.POST.get('urgency', 'routine')
        study.save()
        
        # Create notification if urgency is high
        if study.urgency in ['urgent', 'stat']:
            # Notify radiologists
            radiologists = UserProfile.objects.filter(role='radiologist')
            for radiologist in radiologists:
                Notification.objects.create(
                    recipient=radiologist,
                    notification_type='urgent_study',
                    title=f'Urgent {study.modality} Study',
                    message=f'New {study.urgency.upper()} study for {study.patient_name}',
                    study=study
                )
        
        return Response({'success': True})
    except DicomStudy.DoesNotExist:
        return Response({'error': 'Study not found'}, status=404)


@api_view(['GET', 'POST'])
@login_required
def manage_report(request, study_id=None):
    """Get or save radiology report"""
    if request.method == 'GET' and study_id:
        try:
            study = DicomStudy.objects.get(id=study_id)
            report = study.reports.filter(status__in=['draft', 'finalized']).first()
            
            if report:
                return Response({
                    'findings': report.findings,
                    'impression': report.impression,
                    'recommendations': report.recommendations,
                    'status': report.status
                })
            else:
                return Response({})
        except DicomStudy.DoesNotExist:
            return Response({'error': 'Study not found'}, status=404)
    
    elif request.method == 'POST':
        study_id = request.POST.get('study_id')
        status = request.POST.get('status', 'draft')
        
        try:
            study = DicomStudy.objects.get(id=study_id)
            
            # Check permissions
            if not hasattr(request.user, 'profile') or request.user.profile.role not in ['radiologist', 'admin']:
                return Response({'error': 'Unauthorized'}, status=403)
            
            # Get or create report
            report = study.reports.filter(radiologist=request.user, status='draft').first()
            if not report:
                report = Report.objects.create(
                    study=study,
                    radiologist=request.user
                )
            
            # Update report content
            report.findings = request.POST.get('findings', '')
            report.impression = request.POST.get('impression', '')
            report.recommendations = request.POST.get('recommendations', '')
            
            if status == 'finalized':
                report.finalize()
                
                # Update study status
                study.report_status = 'completed'
                study.save()
                
                # Create notification
                if study.uploaded_by:
                    Notification.objects.create(
                        recipient=study.uploaded_by,
                        notification_type='report_completed',
                        title='Report Completed',
                        message=f'Report for {study.patient_name} has been completed',
                        study=study
                    )
            else:
                report.status = status
                report.save()
            
            return Response({'success': True})
            
        except DicomStudy.DoesNotExist:
            return Response({'error': 'Study not found'}, status=404)


@api_view(['GET'])
def get_notifications(request):
    """Get user notifications"""
    if not request.user.is_authenticated:
        return Response([])
    
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:20]
    
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'notification_type': notif.notification_type,
            'title': notif.title,
            'message': notif.message,
            'is_read': notif.is_read,
            'created_at': notif.created_at,
            'study_id': notif.study.id if notif.study else None
        })
    
    return Response(data)


@api_view(['GET'])
def get_unread_notifications(request):
    """Get count of unread notifications"""
    if not request.user.is_authenticated:
        return Response({'count': 0, 'notifications': []})
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:5]
    
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'notification_type': notif.notification_type,
            'title': notif.title,
            'message': notif.message,
            'created_at': notif.created_at,
            'study_id': notif.study.id if notif.study else None
        })
    
    return Response({
        'count': notifications.count(),
        'notifications': data
    })


@api_view(['POST'])
@login_required
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.is_read = True
        notification.save()
        return Response({'success': True})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=404)


def print_report(request, study_id):
    """Print-friendly report view"""
    try:
        study = DicomStudy.objects.get(id=study_id)
        report = study.reports.filter(status__in=['finalized', 'verified']).first()
        
        if not report:
            return HttpResponse('No finalized report found', status=404)
        
        context = {
            'study': study,
            'report': report,
            'facility': study.facility,
        }
        
        return TemplateResponse(request, 'dicom_viewer/print_report.html', context)
        
    except DicomStudy.DoesNotExist:
        return HttpResponse('Study not found', status=404)


@csrf_exempt
@require_http_methods(['POST'])
def upload_dicom_files(request):
    """Handle DICOM file uploads"""
    if 'files' not in request.FILES:
        return JsonResponse({'error': 'No files provided'}, status=400)
    
    files = request.FILES.getlist('files')
    uploaded_files = []
    study = None
    
    # Get facility from user profile if authenticated
    facility = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        facility = request.user.profile.facility
    
    for file in files:
        try:
            # Save file temporarily
            file_path = default_storage.save(f'temp/{file.name}', ContentFile(file.read()))
            full_path = default_storage.path(file_path)
            
            # Read DICOM data
            dicom_data = pydicom.dcmread(full_path)
            
            # Create or get study
            study_uid = str(dicom_data.get('StudyInstanceUID', ''))
            if not study:
                study, created = DicomStudy.objects.get_or_create(
                    study_instance_uid=study_uid,
                    defaults={
                        'patient_name': str(dicom_data.get('PatientName', 'Unknown')),
                        'patient_id': str(dicom_data.get('PatientID', '')),
                        'study_date': parse_dicom_date(dicom_data.get('StudyDate')),
                        'study_time': parse_dicom_time(dicom_data.get('StudyTime')),
                        'study_description': str(dicom_data.get('StudyDescription', '')),
                        'modality': str(dicom_data.get('Modality', '')),
                        'institution_name': str(dicom_data.get('InstitutionName', '')),
                        'uploaded_by': request.user if request.user.is_authenticated else None,
                        'facility': facility, # Assign facility
                    }
                )
            
            # Create notification for new study
            if created and study:
                # Notify radiologists about new study
                radiologists = UserProfile.objects.filter(role='radiologist')
                for radiologist in radiologists:
                    Notification.objects.create(
                        recipient=radiologist,
                        notification_type='new_study',
                        title='New Study Available',
                        message=f'New {study.modality} study for {study.patient_name}',
                        study=study
                    )
                
                # Special notification for urgent studies
                if hasattr(dicom_data, 'StudyPriority') and dicom_data.StudyPriority in ['STAT', 'URGENT']:
                    study.urgency = 'stat' if dicom_data.StudyPriority == 'STAT' else 'urgent'
                    study.save()
            
            # Create or get series
            series_uid = str(dicom_data.get('SeriesInstanceUID', ''))
            series, created = DicomSeries.objects.get_or_create(
                study=study,
                series_instance_uid=series_uid,
                defaults={
                    'series_number': int(dicom_data.get('SeriesNumber', 0)),
                    'series_description': str(dicom_data.get('SeriesDescription', '')),
                    'modality': str(dicom_data.get('Modality', '')),
                    'body_part_examined': str(dicom_data.get('BodyPartExamined', '')),
                }
            )
            
            # Create image
            sop_uid = str(dicom_data.get('SOPInstanceUID', ''))
            image, created = DicomImage.objects.get_or_create(
                series=series,
                sop_instance_uid=sop_uid,
                defaults={
                    'instance_number': int(dicom_data.get('InstanceNumber', 0)),
                    'file_path': file_path,
                }
            )
            
            # Save metadata
            image.save_dicom_metadata()
            
            uploaded_files.append({
                'filename': file.name,
                'study_uid': study_uid,
                'series_uid': series_uid,
                'image_id': image.id,
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error processing {file.name}: {str(e)}'}, status=400)
    
    return JsonResponse({
        'success': True,
        'study_id': study.id if study else None,
        'uploaded_files': uploaded_files
    })


@api_view(['GET'])
def get_studies(request):
    """Get list of DICOM studies"""
    studies = DicomStudy.objects.all()
    serializer = DicomStudySerializer(studies, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_study_images(request, study_id):
    """Get all images for a study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    images = DicomImage.objects.filter(series__study=study).order_by('series__series_number', 'instance_number')
    
    image_data = []
    for image in images:
        image_data.append({
            'id': image.id,
            'instance_number': image.instance_number,
            'series_number': image.series.series_number,
            'series_description': image.series.series_description,
            'rows': image.rows,
            'columns': image.columns,
            'pixel_spacing_x': image.pixel_spacing_x,
            'pixel_spacing_y': image.pixel_spacing_y,
            'window_width': image.window_width,
            'window_center': image.window_center,
        })
    
    return Response({
        'study': DicomStudySerializer(study).data,
        'images': image_data
    })


@api_view(['GET'])
def get_image_data(request, image_id):
    """Get processed image data"""
    image = get_object_or_404(DicomImage, id=image_id)
    
    # Get parameters from request
    window_width = request.GET.get('window_width')
    window_level = request.GET.get('window_level')  
    inverted = request.GET.get('inverted', 'false').lower() == 'true'
    
    # Convert parameters
    if window_width:
        window_width = float(window_width)
    if window_level:
        window_level = float(window_level)
    
    # Get processed image
    image_base64 = image.get_processed_image_base64(window_width, window_level, inverted)
    
    if not image_base64:
        return Response({'error': 'Could not process image'}, status=400)
    
    return Response({
        'image_data': image_base64,
        'metadata': {
            'rows': image.rows,
            'columns': image.columns,
            'pixel_spacing_x': image.pixel_spacing_x,
            'pixel_spacing_y': image.pixel_spacing_y,
            'window_width': image.window_width,
            'window_center': image.window_center,
        }
    })


@csrf_exempt
@api_view(['POST'])
def save_measurement(request):
    """Save a measurement"""
    try:
        data = json.loads(request.body)
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        measurement = Measurement.objects.create(
            image=image,
            measurement_type=data.get('type', 'line'),
            coordinates=data['coordinates'],
            value=data['value'],
            unit=data.get('unit', 'px'),
            notes=data.get('notes', ''),
            created_by=request.user if request.user.is_authenticated else None,
        )
        
        return JsonResponse({
            'success': True,
            'measurement_id': measurement.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt  
@api_view(['POST'])
def save_annotation(request):
    """Save an annotation"""
    try:
        data = json.loads(request.body)
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        annotation = Annotation.objects.create(
            image=image,
            x_coordinate=data['x'],
            y_coordinate=data['y'],
            text=data['text'],
            created_by=request.user if request.user.is_authenticated else None,
        )
        
        return JsonResponse({
            'success': True,
            'annotation_id': annotation.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def get_measurements(request, image_id):
    """Get measurements for an image"""
    image = get_object_or_404(DicomImage, id=image_id)
    measurements = image.measurements.all()
    
    measurement_data = []
    for measurement in measurements:
        measurement_data.append({
            'id': measurement.id,
            'type': measurement.measurement_type,
            'coordinates': measurement.coordinates,
            'value': measurement.value,
            'unit': measurement.unit,
            'notes': measurement.notes,
        })
    
    return Response(measurement_data)


@api_view(['GET'])
def get_annotations(request, image_id):
    """Get annotations for an image"""
    try:
        image = DicomImage.objects.get(id=image_id)
        annotations = image.annotations.all()
        
        data = []
        for annotation in annotations:
            data.append({
                'id': annotation.id,
                'x': annotation.x_coordinate,
                'y': annotation.y_coordinate,
                'text': annotation.text,
                'created_at': annotation.created_at,
            })
        
        return Response(data)
    except DicomImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=404)


@csrf_exempt
@api_view(['DELETE'])
def clear_measurements(request, image_id):
    """Clear all measurements for an image"""
    image = get_object_or_404(DicomImage, id=image_id)
    image.measurements.all().delete()
    image.annotations.all().delete()
    
    return JsonResponse({'success': True})


def parse_dicom_date(date_str):
    """Parse DICOM date string to Python date"""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), '%Y%m%d').date()
    except:
        return None


def parse_dicom_time(time_str):
    """Parse DICOM time string to Python time"""
    if not time_str:
        return None
    try:
        time_str = str(time_str).split('.')[0]  # Remove microseconds
        if len(time_str) == 6:
            return datetime.strptime(time_str, '%H%M%S').time()
        elif len(time_str) == 4:
            return datetime.strptime(time_str, '%H%M').time()
    except:
        return None

# Add aliases for API endpoints to match URL patterns
study_list = get_studies
study_images = get_study_images
image_pixel_data = get_image_data