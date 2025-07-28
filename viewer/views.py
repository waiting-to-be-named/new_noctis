# dicom_viewer/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
import json
import os
import pydicom
from datetime import datetime
import numpy as np
from .models import (
    DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
    Facility, WorklistPatient, ClinicalInformation, Report, Notification
)
from .serializers import DicomStudySerializer, DicomImageSerializer


class HomeView(TemplateView):
    """Landing page with button to launch viewer"""
    template_name = 'dicom_viewer/home.html'


class WorklistView(ListView):
    """DICOM Worklist view"""
    model = WorklistPatient
    template_name = 'dicom_viewer/worklist.html'
    context_object_name = 'patients'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by facility for non-admin/radiologist users
        if self.request.user.is_authenticated:
            if not (self.request.user.is_staff or self.request.user.groups.filter(name='Radiologists').exists()):
                # Get user's facility
                user_facility = getattr(self.request.user, 'facility', None)
                if user_facility:
                    queryset = queryset.filter(facility=user_facility)
        
        return queryset.select_related('facility')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['facilities'] = Facility.objects.all()
        return context


class FacilityView(ListView):
    """Facility-specific patient view"""
    model = DicomStudy
    template_name = 'dicom_viewer/facility_view.html'
    context_object_name = 'studies'
    
    def get_queryset(self):
        facility_id = self.kwargs.get('facility_id')
        facility = get_object_or_404(Facility, id=facility_id)
        return DicomStudy.objects.filter(facility=facility).select_related('report')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['facility'] = get_object_or_404(Facility, id=self.kwargs.get('facility_id'))
        return context


class DicomViewerView(TemplateView):
    """Main DICOM viewer page"""
    template_name = 'dicom_viewer/viewer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['studies'] = DicomStudy.objects.all()[:10]  # Recent studies
        context['study_id'] = self.request.GET.get('study_id')
        return context


@login_required
@api_view(['POST'])
def create_clinical_info(request, study_id):
    """Create or update clinical information"""
    study = get_object_or_404(DicomStudy, id=study_id)
    
    clinical_info, created = ClinicalInformation.objects.get_or_create(
        study=study,
        defaults={'created_by': request.user}
    )
    
    # Update fields
    clinical_info.chief_complaint = request.data.get('chief_complaint', '')
    clinical_info.clinical_history = request.data.get('clinical_history', '')
    clinical_info.indication = request.data.get('indication', '')
    clinical_info.allergies = request.data.get('allergies', '')
    clinical_info.medications = request.data.get('medications', '')
    clinical_info.save()
    
    return Response({'success': True, 'created': created})


@login_required
@api_view(['POST'])
def create_report(request, study_id):
    """Create or update radiological report"""
    study = get_object_or_404(DicomStudy, id=study_id)
    
    # Check if user is radiologist or admin
    if not (request.user.is_staff or request.user.groups.filter(name='Radiologists').exists()):
        return Response({'error': 'Unauthorized'}, status=403)
    
    report, created = Report.objects.get_or_create(
        study=study,
        defaults={'created_by': request.user}
    )
    
    # Update fields
    report.findings = request.data.get('findings', '')
    report.impression = request.data.get('impression', '')
    report.recommendations = request.data.get('recommendations', '')
    report.status = request.data.get('status', 'draft')
    
    if request.data.get('sign', False) and report.status == 'final':
        report.signed_by = request.user
        report.signed_at = timezone.now()
    
    report.save()
    
    # Create notification for facility
    if report.status == 'final' and study.facility:
        Notification.objects.create(
            user=study.uploaded_by or request.user,
            notification_type='report_ready',
            title=f'Report Ready: {study.patient_name}',
            message=f'The radiological report for {study.patient_name} is now available.',
            study=study,
            facility=study.facility
        )
    
    return Response({'success': True, 'created': created, 'report_id': report.id})


@api_view(['GET'])
def get_report(request, study_id):
    """Get report for a study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    
    try:
        report = study.report
        return Response({
            'findings': report.findings,
            'impression': report.impression,
            'recommendations': report.recommendations,
            'status': report.status,
            'created_by': report.created_by.get_full_name() or report.created_by.username,
            'created_at': report.created_at,
            'signed_by': report.signed_by.get_full_name() if report.signed_by else None,
            'signed_at': report.signed_at
        })
    except Report.DoesNotExist:
        return Response({'error': 'No report found'}, status=404)


@login_required
@api_view(['GET'])
def get_notifications(request):
    """Get unread notifications for current user"""
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).select_related('study', 'facility')[:10]
    
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'type': notif.notification_type,
            'title': notif.title,
            'message': notif.message,
            'study_id': notif.study.id if notif.study else None,
            'facility_name': notif.facility.name if notif.facility else None,
            'created_at': notif.created_at
        })
    
    return Response(data)


@login_required
@api_view(['POST'])
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return Response({'success': True})


@api_view(['POST'])
def launch_viewer_from_worklist(request, patient_id):
    """Launch viewer with patient's studies from worklist"""
    patient = get_object_or_404(WorklistPatient, id=patient_id)
    patient.is_viewed = True
    patient.save()
    
    # Find associated studies
    studies = DicomStudy.objects.filter(
        patient_id=patient.patient_id,
        study_date=patient.study_date
    )
    
    if studies.exists():
        return Response({
            'success': True,
            'study_id': studies.first().id,
            'redirect_url': f'/viewer/?study_id={studies.first().id}'
        })
    else:
        return Response({'error': 'No studies found for this patient'}, status=404)


@csrf_exempt
@require_http_methods(['POST'])
def upload_dicom_files(request):
    """Handle DICOM file uploads"""
    if 'files' not in request.FILES:
        return JsonResponse({'error': 'No files provided'}, status=400)
    
    files = request.FILES.getlist('files')
    uploaded_files = []
    study = None
    
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
                    }
                )
            
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
        data = request.data if hasattr(request, 'data') else json.loads(request.body)
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        measurement_type = data.get('type', 'line')
        coordinates = data['coordinates']
        value = data['value']
        unit = data.get('unit', 'px')
        
        # Create measurement
        measurement = Measurement.objects.create(
            image=image,
            measurement_type=measurement_type,
            coordinates=coordinates,
            value=value,
            unit=unit,
            notes=data.get('notes', ''),
            created_by=request.user if request.user.is_authenticated else None,
        )
        
        # For ellipse measurements, calculate Hounsfield stats
        if measurement_type == 'ellipse' and unit == 'HU':
            stats = image.get_hounsfield_stats_ellipse(
                coordinates['center_x'],
                coordinates['center_y'],
                coordinates['radius_x'],
                coordinates['radius_y']
            )
            if stats:
                measurement.mean_hu = stats['mean']
                measurement.std_hu = stats['std']
                measurement.min_hu = stats['min']
                measurement.max_hu = stats['max']
                measurement.value = stats['area']
                measurement.save()
        
        return JsonResponse({
            'success': True,
            'measurement_id': measurement.id,
            'stats': {
                'mean_hu': measurement.mean_hu,
                'std_hu': measurement.std_hu,
                'min_hu': measurement.min_hu,
                'max_hu': measurement.max_hu
            } if measurement.mean_hu else None
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_view(['POST'])
def save_annotation(request):
    """Save an annotation"""
    try:
        data = request.data if hasattr(request, 'data') else json.loads(request.body)
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        annotation = Annotation.objects.create(
            image=image,
            x_coordinate=data['x'],
            y_coordinate=data['y'],
            text=data['text'],
            font_size=data.get('font_size', 14),
            color=data.get('color', '#FFFF00'),
            is_draggable=data.get('is_draggable', True),
            created_by=request.user if request.user.is_authenticated else None,
        )
        
        return JsonResponse({
            'success': True,
            'annotation_id': annotation.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['POST'])
def update_annotation_position(request, annotation_id):
    """Update annotation position after dragging"""
    annotation = get_object_or_404(Annotation, id=annotation_id)
    
    annotation.x_coordinate = request.data.get('x', annotation.x_coordinate)
    annotation.y_coordinate = request.data.get('y', annotation.y_coordinate)
    annotation.save()
    
    return Response({'success': True})


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
    image = get_object_or_404(DicomImage, id=image_id)
    annotations = image.annotations.all()
    
    annotation_data = []
    for annotation in annotations:
        annotation_data.append({
            'id': annotation.id,
            'x': annotation.x_coordinate,
            'y': annotation.y_coordinate,
            'text': annotation.text,
        })
    
    return Response(annotation_data)


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