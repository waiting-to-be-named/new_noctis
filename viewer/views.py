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
from django.contrib.auth.models import User
from django.db.models import Q
import json
import os
import pydicom
from datetime import datetime
import numpy as np
from .models import (
    DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
    Facility, UserProfile, RadiologyReport, Notification
)
from .serializers import DicomStudySerializer, DicomImageSerializer


class DicomViewerView(TemplateView):
    """Main DICOM viewer page"""
    template_name = 'dicom_viewer/viewer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['studies'] = DicomStudy.objects.all()[:10]  # Recent studies
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
                # Determine facility from user or institution
                facility = None
                if request.user.is_authenticated:
                    try:
                        user_profile = UserProfile.objects.get(user=request.user)
                        facility = user_profile.facility
                    except UserProfile.DoesNotExist:
                        pass
                
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
        Notification.objects.create(
            notification_type='new_upload',
            title='New DICOM Upload',
            message=f'New study uploaded: {study.patient_name}',
        )
    
    return JsonResponse({
        'success': True,
        'uploaded_files': uploaded_files,
        'study_id': study.id if study else None
    })


@api_view(['GET'])
def get_studies(request):
    """Get list of studies"""
    studies = DicomStudy.objects.all()[:50]  # Limit to recent studies
    serializer = DicomStudySerializer(studies, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_study_images(request, study_id):
    """Get images for a specific study"""
    try:
        study = DicomStudy.objects.get(id=study_id)
        images = []
        
        for series in study.series.all():
            for image in series.images.all():
                images.append(image.id)
        
        return Response({
            'study': {
                'id': study.id,
                'patient_name': study.patient_name,
                'patient_id': study.patient_id,
                'study_date': study.study_date.isoformat() if study.study_date else None,
                'modality': study.modality,
                'status': study.status,
                'facility': study.facility.name if study.facility else None,
            },
            'images': images
        })
    except DicomStudy.DoesNotExist:
        return Response({'error': 'Study not found'}, status=404)


@api_view(['GET'])
def get_image_data(request, image_id):
    """Get processed image data"""
    try:
        image = DicomImage.objects.get(id=image_id)
        
        # Get window/level parameters from request
        window_width = request.GET.get('window_width', None)
        window_level = request.GET.get('window_level', None)
        inverted = request.GET.get('inverted', 'false').lower() == 'true'
        
        if window_width:
            window_width = float(window_width)
        if window_level:
            window_level = float(window_level)
        
        # Get processed image
        image_data = image.get_processed_image_base64(window_width, window_level, inverted)
        
        return Response({
            'id': image.id,
            'image_data': image_data,
            'metadata': {
                'rows': image.rows,
                'columns': image.columns,
                'pixel_spacing_x': image.pixel_spacing_x,
                'pixel_spacing_y': image.pixel_spacing_y,
                'slice_thickness': image.slice_thickness,
                'window_width': image.window_width,
                'window_center': image.window_center,
                'rescale_intercept': image.rescale_intercept,
                'rescale_slope': image.rescale_slope,
            }
        })
    except DicomImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=404)


@csrf_exempt
@api_view(['POST'])
def save_measurement(request):
    """Save a measurement"""
    try:
        data = json.loads(request.body)
        image_id = data.get('image_id')
        measurement_type = data.get('measurement_type', 'line')
        coordinates = data.get('coordinates', {})
        value = data.get('value', 0)
        unit = data.get('unit', 'px')
        hounsfield_value = data.get('hounsfield_value', None)
        
        image = DicomImage.objects.get(id=image_id)
        
        measurement = Measurement.objects.create(
            image=image,
            measurement_type=measurement_type,
            coordinates=coordinates,
            value=value,
            unit=unit,
            hounsfield_value=hounsfield_value,
            created_by=request.user if request.user.is_authenticated else None,
        )
        
        return Response({
            'success': True,
            'measurement_id': measurement.id
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@csrf_exempt  
@api_view(['POST'])
def save_annotation(request):
    """Save an annotation"""
    try:
        data = json.loads(request.body)
        image_id = data.get('image_id')
        x_coordinate = data.get('x_coordinate')
        y_coordinate = data.get('y_coordinate')
        text = data.get('text', '')
        
        image = DicomImage.objects.get(id=image_id)
        
        annotation = Annotation.objects.create(
            image=image,
            x_coordinate=x_coordinate,
            y_coordinate=y_coordinate,
            text=text,
            created_by=request.user if request.user.is_authenticated else None,
        )
        
        return Response({
            'success': True,
            'annotation_id': annotation.id
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
def get_measurements(request, image_id):
    """Get measurements for an image"""
    try:
        image = DicomImage.objects.get(id=image_id)
        measurements = image.measurements.all()
        
        measurement_data = []
        for measurement in measurements:
            data = {
                'id': measurement.id,
                'type': measurement.measurement_type,
                'coordinates': measurement.coordinates,
                'value': measurement.value,
                'unit': measurement.unit,
                'hounsfield_value': measurement.hounsfield_value,
                'notes': measurement.notes,
            }
            measurement_data.append(data)
        
        return Response({'measurements': measurement_data})
    except DicomImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=404)


@api_view(['GET'])
def get_annotations(request, image_id):
    """Get annotations for an image"""
    try:
        image = DicomImage.objects.get(id=image_id)
        annotations = image.annotations.all()
        
        annotation_data = []
        for annotation in annotations:
            data = {
                'id': annotation.id,
                'x': annotation.x_coordinate,
                'y': annotation.y_coordinate,
                'text': annotation.text,
            }
            annotation_data.append(data)
        
        return Response({'annotations': annotation_data})
    except DicomImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=404)


@csrf_exempt
@api_view(['DELETE'])
def clear_measurements(request, image_id):
    """Clear all measurements for an image"""
    try:
        image = DicomImage.objects.get(id=image_id)
        image.measurements.all().delete()
        return Response({'success': True})
    except DicomImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=404)


@api_view(['GET'])
def get_worklist(request):
    """Get worklist data"""
    try:
        # Get user profile
        user_profile = None
        if request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
            except UserProfile.DoesNotExist:
                pass
        
        # Filter studies based on user role
        studies = DicomStudy.objects.all()
        
        if user_profile and not user_profile.can_view_all_facilities:
            # Facility staff can only see their facility's studies
            if user_profile.facility:
                studies = studies.filter(facility=user_profile.facility)
        
        # Apply filters
        search = request.GET.get('search', '')
        facility_filter = request.GET.get('facility', '')
        modality_filter = request.GET.get('modality', '')
        
        if search:
            studies = studies.filter(
                Q(patient_name__icontains=search) |
                Q(patient_id__icontains=search)
            )
        
        if facility_filter:
            studies = studies.filter(facility__code=facility_filter)
        
        if modality_filter:
            studies = studies.filter(modality=modality_filter)
        
        patients = []
        for study in studies[:100]:  # Limit to 100 studies
            patients.append({
                'study_id': study.id,
                'patient_name': study.patient_name,
                'patient_id': study.patient_id,
                'study_date': study.study_date.isoformat() if study.study_date else None,
                'modality': study.modality,
                'facility': study.facility.name if study.facility else 'Unknown',
                'status': study.status,
            })
        
        return Response({'patients': patients})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def get_hounsfield_units(request, image_id):
    """Get Hounsfield units for a specific point"""
    try:
        image = DicomImage.objects.get(id=image_id)
        x = float(request.GET.get('x', 0))
        y = float(request.GET.get('y', 0))
        radius = int(request.GET.get('radius', 5))
        
        hu_data = image.get_hounsfield_units(x, y, radius)
        
        if hu_data:
            return Response(hu_data)
        else:
            return Response({'error': 'Could not calculate Hounsfield units'}, status=400)
    except DicomImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
def get_notifications(request):
    """Get notifications for the current user"""
    try:
        if not request.user.is_authenticated:
            return Response({'notifications': []})
        
        notifications = Notification.objects.filter(
            Q(recipient=request.user) | Q(recipient__isnull=True)
        ).filter(is_read=False)[:10]
        
        notification_data = []
        for notification in notifications:
            notification_data.append({
                'id': notification.id,
                'type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'created_at': notification.created_at.isoformat(),
            })
        
        return Response({
            'notifications': notification_data,
            'new_uploads': Notification.objects.filter(
                notification_type='new_upload',
                is_read=False
            ).count()
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
def save_report(request):
    """Save a radiology report"""
    try:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        data = json.loads(request.body)
        study_id = data.get('study_id')
        clinical_info = data.get('clinical_information', '')
        findings = data.get('findings', '')
        impression = data.get('impression', '')
        recommendation = data.get('recommendation', '')
        
        study = DicomStudy.objects.get(id=study_id)
        
        # Check if user can create reports
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if not user_profile.can_create_reports:
                return Response({'error': 'Insufficient permissions'}, status=403)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found'}, status=400)
        
        report = RadiologyReport.objects.create(
            study=study,
            clinical_information=clinical_info,
            findings=findings,
            impression=impression,
            recommendation=recommendation,
            created_by=request.user,
        )
        
        # Update study status
        study.status = 'pending'
        study.save()
        
        return Response({
            'success': True,
            'report_id': report.id
        })
    except DicomStudy.DoesNotExist:
        return Response({'error': 'Study not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
def get_report(request, study_id):
    """Get report for a study"""
    try:
        study = DicomStudy.objects.get(id=study_id)
        report = study.reports.first()
        
        if report:
            return Response({
                'id': report.id,
                'clinical_information': report.clinical_information,
                'findings': report.findings,
                'impression': report.impression,
                'recommendation': report.recommendation,
                'status': report.status,
                'created_at': report.created_at.isoformat(),
                'created_by': report.created_by.username if report.created_by else None,
            })
        else:
            return Response({'error': 'No report found'}, status=404)
    except DicomStudy.DoesNotExist:
        return Response({'error': 'Study not found'}, status=404)


def parse_dicom_date(date_str):
    """Parse DICOM date string to Python date"""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), '%Y%m%d').date()
    except ValueError:
        return None


def parse_dicom_time(time_str):
    """Parse DICOM time string to Python time"""
    if not time_str:
        return None
    try:
        return datetime.strptime(str(time_str), '%H%M%S.%f').time()
    except ValueError:
        try:
            return datetime.strptime(str(time_str), '%H%M%S').time()
        except ValueError:
            return None