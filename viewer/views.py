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
import json
import os
import pydicom
from datetime import datetime
import numpy as np
from .models import (
    DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
    Facility, ClinicalInformation, Report, Notification
)
from .serializers import DicomStudySerializer, DicomImageSerializer


class LauncherView(TemplateView):
    """Launcher page for the DICOM viewer"""
    template_name = 'dicom_viewer/launcher.html'


class DicomViewerView(TemplateView):
    """Main DICOM viewer page"""
    template_name = 'dicom_viewer/viewer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['studies'] = DicomStudy.objects.all()[:10]  # Recent studies
        return context


class WorklistView(TemplateView):
    """Worklist view for viewing patient studies"""
    template_name = 'dicom_viewer/worklist.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Filter studies based on user role
        if user.is_superuser or user.groups.filter(name__in=['radiologist', 'admin']).exists():
            # Admin/radiologist can see all studies
            studies = DicomStudy.objects.all()
        else:
            # Regular users can only see their facility's studies
            if hasattr(user, 'profile') and user.profile.facility:
                studies = DicomStudy.objects.filter(facility=user.profile.facility)
            else:
                studies = DicomStudy.objects.none()
        
        context['studies'] = studies
        context['facilities'] = Facility.objects.all()
        return context


class ReportView(TemplateView):
    """Report writing view"""
    template_name = 'dicom_viewer/report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        study_id = self.request.GET.get('study_id')
        if study_id:
            context['study'] = get_object_or_404(DicomStudy, id=study_id)
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
        radiologists = User.objects.filter(groups__name='radiologist')
        for radiologist in radiologists:
            Notification.objects.create(
                recipient=radiologist,
                notification_type='new_upload',
                title='New DICOM Upload',
                message=f'New study uploaded for patient {study.patient_name}',
                study=study
            )
    
    return JsonResponse({
        'success': True,
        'study_id': study.id if study else None,
        'uploaded_files': uploaded_files
    })


@api_view(['GET'])
def get_studies(request):
    """Get list of studies for worklist"""
    user = request.user
    facility_id = request.GET.get('facility_id')
    
    if user.is_superuser or user.groups.filter(name__in=['radiologist', 'admin']).exists():
        studies = DicomStudy.objects.all()
    else:
        if hasattr(user, 'profile') and user.profile.facility:
            studies = DicomStudy.objects.filter(facility=user.profile.facility)
        else:
            studies = DicomStudy.objects.none()
    
    if facility_id:
        studies = studies.filter(facility_id=facility_id)
    
    serializer = DicomStudySerializer(studies, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_study_images(request, study_id):
    """Get images for a specific study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    images = []
    
    for series in study.series.all():
        for image in series.images.all():
            images.append({
                'id': image.id,
                'series_number': series.series_number,
                'instance_number': image.instance_number,
                'description': series.series_description,
                'modality': series.modality,
            })
    
    return Response({'images': images})


@api_view(['GET'])
def get_image_data(request, image_id):
    """Get processed image data"""
    image = get_object_or_404(DicomImage, id=image_id)
    
    # Get window/level parameters
    window_width = request.GET.get('ww', image.window_width or 400)
    window_level = request.GET.get('wl', image.window_center or 40)
    inverted = request.GET.get('inverted', 'false').lower() == 'true'
    
    # Get processed image
    image_data = image.get_processed_image_base64(
        window_width=float(window_width),
        window_level=float(window_level),
        inverted=inverted
    )
    
    if not image_data:
        return Response({'error': 'Failed to process image'}, status=400)
    
    return Response({
        'image_data': image_data,
        'metadata': {
            'rows': image.rows,
            'columns': image.columns,
            'pixel_spacing_x': image.pixel_spacing_x,
            'pixel_spacing_y': image.pixel_spacing_y,
            'slice_thickness': image.slice_thickness,
            'window_width': image.window_width,
            'window_center': image.window_center,
        }
    })


@csrf_exempt
@api_view(['POST'])
def save_measurement(request):
    """Save a measurement"""
    data = json.loads(request.body)
    image_id = data.get('image_id')
    measurement_type = data.get('type')
    coordinates = data.get('coordinates')
    value = data.get('value')
    unit = data.get('unit', 'px')
    hounsfield_units = data.get('hounsfield_units')
    notes = data.get('notes', '')
    
    image = get_object_or_404(DicomImage, id=image_id)
    
    measurement = Measurement.objects.create(
        image=image,
        measurement_type=measurement_type,
        coordinates=coordinates,
        value=value,
        unit=unit,
        hounsfield_units=hounsfield_units,
        notes=notes,
        created_by=request.user if request.user.is_authenticated else None
    )
    
    return Response({
        'id': measurement.id,
        'type': measurement.measurement_type,
        'value': measurement.value,
        'unit': measurement.unit,
        'hounsfield_units': measurement.hounsfield_units
    })


@csrf_exempt  
@api_view(['POST'])
def save_annotation(request):
    """Save an annotation"""
    data = json.loads(request.body)
    image_id = data.get('image_id')
    x = data.get('x')
    y = data.get('y')
    text = data.get('text')
    font_size = data.get('font_size', 14)
    color = data.get('color', '#FF0000')
    
    image = get_object_or_404(DicomImage, id=image_id)
    
    annotation = Annotation.objects.create(
        image=image,
        x_coordinate=x,
        y_coordinate=y,
        text=text,
        font_size=font_size,
        color=color,
        created_by=request.user if request.user.is_authenticated else None
    )
    
    return Response({
        'id': annotation.id,
        'x': annotation.x_coordinate,
        'y': annotation.y_coordinate,
        'text': annotation.text,
        'font_size': annotation.font_size,
        'color': annotation.color
    })


@api_view(['GET'])
def get_measurements(request, image_id):
    """Get measurements for an image"""
    image = get_object_or_404(DicomImage, id=image_id)
    measurements = image.measurements.all()
    
    data = []
    for measurement in measurements:
        data.append({
            'id': measurement.id,
            'type': measurement.measurement_type,
            'coordinates': measurement.coordinates,
            'value': measurement.value,
            'unit': measurement.unit,
            'hounsfield_units': measurement.hounsfield_units,
            'notes': measurement.notes
        })
    
    return Response({'measurements': data})


@api_view(['GET'])
def get_annotations(request, image_id):
    """Get annotations for an image"""
    image = get_object_or_404(DicomImage, id=image_id)
    annotations = image.annotations.all()
    
    data = []
    for annotation in annotations:
        data.append({
            'id': annotation.id,
            'x': annotation.x_coordinate,
            'y': annotation.y_coordinate,
            'text': annotation.text,
            'font_size': annotation.font_size,
            'color': annotation.color
        })
    
    return Response({'annotations': data})


@csrf_exempt
@api_view(['DELETE'])
def clear_measurements(request, image_id):
    """Clear all measurements for an image"""
    image = get_object_or_404(DicomImage, id=image_id)
    image.measurements.all().delete()
    return Response({'success': True})


@csrf_exempt
@api_view(['POST'])
def measure_hu(request):
    """Measure Hounsfield units in an ellipse region"""
    data = json.loads(request.body)
    image_id = data.get('image_id')
    center_x = data.get('center_x')
    center_y = data.get('center_y')
    radius_x = data.get('radius_x')
    radius_y = data.get('radius_y')
    
    image = get_object_or_404(DicomImage, id=image_id)
    pixel_array = image.get_pixel_array()
    
    if pixel_array is None:
        return Response({'error': 'Failed to load pixel data'}, status=400)
    
    # Create ellipse mask
    y, x = np.ogrid[:pixel_array.shape[0], :pixel_array.shape[1]]
    
    # Normalize coordinates
    center_x_norm = center_x / image.columns
    center_y_norm = center_y / image.rows
    radius_x_norm = radius_x / image.columns
    radius_y_norm = radius_y / image.rows
    
    # Create mask
    mask = ((x - center_x_norm) ** 2 / radius_x_norm ** 2 + 
            (y - center_y_norm) ** 2 / radius_y_norm ** 2) <= 1
    
    # Get pixel values in ellipse
    ellipse_pixels = pixel_array[mask]
    
    if len(ellipse_pixels) == 0:
        return Response({'error': 'No pixels found in ellipse'}, status=400)
    
    # Calculate statistics
    mean_hu = float(np.mean(ellipse_pixels))
    min_hu = float(np.min(ellipse_pixels))
    max_hu = float(np.max(ellipse_pixels))
    std_hu = float(np.std(ellipse_pixels))
    
    # Save measurement
    measurement = Measurement.objects.create(
        image=image,
        measurement_type='ellipse',
        coordinates={
            'center_x': center_x,
            'center_y': center_y,
            'radius_x': radius_x,
            'radius_y': radius_y
        },
        value=mean_hu,
        unit='HU',
        hounsfield_units=mean_hu,
        notes=f'Mean: {mean_hu:.1f} HU, Min: {min_hu:.1f} HU, Max: {max_hu:.1f} HU, Std: {std_hu:.1f} HU',
        created_by=request.user if request.user.is_authenticated else None
    )
    
    return Response({
        'id': measurement.id,
        'mean_hu': mean_hu,
        'min_hu': min_hu,
        'max_hu': max_hu,
        'std_hu': std_hu,
        'pixel_count': len(ellipse_pixels)
    })


@api_view(['GET'])
def get_clinical_info(request, study_id):
    """Get clinical information for a study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    clinical_info, created = ClinicalInformation.objects.get_or_create(study=study)
    
    return Response({
        'chief_complaint': clinical_info.chief_complaint,
        'clinical_history': clinical_info.clinical_history,
        'physical_examination': clinical_info.physical_examination,
        'clinical_diagnosis': clinical_info.clinical_diagnosis,
        'referring_physician': clinical_info.referring_physician,
    })


@csrf_exempt
@api_view(['POST'])
def save_clinical_info(request, study_id):
    """Save clinical information for a study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    data = json.loads(request.body)
    
    clinical_info, created = ClinicalInformation.objects.get_or_create(study=study)
    clinical_info.chief_complaint = data.get('chief_complaint', '')
    clinical_info.clinical_history = data.get('clinical_history', '')
    clinical_info.physical_examination = data.get('physical_examination', '')
    clinical_info.clinical_diagnosis = data.get('clinical_diagnosis', '')
    clinical_info.referring_physician = data.get('referring_physician', '')
    clinical_info.created_by = request.user if request.user.is_authenticated else None
    clinical_info.save()
    
    return Response({'success': True})


@api_view(['GET'])
def get_report(request, study_id):
    """Get report for a study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    report, created = Report.objects.get_or_create(study=study)
    
    return Response({
        'title': report.title,
        'findings': report.findings,
        'impression': report.impression,
        'recommendations': report.recommendations,
        'status': report.status,
    })


@csrf_exempt
@api_view(['POST'])
def save_report(request, study_id):
    """Save report for a study"""
    study = get_object_or_404(DicomStudy, id=study_id)
    data = json.loads(request.body)
    
    report, created = Report.objects.get_or_create(study=study)
    report.title = data.get('title', 'Radiology Report')
    report.findings = data.get('findings', '')
    report.impression = data.get('impression', '')
    report.recommendations = data.get('recommendations', '')
    report.status = data.get('status', 'draft')
    report.created_by = request.user if request.user.is_authenticated else None
    report.save()
    
    return Response({'success': True})


@api_view(['GET'])
def get_notifications(request):
    """Get notifications for current user"""
    if not request.user.is_authenticated:
        return Response({'notifications': []})
    
    notifications = Notification.objects.filter(recipient=request.user, is_read=False)
    
    data = []
    for notification in notifications:
        data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'study_id': notification.study.id if notification.study else None,
            'created_at': notification.created_at.isoformat(),
        })
    
    return Response({'notifications': data})


@csrf_exempt
@api_view(['POST'])
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return Response({'success': True})


@api_view(['GET'])
def get_3d_reconstruction_types(request):
    """Get available 3D reconstruction types"""
    return Response({
        'reconstruction_types': [
            {'id': 'mpr', 'name': 'MPR (Multi-Planar Reconstruction)'},
            {'id': '3d_bone', 'name': '3D Bone Reconstruction'},
            {'id': 'angio', 'name': 'Angio Reconstruction'},
            {'id': 'virtual_surgery', 'name': 'Virtual Surgery Planning'},
        ]
    })


@api_view(['GET'])
def get_ai_analysis_types(request):
    """Get available AI analysis types"""
    return Response({
        'ai_types': [
            {'id': 'lung_nodule', 'name': 'Lung Nodule Detection'},
            {'id': 'brain_lesion', 'name': 'Brain Lesion Detection'},
            {'id': 'bone_fracture', 'name': 'Bone Fracture Detection'},
            {'id': 'tumor_segmentation', 'name': 'Tumor Segmentation'},
        ]
    })


def parse_dicom_date(date_str):
    """Parse DICOM date string"""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), '%Y%m%d').date()
    except:
        return None


def parse_dicom_time(time_str):
    """Parse DICOM time string"""
    if not time_str:
        return None
    try:
        return datetime.strptime(str(time_str), '%H%M%S').time()
    except:
        return None