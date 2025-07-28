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
from .ai_utils import DicomImageAnalyzer, DicomAIPredictor
from .anonymizer import DicomAnonymizer, SecureAnonymizer
from django.conf import settings
import logging
import tempfile
import zipfile
from django.http import StreamingHttpResponse
import io

logger = logging.getLogger(__name__)


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


# AI Analysis Endpoints
@api_view(['POST'])
@login_required
def analyze_image(request, image_id):
    """Perform AI analysis on a DICOM image"""
    try:
        image = get_object_or_404(DicomImage, id=image_id)
        
        # Get analysis parameters from request
        analysis_type = request.data.get('analysis_type', 'anomaly_detection')
        
        # Initialize analyzer
        analyzer = DicomImageAnalyzer()
        
        # Get image array
        image_array = image.get_pixel_array()
        
        if analysis_type == 'anomaly_detection':
            results = analyzer.detect_anomalies(image_array)
        elif analysis_type == 'enhancement':
            enhancement_type = request.data.get('enhancement_type', 'auto')
            enhanced_image = analyzer.enhance_image(image_array, enhancement_type)
            # Convert to base64 for frontend
            results = {
                'enhanced_image': image_to_base64(enhanced_image),
                'enhancement_type': enhancement_type
            }
        elif analysis_type == 'roi_measurement':
            roi_coords = request.data.get('roi_coords', [])
            pixel_spacing = (image.pixel_spacing_x, image.pixel_spacing_y)
            results = analyzer.measure_roi(image_array, roi_coords, pixel_spacing)
        else:
            return Response({'error': 'Invalid analysis type'}, status=400)
        
        return Response({
            'success': True,
            'results': results,
            'analysis_type': analysis_type
        })
        
    except Exception as e:
        logger.error(f"Error in image analysis: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@login_required
def predict_image(request, image_id):
    """Make AI prediction on DICOM image"""
    if not settings.ENABLE_AI_ANALYSIS:
        return Response({'error': 'AI analysis is disabled'}, status=403)
    
    try:
        image = get_object_or_404(DicomImage, id=image_id)
        
        # Initialize predictor
        model_path = request.data.get('model_path', None)
        predictor = DicomAIPredictor(model_path)
        
        # Get image array
        image_array = image.get_pixel_array()
        
        # Make prediction
        results = predictor.predict(image_array)
        
        return Response({
            'success': True,
            'prediction': results
        })
        
    except Exception as e:
        logger.error(f"Error in prediction: {e}")
        return Response({'error': str(e)}, status=500)


# Anonymization Endpoints
@api_view(['POST'])
@login_required
def anonymize_study(request, study_id):
    """Anonymize all DICOM files in a study"""
    try:
        study = get_object_or_404(DicomStudy, id=study_id)
        
        # Get anonymization options
        keep_dates = request.data.get('keep_dates', False)
        keep_uid_structure = request.data.get('keep_uid_structure', True)
        use_secure = request.data.get('use_secure', False)
        
        # Initialize anonymizer
        if use_secure:
            anonymizer = SecureAnonymizer(keep_dates=keep_dates, keep_uid_structure=keep_uid_structure)
        else:
            anonymizer = DicomAnonymizer(keep_dates=keep_dates, keep_uid_structure=keep_uid_structure)
        
        # Create temporary directory for anonymized files
        with tempfile.TemporaryDirectory() as temp_dir:
            anonymized_files = []
            
            # Anonymize all images in the study
            for series in study.series.all():
                for image in series.images.all():
                    try:
                        # Read original file
                        ds = pydicom.dcmread(image.file_path.path)
                        
                        # Anonymize
                        anon_ds = anonymizer.anonymize_dataset(ds)
                        
                        # Save to temp directory
                        filename = f"anon_{study.id}_{series.id}_{image.id}.dcm"
                        filepath = os.path.join(temp_dir, filename)
                        anon_ds.save_as(filepath)
                        anonymized_files.append(filepath)
                        
                    except Exception as e:
                        logger.error(f"Error anonymizing image {image.id}: {e}")
            
            # Create zip file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filepath in anonymized_files:
                    arcname = os.path.basename(filepath)
                    zip_file.write(filepath, arcname)
            
            # Return zip file
            zip_buffer.seek(0)
            response = StreamingHttpResponse(
                zip_buffer,
                content_type='application/zip'
            )
            response['Content-Disposition'] = f'attachment; filename="anonymized_study_{study.id}.zip"'
            
            return response
            
    except Exception as e:
        logger.error(f"Error anonymizing study: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@login_required
def anonymize_batch(request):
    """Anonymize multiple DICOM files"""
    if 'files' not in request.FILES:
        return Response({'error': 'No files provided'}, status=400)
    
    try:
        files = request.FILES.getlist('files')
        
        # Get anonymization options
        keep_dates = request.data.get('keep_dates', False)
        keep_uid_structure = request.data.get('keep_uid_structure', True)
        
        # Initialize anonymizer
        anonymizer = DicomAnonymizer(keep_dates=keep_dates, keep_uid_structure=keep_uid_structure)
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            anonymized_files = []
            
            for i, file in enumerate(files):
                try:
                    # Save uploaded file temporarily
                    file_path = os.path.join(temp_dir, f"temp_{i}.dcm")
                    with open(file_path, 'wb') as f:
                        for chunk in file.chunks():
                            f.write(chunk)
                    
                    # Anonymize
                    output_path = os.path.join(temp_dir, f"anon_{i}.dcm")
                    anonymizer.anonymize_file(file_path, output_path)
                    anonymized_files.append(output_path)
                    
                except Exception as e:
                    logger.error(f"Error anonymizing file {file.name}: {e}")
            
            # Create zip file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filepath in anonymized_files:
                    arcname = os.path.basename(filepath)
                    zip_file.write(filepath, arcname)
            
            # Return zip file
            zip_buffer.seek(0)
            response = StreamingHttpResponse(
                zip_buffer,
                content_type='application/zip'
            )
            response['Content-Disposition'] = 'attachment; filename="anonymized_files.zip"'
            
            return response
            
    except Exception as e:
        logger.error(f"Error in batch anonymization: {e}")
        return Response({'error': str(e)}, status=500)


# Export Endpoints
@api_view(['POST'])
@login_required
def export_images(request):
    """Export processed images in various formats"""
    try:
        image_ids = request.data.get('image_ids', [])
        export_format = request.data.get('format', 'png')
        include_metadata = request.data.get('include_metadata', False)
        
        if not image_ids:
            return Response({'error': 'No images specified'}, status=400)
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            exported_files = []
            metadata = {}
            
            for image_id in image_ids:
                try:
                    image = DicomImage.objects.get(id=image_id)
                    image_array = image.get_pixel_array()
                    
                    # Apply window/level
                    windowed = apply_window_level(
                        image_array,
                        image.window_center,
                        image.window_width
                    )
                    
                    # Export based on format
                    if export_format == 'png':
                        filename = f"image_{image_id}.png"
                        filepath = os.path.join(temp_dir, filename)
                        save_image_as_png(windowed, filepath)
                    elif export_format == 'jpeg':
                        filename = f"image_{image_id}.jpg"
                        filepath = os.path.join(temp_dir, filename)
                        save_image_as_jpeg(windowed, filepath)
                    elif export_format == 'npy':
                        filename = f"image_{image_id}.npy"
                        filepath = os.path.join(temp_dir, filename)
                        np.save(filepath, image_array)
                    else:
                        continue
                    
                    exported_files.append(filepath)
                    
                    # Collect metadata if requested
                    if include_metadata:
                        metadata[filename] = {
                            'patient_name': image.series.study.patient_name,
                            'study_date': str(image.series.study.study_date),
                            'modality': image.series.modality,
                            'series_description': image.series.series_description,
                            'instance_number': image.instance_number,
                            'window_center': image.window_center,
                            'window_width': image.window_width,
                            'pixel_spacing': [image.pixel_spacing_x, image.pixel_spacing_y]
                        }
                    
                except Exception as e:
                    logger.error(f"Error exporting image {image_id}: {e}")
            
            # Save metadata if requested
            if include_metadata and metadata:
                metadata_path = os.path.join(temp_dir, 'metadata.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                exported_files.append(metadata_path)
            
            # Create zip file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filepath in exported_files:
                    arcname = os.path.basename(filepath)
                    zip_file.write(filepath, arcname)
            
            # Return zip file
            zip_buffer.seek(0)
            response = StreamingHttpResponse(
                zip_buffer,
                content_type='application/zip'
            )
            response['Content-Disposition'] = f'attachment; filename="exported_images.zip"'
            
            return response
            
    except Exception as e:
        logger.error(f"Error exporting images: {e}")
        return Response({'error': str(e)}, status=500)


# Helper functions
def image_to_base64(image_array):
    """Convert numpy array to base64 encoded image"""
    from PIL import Image
    import base64
    
    # Normalize to 0-255
    if image_array.dtype != np.uint8:
        image_array = ((image_array - image_array.min()) / 
                      (image_array.max() - image_array.min()) * 255).astype(np.uint8)
    
    # Convert to PIL Image
    pil_image = Image.fromarray(image_array)
    
    # Save to buffer
    buffer = io.BytesIO()
    pil_image.save(buffer, format='PNG')
    
    # Encode to base64
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return f"data:image/png;base64,{image_base64}"


def apply_window_level(image_array, window_center, window_width):
    """Apply window/level to image array"""
    min_val = window_center - window_width // 2
    max_val = window_center + window_width // 2
    
    windowed = np.clip(image_array, min_val, max_val)
    windowed = ((windowed - min_val) / (max_val - min_val) * 255).astype(np.uint8)
    
    return windowed


def save_image_as_png(image_array, filepath):
    """Save numpy array as PNG"""
    from PIL import Image
    Image.fromarray(image_array).save(filepath, 'PNG')


def save_image_as_jpeg(image_array, filepath):
    """Save numpy array as JPEG"""
    from PIL import Image
    Image.fromarray(image_array).save(filepath, 'JPEG', quality=95)