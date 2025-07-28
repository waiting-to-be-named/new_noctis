# dicom_viewer/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import json
import os
import pydicom
from datetime import datetime
import numpy as np
from .models import (
    DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
    UserProfile, Facility, Report, Notification, AIAnalysis, Reconstruction3D
)
from .serializers import DicomStudySerializer, DicomImageSerializer


class DicomViewerView(TemplateView):
    """Main DICOM viewer page"""
    template_name = 'dicom_viewer/viewer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['studies'] = DicomStudy.objects.all()[:10]  # Recent studies
        return context


class WorklistView(TemplateView):
    """Worklist view for managing DICOM studies"""
    template_name = 'dicom_viewer/worklist.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user profile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = None
        
        # Filter studies based on user role
        if profile and profile.role in ['radiologist', 'admin']:
            # Radiologists and admins can see all studies
            studies = DicomStudy.objects.all()
        elif profile and profile.facility:
            # Facility staff can only see their facility's studies
            studies = DicomStudy.objects.filter(facility=profile.facility)
        else:
            studies = DicomStudy.objects.none()
        
        context['studies'] = studies
        context['user_profile'] = profile
        return context


class FacilityView(TemplateView):
    """Facility-specific view"""
    template_name = 'dicom_viewer/facility.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            profile = user.profile
            if profile and profile.facility:
                context['facility'] = profile.facility
                context['studies'] = DicomStudy.objects.filter(facility=profile.facility)
            else:
                context['facility'] = None
                context['studies'] = []
        except UserProfile.DoesNotExist:
            context['facility'] = None
            context['studies'] = []
        
        return context


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
    
    # Create notification for new upload
    if study and request.user.is_authenticated:
        try:
            profile = request.user.profile
            if profile and profile.role in ['radiologist', 'admin']:
                # Notify radiologists and admins about new upload
                Notification.objects.create(
                    user=request.user,
                    notification_type='new_upload',
                    title='New DICOM Upload',
                    message=f'New DICOM files uploaded for patient {study.patient_name}',
                    related_study=study
                )
        except UserProfile.DoesNotExist:
            pass
    
    return JsonResponse({
        'success': True,
        'study_id': study.id if study else None,
        'uploaded_files': uploaded_files
    })


@api_view(['GET'])
def get_studies(request):
    """Get list of DICOM studies with role-based filtering"""
    user = request.user
    
    try:
        profile = user.profile
        if profile and profile.role in ['radiologist', 'admin']:
            studies = DicomStudy.objects.all()
        elif profile and profile.facility:
            studies = DicomStudy.objects.filter(facility=profile.facility)
        else:
            studies = DicomStudy.objects.none()
    except UserProfile.DoesNotExist:
        studies = DicomStudy.objects.none()
    
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
    """Save a measurement with enhanced unit support"""
    try:
        data = json.loads(request.body)
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        # Calculate measurement value based on unit
        value = data['value']
        unit = data.get('unit', 'px')
        
        # Convert to different units if needed
        if unit in ['mm', 'cm'] and image.pixel_spacing_x and image.pixel_spacing_y:
            avg_spacing = (image.pixel_spacing_x + image.pixel_spacing_y) / 2
            if unit == 'mm':
                value = value * avg_spacing
            elif unit == 'cm':
                value = value * avg_spacing * 10
        
        measurement = Measurement.objects.create(
            image=image,
            measurement_type=data.get('type', 'line'),
            coordinates=data['coordinates'],
            value=value,
            unit=unit,
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
    """Save an annotation with enhanced features"""
    try:
        data = json.loads(request.body)
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        annotation = Annotation.objects.create(
            image=image,
            x_coordinate=data['x'],
            y_coordinate=data['y'],
            text=data['text'],
            font_size=data.get('font_size', 12),
            is_draggable=data.get('is_draggable', True),
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
    image = get_object_or_404(DicomImage, id=image_id)
    annotations = image.annotations.all()
    
    annotation_data = []
    for annotation in annotations:
        annotation_data.append({
            'id': annotation.id,
            'x': annotation.x_coordinate,
            'y': annotation.y_coordinate,
            'text': annotation.text,
            'font_size': annotation.font_size,
            'is_draggable': annotation.is_draggable,
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


@api_view(['POST'])
def ai_analysis(request, image_id):
    """Perform AI analysis on an image"""
    image = get_object_or_404(DicomImage, id=image_id)
    
    try:
        data = json.loads(request.body)
        analysis_type = data.get('analysis_type', 'general')
        
        # Simulate AI analysis (replace with actual AI implementation)
        analysis_result = {
            'analysis_type': analysis_type,
            'confidence_score': 85.5,
            'findings': 'No significant abnormalities detected. Normal anatomical structures visible.',
            'highlighted_regions': [
                {'x': 100, 'y': 100, 'width': 50, 'height': 50, 'type': 'normal'}
            ]
        }
        
        # Save AI analysis
        ai_analysis = AIAnalysis.objects.create(
            image=image,
            analysis_type=analysis_type,
            confidence_score=analysis_result['confidence_score'],
            findings=analysis_result['findings'],
            highlighted_regions=analysis_result['highlighted_regions']
        )
        
        return Response({
            'success': True,
            'analysis': analysis_result,
            'analysis_id': ai_analysis.id
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
def create_3d_reconstruction(request, study_id):
    """Create 3D reconstruction"""
    study = get_object_or_404(DicomStudy, id=study_id)
    
    try:
        data = json.loads(request.body)
        reconstruction_type = data.get('type', 'mpr')
        settings = data.get('settings', {})
        
        # Create reconstruction record
        reconstruction = Reconstruction3D.objects.create(
            study=study,
            reconstruction_type=reconstruction_type,
            settings=settings,
            created_by=request.user
        )
        
        # Simulate 3D reconstruction (replace with actual implementation)
        result_data = {
            'reconstruction_id': reconstruction.id,
            'type': reconstruction_type,
            'status': 'completed',
            'preview_url': f'/api/reconstructions/{reconstruction.id}/preview/'
        }
        
        return Response({
            'success': True,
            'reconstruction': result_data
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
def get_notifications(request):
    """Get user notifications"""
    if not request.user.is_authenticated:
        return Response({'notifications': []})
    
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    
    notification_data = []
    for notification in notifications:
        notification_data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'created_at': notification.created_at.isoformat(),
            'related_study_id': notification.related_study.id if notification.related_study else None
        })
    
    return Response({'notifications': notification_data})


@api_view(['POST'])
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    return Response({'success': True})


@api_view(['GET', 'POST'])
def reports(request, study_id=None):
    """Handle reports for studies"""
    if request.method == 'GET':
        if study_id:
            study = get_object_or_404(DicomStudy, id=study_id)
            reports = Report.objects.filter(study=study)
            return Response(ReportSerializer(reports, many=True).data)
        else:
            reports = Report.objects.filter(created_by=request.user)
            return Response(ReportSerializer(reports, many=True).data)
    
    elif request.method == 'POST':
        study = get_object_or_404(DicomStudy, id=study_id)
        data = json.loads(request.body)
        
        report = Report.objects.create(
            study=study,
            title=data.get('title', ''),
            content=data.get('content', ''),
            findings=data.get('findings', ''),
            impression=data.get('impression', ''),
            status=data.get('status', 'draft'),
            created_by=request.user
        )
        
        return Response({
            'success': True,
            'report_id': report.id
        })


@api_view(['POST'])
def update_clinical_notes(request, study_id):
    """Update clinical notes for a study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    data = json.loads(request.body)
    
    study.clinical_notes = data.get('clinical_notes', '')
    study.save()
    
    return Response({'success': True})


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


# Simple serializer for reports
class ReportSerializer:
    def __init__(self, reports, many=False):
        self.reports = reports
        self.many = many
    
    @property
    def data(self):
        if self.many:
            return [self._serialize_report(report) for report in self.reports]
        else:
            return self._serialize_report(self.reports)
    
    def _serialize_report(self, report):
        return {
            'id': report.id,
            'title': report.title,
            'content': report.content,
            'findings': report.findings,
            'impression': report.impression,
            'status': report.status,
            'created_at': report.created_at.isoformat(),
            'updated_at': report.updated_at.isoformat(),
            'created_by': report.created_by.username
        }