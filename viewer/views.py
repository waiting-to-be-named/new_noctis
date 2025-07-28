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
from .models import DicomStudy, DicomSeries, DicomImage, Measurement, Annotation
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