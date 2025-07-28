# dicom_viewer/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
import os
import pydicom
from datetime import datetime
from django.utils import timezone
import uuid
import numpy as np
from .models import (
    DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
    Facility, Report, WorklistEntry, AIAnalysis, Notification
)
from .serializers import DicomStudySerializer, DicomImageSerializer


class HomeView(TemplateView):
    """Home page with launch buttons"""
    template_name = 'home.html'


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
            
            # Create/update study with facility association
            study_uid = str(dicom_data.get('StudyInstanceUID', ''))
            if not study:
                study, created = DicomStudy.objects.get_or_create(
                    study_instance_uid=study_uid,
                    defaults={
                        'patient_name': str(dicom_data.PatientName) if hasattr(dicom_data, 'PatientName') else 'Unknown',
                        'patient_id': str(dicom_data.PatientID) if hasattr(dicom_data, 'PatientID') else 'Unknown',
                        'study_date': parse_dicom_date(getattr(dicom_data, 'StudyDate', None)),
                        'study_time': parse_dicom_time(getattr(dicom_data, 'StudyTime', None)),
                        'study_description': str(getattr(dicom_data, 'StudyDescription', '')),
                        'modality': str(dicom_data.Modality) if hasattr(dicom_data, 'Modality') else 'OT',
                        'institution_name': str(getattr(dicom_data, 'InstitutionName', '')),
                        'uploaded_by': request.user if request.user.is_authenticated else None,
                        'facility': request.user.facility_staff.facility if hasattr(request.user, 'facility_staff') else None,
                    }
                )
            
            # If study was created, send notifications and create worklist entry
            if created:
                radiologists = User.objects.filter(groups__name='Radiologists')
                for radiologist in radiologists:
                    Notification.objects.create(
                        recipient=radiologist,
                        notification_type='new_study',
                        title=f'New {study.modality} Study',
                        message=f'New study uploaded for {study.patient_name}',
                        related_study=study
                    )

                # Determine facility for worklist entry (fallback to first facility)
                facility_for_entry = study.facility or Facility.objects.first()

                # Create corresponding worklist entry so the study shows up in the worklist
                try:
                    WorklistEntry.objects.create(
                        patient_name=study.patient_name,
                        patient_id=study.patient_id,
                        accession_number=str(getattr(dicom_data, 'AccessionNumber', '')) or uuid.uuid4().hex[:12],
                        scheduled_station_ae_title='UPLOAD',
                        scheduled_procedure_step_start_date=timezone.now().date(),
                        scheduled_procedure_step_start_time=timezone.now().time(),
                        modality=study.modality,
                        scheduled_performing_physician=str(getattr(dicom_data, 'PerformingPhysicianName', '')),
                        procedure_description=study.study_description or 'Uploaded Study',
                        facility=facility_for_entry,
                        status='completed',
                        study=study,
                    )
                except Exception:
                    # Don't fail the upload if the worklist entry creation has an issue
                    pass
            
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
        image_id = data.get('image_id')
        measurement_type = data.get('measurement_type')
        coordinates = data.get('coordinates')
        value = data.get('value')
        unit = data.get('unit', 'px')
        
        # Convert pixel measurements to selected unit
        image = get_object_or_404(DicomImage, id=image_id)
        
        if unit in ['mm', 'cm'] and measurement_type == 'line':
            # Get pixel spacing
            pixel_spacing_x = image.pixel_spacing_x or 1.0
            pixel_spacing_y = image.pixel_spacing_y or 1.0
            
            # Convert based on measurement type
            if measurement_type == 'line':
                # Calculate actual distance in mm
                dx = (coordinates['x1'] - coordinates['x0']) * pixel_spacing_x
                dy = (coordinates['y1'] - coordinates['y0']) * pixel_spacing_y
                value_mm = np.sqrt(dx**2 + dy**2)
                
                if unit == 'cm':
                    value = value_mm / 10.0
                else:
                    value = value_mm
        
        # Handle ellipse HU measurements
        if measurement_type == 'ellipse':
            # Calculate HU values
            pixel_array = image.get_pixel_array()
            dicom_data = image.load_dicom_data()
            
            if pixel_array is not None and dicom_data:
                # Apply rescale for HU
                rescale_slope = float(getattr(dicom_data, 'RescaleSlope', 1))
                rescale_intercept = float(getattr(dicom_data, 'RescaleIntercept', 0))
                pixel_array = pixel_array * rescale_slope + rescale_intercept
                
                # Extract ellipse region
                x0, y0 = coordinates['x0'], coordinates['y0']
                x1, y1 = coordinates['x1'], coordinates['y1']
                
                # Calculate ellipse mask
                xc = (x0 + x1) / 2.0
                yc = (y0 + y1) / 2.0
                a = abs(x1 - x0) / 2.0
                b = abs(y1 - y0) / 2.0
                
                y_min = int(max(min(y0, y1), 0))
                y_max = int(min(max(y0, y1), pixel_array.shape[0] - 1))
                x_min = int(max(min(x0, x1), 0))
                x_max = int(min(max(x0, x1), pixel_array.shape[1] - 1))
                
                yy, xx = np.ogrid[y_min:y_max + 1, x_min:x_max + 1]
                ellipse_mask = (((xx - xc) / a) ** 2 + ((yy - yc) / b) ** 2) <= 1.0
                
                region_pixels = pixel_array[y_min:y_max + 1, x_min:x_max + 1][ellipse_mask]
                
                if region_pixels.size > 0:
                    hounsfield_mean = float(np.mean(region_pixels))
                    hounsfield_min = float(np.min(region_pixels))
                    hounsfield_max = float(np.max(region_pixels))
                    hounsfield_std = float(np.std(region_pixels))
                    
                    measurement = Measurement.objects.create(
                        image_id=image_id,
                        measurement_type=measurement_type,
                        coordinates=coordinates,
                        value=hounsfield_mean,
                        unit='HU',
                        hounsfield_mean=hounsfield_mean,
                        hounsfield_min=hounsfield_min,
                        hounsfield_max=hounsfield_max,
                        hounsfield_std=hounsfield_std,
                        notes=data.get('notes', ''),
                        created_by=request.user if request.user.is_authenticated else None,
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'measurement_id': measurement.id,
                        'hounsfield_mean': hounsfield_mean,
                        'hounsfield_min': hounsfield_min,
                        'hounsfield_max': hounsfield_max,
                        'hounsfield_std': hounsfield_std
                    })
        
        else:
            # Regular measurement
            measurement = Measurement.objects.create(
                image_id=image_id,
                measurement_type=measurement_type,
                coordinates=coordinates,
                value=value,
                unit=unit,
                notes=data.get('notes', ''),
                created_by=request.user if request.user.is_authenticated else None,
            )
        
        return JsonResponse({
            'success': True,
            'measurement_id': measurement.id,
            'value': measurement.value,
            'unit': measurement.unit
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['POST'])
def save_annotation(request):
    """Save an annotation with enhanced properties"""
    try:
        data = json.loads(request.body)
        
        annotation = Annotation.objects.create(
            image_id=data.get('image_id'),
            x_coordinate=data.get('x'),
            y_coordinate=data.get('y'),
            text=data.get('text'),
            font_size=data.get('font_size', 14),
            color=data.get('color', '#FFFF00'),
            created_by=request.user if request.user.is_authenticated else None,
        )
        
        return JsonResponse({
            'success': True,
            'annotation_id': annotation.id,
            'font_size': annotation.font_size,
            'color': annotation.color
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


@csrf_exempt
@api_view(['POST'])
def measure_hu(request):
    """Calculate average Hounsfield Units inside an ellipse region"""
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

        # Save measurement
        measurement = Measurement.objects.create(
            image=image,
            measurement_type='ellipse',
            coordinates={'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1},
            value=mean_hu,
            unit='HU',
            notes=f"Min: {min_hu:.1f}, Max: {max_hu:.1f}",
            created_by=request.user if request.user.is_authenticated else None,
        )

        return JsonResponse({
            'success': True,
            'measurement_id': measurement.id,
            'mean_hu': mean_hu,
            'min_hu': min_hu,
            'max_hu': max_hu,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_view(['POST'])
def perform_ai_analysis(request, image_id):
    """Perform AI analysis on DICOM image"""
    try:
        image = get_object_or_404(DicomImage, id=image_id)
        
        # Mock AI analysis - in production, this would call actual AI model
        pixel_array = image.get_pixel_array()
        if pixel_array is None:
            return Response({'error': 'Cannot load image data'}, status=400)
        
        # Simulate finding regions of interest
        height, width = pixel_array.shape
        mock_findings = []
        
        # Generate some mock findings
        for i in range(3):
            x = np.random.randint(width * 0.2, width * 0.8)
            y = np.random.randint(height * 0.2, height * 0.8)
            size = np.random.randint(20, 50)
            confidence = np.random.uniform(0.7, 0.95)
            
            mock_findings.append({
                'type': np.random.choice(['nodule', 'consolidation', 'opacity']),
                'location': {'x': int(x), 'y': int(y)},
                'size': int(size),
                'confidence': float(confidence)
            })
        
        # Create AI analysis record
        analysis = AIAnalysis.objects.create(
            image=image,
            analysis_type='chest_xray_abnormality_detection',
            findings=mock_findings,
            summary=f"Detected {len(mock_findings)} potential abnormalities with high confidence.",
            confidence_score=0.85,
            highlighted_regions=[{
                'x': f['location']['x'],
                'y': f['location']['y'],
                'width': f['size'],
                'height': f['size'],
                'label': f['type'],
                'confidence': f['confidence']
            } for f in mock_findings]
        )
        
        return Response({
            'analysis_id': analysis.id,
            'findings': analysis.findings,
            'summary': analysis.summary,
            'highlighted_regions': analysis.highlighted_regions,
            'confidence_score': analysis.confidence_score
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@csrf_exempt
@api_view(['GET'])
def get_3d_reconstruction(request, series_id):
    """Get 3D reconstruction data for a series"""
    try:
        series = get_object_or_404(DicomSeries, id=series_id)
        reconstruction_type = request.GET.get('type', 'mpr')
        
        # Check if series has enough images for 3D
        if series.image_count < 10:
            return Response({
                'error': 'Not enough images for 3D reconstruction'
            }, status=400)
        
        # Mock 3D reconstruction data
        if reconstruction_type == 'mpr':
            # Multi-planar reconstruction
            return Response({
                'type': 'mpr',
                'planes': {
                    'axial': {'available': True, 'slice_count': series.image_count},
                    'coronal': {'available': True, 'slice_count': 100},
                    'sagittal': {'available': True, 'slice_count': 100}
                },
                'voxel_spacing': [1.0, 1.0, 2.0]
            })
            
        elif reconstruction_type == '3d_bone':
            # 3D bone reconstruction
            return Response({
                'type': '3d_bone',
                'mesh_data': {
                    'vertices': 15000,
                    'faces': 30000,
                    'threshold': 200  # HU threshold for bone
                },
                'rendering_params': {
                    'opacity': 0.8,
                    'color': '#F5DEB3'
                }
            })
            
        elif reconstruction_type == 'angio':
            # Angiography reconstruction
            return Response({
                'type': 'angio',
                'vessel_tree': {
                    'main_vessels': 12,
                    'branches': 45
                },
                'contrast_params': {
                    'window': 600,
                    'level': 100
                }
            })
            
        elif reconstruction_type == 'virtual_surgery':
            # Virtual surgery planning
            return Response({
                'type': 'virtual_surgery',
                'tools': ['cutting_plane', 'measurement', 'annotation'],
                'anatomical_structures': ['bone', 'soft_tissue', 'vessels'],
                'planning_data': {
                    'cutting_planes': [],
                    'measurements': [],
                    'annotations': []
                }
            })
            
        else:
            return Response({'error': 'Unknown reconstruction type'}, status=400)
            
    except Exception as e:
        return Response({'error': str(e)}, status=400)


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