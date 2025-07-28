# dicom_viewer/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth import authenticate, login
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import json
import os
import pydicom
from datetime import datetime, timezone
import numpy as np
from .models import (
    DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
    Facility, UserProfile, Report, Notification, AIAnalysis, ReconstructionSettings
)
from .serializers import (
    DicomStudySerializer, DicomImageSerializer, MeasurementSerializer,
    AnnotationSerializer, FacilitySerializer, UserProfileSerializer,
    ReportSerializer, NotificationSerializer, AIAnalysisSerializer,
    ReconstructionSettingsSerializer
)


class DicomViewerView(TemplateView):
    """Main DICOM viewer page"""
    template_name = 'dicom_viewer/viewer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['studies'] = DicomStudy.objects.all()[:10]  # Recent studies
        return context


class WorklistView(TemplateView):
    """Patient worklist page"""
    template_name = 'worklist/worklist.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add worklist context
        return context


class FacilityDashboardView(TemplateView):
    """Facility-specific dashboard"""
    template_name = 'facility/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            context['facility'] = self.request.user.profile.facility
        return context


@csrf_exempt
@require_http_methods(['POST'])
def upload_dicom_files(request):
    """Handle DICOM file uploads with facility assignment"""
    if 'files' not in request.FILES:
        return JsonResponse({'error': 'No files provided'}, status=400)
    
    files = request.FILES.getlist('files')
    uploaded_files = []
    study = None
    
    # Get user's facility if available
    user_facility = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_facility = request.user.profile.facility
    
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
                        'facility': user_facility,
                        'uploaded_by': request.user if request.user.is_authenticated else None,
                    }
                )
                
                # Create notification for radiologists
                if created:
                    create_upload_notification(study, request.user)
            
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
    """Get list of DICOM studies with facility filtering"""
    user = request.user
    studies = DicomStudy.objects.all()
    
    # Apply facility filtering based on user role
    if user.is_authenticated and hasattr(user, 'profile'):
        profile = user.profile
        if profile.role == 'facility':
            # Facility users only see their own facility's studies
            studies = studies.filter(facility=profile.facility)
        elif profile.role == 'radiologist':
            # Radiologists see all studies or assigned ones
            pass  # No filtering for now
        # Admins see all studies
    
    serializer = DicomStudySerializer(studies, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_study_images(request, study_id):
    """Get all images for a study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    
    # Check permissions
    if not can_access_study(request.user, study):
        return Response({'error': 'Access denied'}, status=403)
    
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
    
    # Check permissions
    if not can_access_study(request.user, image.series.study):
        return Response({'error': 'Access denied'}, status=403)
    
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
    """Save a measurement with enhanced units support"""
    try:
        data = json.loads(request.body)
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        # Check permissions
        if not can_access_study(request.user, image.series.study):
            return Response({'error': 'Access denied'}, status=403)
        
        # Calculate Hounsfield units if ellipse measurement
        value = data['value']
        unit = data.get('unit', 'px')
        
        if data.get('type') == 'hounsfield' or unit == 'hu':
            # Calculate HU from pixel values
            pixel_array = image.get_pixel_array()
            if pixel_array is not None and 'coordinates' in data:
                coords = data['coordinates']
                if len(coords) >= 2:  # Ellipse coordinates
                    hu_value = calculate_hounsfield_units(pixel_array, coords, image)
                    value = hu_value
                    unit = 'hu'
        
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
            'measurement_id': measurement.id,
            'value': value,
            'unit': unit
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
        
        # Check permissions
        if not can_access_study(request.user, image.series.study):
            return Response({'error': 'Access denied'}, status=403)
        
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
    
    # Check permissions
    if not can_access_study(request.user, image.series.study):
        return Response({'error': 'Access denied'}, status=403)
    
    measurements = image.measurements.all()
    serializer = MeasurementSerializer(measurements, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_annotations(request, image_id):
    """Get annotations for an image"""
    image = get_object_or_404(DicomImage, id=image_id)
    
    # Check permissions
    if not can_access_study(request.user, image.series.study):
        return Response({'error': 'Access denied'}, status=403)
    
    annotations = image.annotations.all()
    serializer = AnnotationSerializer(annotations, many=True)
    return Response(serializer.data)


@csrf_exempt
@api_view(['DELETE'])
def clear_measurements(request, image_id):
    """Clear all measurements for an image"""
    image = get_object_or_404(DicomImage, id=image_id)
    
    # Check permissions
    if not can_access_study(request.user, image.series.study):
        return Response({'error': 'Access denied'}, status=403)
    
    image.measurements.all().delete()
    image.annotations.all().delete()
    
    return JsonResponse({'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_3d_reconstruction(request, study_id):
    """Create 3D reconstruction"""
    try:
        study = get_object_or_404(DicomStudy, id=study_id)
        
        # Check permissions
        if not can_access_study(request.user, study):
            return Response({'error': 'Access denied'}, status=403)
        
        data = request.data
        reconstruction_type = data.get('type', 'mpr')
        settings = data.get('settings', {})
        
        reconstruction = ReconstructionSettings.objects.create(
            study=study,
            reconstruction_type=reconstruction_type,
            settings=settings,
            created_by=request.user
        )
        
        # TODO: Implement actual 3D reconstruction logic
        # For now, just return the reconstruction object
        
        serializer = ReconstructionSettingsSerializer(reconstruction)
        return Response(serializer.data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_ai_analysis(request, image_id):
    """Trigger AI analysis for an image"""
    try:
        image = get_object_or_404(DicomImage, id=image_id)
        
        # Check permissions
        if not can_access_study(request.user, image.series.study):
            return Response({'error': 'Access denied'}, status=403)
        
        analysis_type = request.data.get('type', 'anomaly_detection')
        
        # Create AI analysis record
        ai_analysis = AIAnalysis.objects.create(
            image=image,
            analysis_type=analysis_type,
            status='pending'
        )
        
        # TODO: Implement actual AI analysis
        # For now, simulate analysis with dummy data
        dummy_results = {
            'findings': ['Possible abnormality detected'],
            'confidence': 0.85,
            'regions': [{'x': 100, 'y': 100, 'width': 50, 'height': 50}]
        }
        
        ai_analysis.results = dummy_results
        ai_analysis.confidence_score = 0.85
        ai_analysis.highlighted_regions = dummy_results['regions']
        ai_analysis.status = 'completed'
        ai_analysis.completed_at = datetime.now(timezone.utc)
        ai_analysis.save()
        
        serializer = AIAnalysisSerializer(ai_analysis)
        return Response(serializer.data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_reports(request, study_id=None):
    """Get or create reports"""
    if request.method == 'GET':
        if study_id:
            study = get_object_or_404(DicomStudy, id=study_id)
            if not can_access_study(request.user, study):
                return Response({'error': 'Access denied'}, status=403)
            reports = study.reports.all()
        else:
            # Get reports for user's facility
            reports = Report.objects.all()
            if hasattr(request.user, 'profile') and request.user.profile.role == 'facility':
                reports = reports.filter(study__facility=request.user.profile.facility)
        
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        study = get_object_or_404(DicomStudy, id=study_id)
        
        # Check if user can create reports (radiologist or admin)
        if not (hasattr(request.user, 'profile') and 
                request.user.profile.role in ['radiologist', 'admin']):
            return Response({'error': 'Permission denied'}, status=403)
        
        data = request.data
        report = Report.objects.create(
            study=study,
            report_text=data.get('report_text', ''),
            impression=data.get('impression', ''),
            status=data.get('status', 'draft'),
            created_by=request.user
        )
        
        serializer = ReportSerializer(report)
        return Response(serializer.data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """Get notifications for the user"""
    notifications = request.user.notifications.filter(is_read=False)
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return Response({'success': True})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_clinical_info(request, study_id):
    """Update clinical information for a study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    
    # Check permissions
    if not can_access_study(request.user, study):
        return Response({'error': 'Access denied'}, status=403)
    
    data = request.data
    study.clinical_history = data.get('clinical_history', study.clinical_history)
    study.indication = data.get('indication', study.indication)
    study.save()
    
    serializer = DicomStudySerializer(study)
    return Response(serializer.data)


# Helper functions
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


def create_upload_notification(study, uploader):
    """Create notification for new upload"""
    # Get radiologists and admins
    radiologist_profiles = UserProfile.objects.filter(role__in=['radiologist', 'admin'])
    
    for profile in radiologist_profiles:
        Notification.objects.create(
            recipient=profile.user,
            notification_type='new_upload',
            title=f'New Study Uploaded: {study.patient_name}',
            message=f'A new {study.modality} study has been uploaded for {study.patient_name}',
            study=study
        )


def calculate_hounsfield_units(pixel_array, coordinates, image):
    """Calculate Hounsfield Units from pixel values in ellipse region"""
    try:
        # Load DICOM data to get rescale parameters
        dicom_data = image.load_dicom_data()
        if not dicom_data:
            return 0
        
        # Get rescale parameters
        rescale_intercept = getattr(dicom_data, 'RescaleIntercept', 0)
        rescale_slope = getattr(dicom_data, 'RescaleSlope', 1)
        
        # Extract ellipse region (simplified - just use bounding box for now)
        if len(coordinates) >= 2:
            x1, y1 = int(coordinates[0]['x']), int(coordinates[0]['y'])
            x2, y2 = int(coordinates[1]['x']), int(coordinates[1]['y'])
            
            # Get ROI
            roi = pixel_array[min(y1, y2):max(y1, y2), min(x1, x2):max(x1, x2)]
            
            if roi.size > 0:
                # Calculate mean pixel value
                mean_pixel_value = np.mean(roi)
                
                # Convert to Hounsfield Units
                hu_value = mean_pixel_value * rescale_slope + rescale_intercept
                return float(hu_value)
        
        return 0
    except Exception as e:
        print(f"Error calculating HU: {e}")
        return 0