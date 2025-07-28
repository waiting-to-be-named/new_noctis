# dicom_viewer/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
import json
import os
import pydicom
from datetime import datetime
import numpy as np
from .models import (DicomStudy, DicomSeries, DicomImage, Measurement, Annotation, 
                     Facility, UserProfile, ClinicalInformation, RadiologyReport, Notification)
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
    
    @login_required
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        # Get user profile and filter studies based on role
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            # Create default profile for users without one
            profile = UserProfile.objects.create(user=request.user)
        
        if profile.role in ['admin', 'radiologist']:
            # Admins and radiologists can see all studies
            studies = DicomStudy.objects.all()
        else:
            # Facility users can only see their facility's studies
            studies = DicomStudy.objects.filter(facility=profile.facility)
        
        context['studies'] = studies.order_by('-created_at')
        context['user_profile'] = profile
        return render(request, self.template_name, context)


class FacilityDashboardView(TemplateView):
    """Facility-specific dashboard"""
    template_name = 'dicom_viewer/facility_dashboard.html'
    
    @login_required
    def get(self, request, *args, **kwargs):
        try:
            profile = request.user.userprofile
            if not profile.facility and profile.role not in ['admin', 'radiologist']:
                return redirect('worklist')
        except UserProfile.DoesNotExist:
            return redirect('worklist')
        
        context = self.get_context_data(**kwargs)
        
        # Get studies for this facility only
        studies = DicomStudy.objects.filter(facility=profile.facility)
        context['studies'] = studies.order_by('-created_at')
        context['facility'] = profile.facility
        context['user_profile'] = profile
        
        # Get reports ready for this facility
        reports = RadiologyReport.objects.filter(
            study__facility=profile.facility,
            status='finalized'
        ).order_by('-finalized_at')[:10]
        context['recent_reports'] = reports
        
        return render(request, self.template_name, context)


@login_required
def launch_viewer(request, study_id):
    """Launch the DICOM viewer for a specific study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    
    # Check permissions
    try:
        profile = request.user.userprofile
        if profile.role not in ['admin', 'radiologist'] and study.facility != profile.facility:
            return JsonResponse({'error': 'Access denied'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=403)
    
    # Redirect to viewer with study parameter
    return redirect(f'/viewer/?study={study_id}')


@csrf_exempt
@require_http_methods(['POST'])
def upload_dicom_files(request):
    """Handle DICOM file uploads"""
    if 'files' not in request.FILES:
        return JsonResponse({'error': 'No files provided'}, status=400)
    
    files = request.FILES.getlist('files')
    uploaded_files = []
    study = None
    
    # Get user facility
    facility = None
    if request.user.is_authenticated:
        try:
            profile = request.user.userprofile
            facility = profile.facility
        except UserProfile.DoesNotExist:
            pass
    
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
                        'facility': facility,
                        'uploaded_by': request.user if request.user.is_authenticated else None,
                    }
                )
                
                # Create notification for radiologists and admins
                if created:
                    create_new_study_notifications(study)
            
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


def create_new_study_notifications(study):
    """Create notifications for new study uploads"""
    # Notify all radiologists and admins
    radiologists_admins = User.objects.filter(
        userprofile__role__in=['radiologist', 'admin']
    )
    
    for user in radiologists_admins:
        Notification.objects.create(
            user=user,
            title='New Study Uploaded',
            message=f'New study for patient {study.patient_name} ({study.modality}) has been uploaded.',
            notification_type='new_study',
            study=study
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_studies(request):
    """Get list of DICOM studies based on user permissions"""
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if profile.role in ['admin', 'radiologist']:
        studies = DicomStudy.objects.all()
    else:
        studies = DicomStudy.objects.filter(facility=profile.facility)
    
    serializer = DicomStudySerializer(studies, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])  
def get_study_images(request, study_id):
    """Get all images for a study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    
    # Check permissions
    try:
        profile = request.user.userprofile
        if profile.role not in ['admin', 'radiologist'] and study.facility != profile.facility:
            return Response({'error': 'Access denied'}, status=403)
    except UserProfile.DoesNotExist:
        return Response({'error': 'User profile not found'}, status=403)
    
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
@permission_classes([IsAuthenticated])
def save_measurement(request):
    """Save a measurement with enhanced unit support"""
    try:
        data = json.loads(request.body)
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        measurement = Measurement.objects.create(
            image=image,
            measurement_type=data.get('type', 'line'),
            coordinates=data['coordinates'],
            value=data['value'],
            unit=data.get('unit', 'mm'),
            notes=data.get('notes', ''),
            min_value=data.get('min_value'),
            max_value=data.get('max_value'), 
            std_dev=data.get('std_dev'),
            created_by=request.user,
        )
        
        return JsonResponse({
            'success': True,
            'measurement_id': measurement.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt  
@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
            created_by=request.user,
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
            'min_value': measurement.min_value,
            'max_value': measurement.max_value,
            'std_dev': measurement.std_dev,
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
@permission_classes([IsAuthenticated])
def clear_measurements(request, image_id):
    """Clear all measurements for an image"""
    image = get_object_or_404(DicomImage, id=image_id)
    image.measurements.all().delete()
    image.annotations.all().delete()
    
    return JsonResponse({'success': True})


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def measure_hu(request):
    """Calculate average Hounsfield Units inside an ellipse region with enhanced statistics"""
    try:
        data = json.loads(request.body)
        image = get_object_or_404(DicomImage, id=data['image_id'])
        x0 = float(data['x0'])
        y0 = float(data['y0'])
        x1 = float(data['x1'])
        y1 = float(data['y1'])

        dicom_data = image.load_dicom_data()
        if dicom_data is None or not hasattr(dicom_data, 'pixel_array'):
            return JsonResponse({'error': 'Unable to load DICOM pixel data'}, status=400)

        pixel_array = dicom_data.pixel_array.astype(np.float32)

        # Apply rescale slope/intercept for CT to convert to HU
        rescale_slope = float(getattr(dicom_data, 'RescaleSlope', 1))
        rescale_intercept = float(getattr(dicom_data, 'RescaleIntercept', 0))
        pixel_array = pixel_array * rescale_slope + rescale_intercept

        # Create mask for ellipse within bounding box
        rows, cols = pixel_array.shape
        x_min = int(max(min(x0, x1), 0))
        x_max = int(min(max(x0, x1), cols - 1))
        y_min = int(max(min(y0, y1), 0))
        y_max = int(min(max(y0, y1), rows - 1))

        if x_max <= x_min or y_max <= y_min:
            return JsonResponse({'error': 'Invalid ellipse bounds'}, status=400)

        # Ellipse parameters
        xc = (x_min + x_max) / 2.0
        yc = (y_min + y_max) / 2.0
        a = (x_max - x_min) / 2.0  # semi-major axis
        b = (y_max - y_min) / 2.0  # semi-minor axis

        yy, xx = np.ogrid[y_min:y_max + 1, x_min:x_max + 1]
        ellipse_mask = (((xx - xc) / a) ** 2 + ((yy - yc) / b) ** 2) <= 1.0

        region_pixels = pixel_array[y_min:y_max + 1, x_min:x_max + 1][ellipse_mask]
        if region_pixels.size == 0:
            return JsonResponse({'error': 'No pixels inside region'}, status=400)

        mean_hu = float(np.mean(region_pixels))
        min_hu = float(np.min(region_pixels))
        max_hu = float(np.max(region_pixels))
        std_hu = float(np.std(region_pixels))

        # Save measurement with enhanced statistics
        measurement = Measurement.objects.create(
            image=image,
            measurement_type='ellipse',
            coordinates={'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1},
            value=mean_hu,
            unit='HU',
            min_value=min_hu,
            max_value=max_hu,
            std_dev=std_hu,
            notes=f"Pixels: {region_pixels.size}",
            created_by=request.user,
        )

        return JsonResponse({
            'success': True,
            'measurement_id': measurement.id,
            'mean_hu': mean_hu,
            'min_hu': min_hu,
            'max_hu': max_hu,
            'std_hu': std_hu,
            'pixel_count': int(region_pixels.size),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_analysis(request):
    """AI analysis endpoint - placeholder for future implementation"""
    return JsonResponse({
        'status': 'not_implemented',
        'message': 'AI analysis feature is not implemented yet. This will include automated image analysis and reporting capabilities.'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reconstruction_3d(request):
    """3D reconstruction endpoint - placeholder for future implementation"""
    reconstruction_type = request.data.get('type', 'mpr')
    
    return JsonResponse({
        'status': 'not_implemented',
        'type': reconstruction_type,
        'message': f'3D {reconstruction_type} reconstruction feature is not implemented yet. This will include MPR, 3D bone, angio reconstruction, and virtual surgery capabilities.'
    })


@csrf_exempt
@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def save_clinical_info(request, study_id):
    """Save or update clinical information for a study"""
    try:
        study = get_object_or_404(DicomStudy, id=study_id)
        data = json.loads(request.body)
        
        clinical_info, created = ClinicalInformation.objects.get_or_create(
            study=study,
            defaults={
                'created_by': request.user
            }
        )
        
        # Update fields
        clinical_info.patient_age = data.get('patient_age', '')
        clinical_info.patient_sex = data.get('patient_sex', '')
        clinical_info.patient_weight = data.get('patient_weight')
        clinical_info.patient_height = data.get('patient_height')
        clinical_info.referring_physician = data.get('referring_physician', '')
        clinical_info.clinical_history = data.get('clinical_history', '')
        clinical_info.indication = data.get('indication', '')
        clinical_info.contrast_agent = data.get('contrast_agent', '')
        clinical_info.save()
        
        return JsonResponse({
            'success': True,
            'clinical_info_id': clinical_info.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def save_report(request, study_id):
    """Save or update radiology report"""
    try:
        study = get_object_or_404(DicomStudy, id=study_id)
        data = json.loads(request.body)
        
        # Check if user is radiologist or admin
        try:
            profile = request.user.userprofile
            if profile.role not in ['radiologist', 'admin']:
                return JsonResponse({'error': 'Only radiologists and admins can create reports'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'error': 'User profile not found'}, status=403)
        
        report, created = RadiologyReport.objects.get_or_create(
            study=study,
            defaults={
                'radiologist': request.user
            }
        )
        
        # Update fields
        report.findings = data.get('findings', '')
        report.impression = data.get('impression', '')
        report.recommendations = data.get('recommendations', '')
        report.status = data.get('status', 'draft')
        
        if report.status == 'finalized' and not report.finalized_at:
            report.finalized_at = timezone.now()
        
        report.save()
        
        return JsonResponse({
            'success': True,
            'report_id': report.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """Get user notifications"""
    notifications = request.user.notifications.filter(is_read=False)[:20]
    
    notification_data = []
    for notification in notifications:
        notification_data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'study_id': notification.study.id if notification.study else None,
            'created_at': notification.created_at.isoformat(),
        })
    
    return Response(notification_data)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


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