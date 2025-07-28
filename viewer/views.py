# viewer/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from django.contrib import messages
import json
import os
import pydicom
from PIL import Image
import numpy as np
import io
import base64
from datetime import datetime, timedelta
import logging

from .models import (
    Facility, UserProfile, DicomStudy, DicomSeries, DicomImage, 
    Measurement, Annotation, ClinicalInfo, Report, 
    UploadNotification, AIAnalysis
)

logger = logging.getLogger(__name__)


@login_required
def viewer_home(request):
    """Main launcher page with role-based access"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Create a default profile for users without one
        user_profile = UserProfile.objects.create(
            user=request.user,
            role='facility'
        )
    
    context = {
        'user_profile': user_profile,
        'user_role': user_profile.role,
        'facility': user_profile.facility,
        'can_access_all_facilities': user_profile.role in ['radiologist', 'admin'],
    }
    
    return render(request, 'dicom_viewer/launcher.html', context)


@login_required
def worklist(request):
    """Patient worklist with facility-based filtering"""
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Filter studies based on user role
    if user_profile.role in ['radiologist', 'admin']:
        # Can see all facilities
        studies = DicomStudy.objects.all()
    else:
        # Can only see their facility's studies
        studies = DicomStudy.objects.filter(facility=user_profile.facility)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        studies = studies.filter(
            Q(patient_name__icontains=search_query) |
            Q(patient_id__icontains=search_query) |
            Q(accession_number__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        studies = studies.filter(status=status_filter)
    
    # Filter by modality
    modality_filter = request.GET.get('modality', '')
    if modality_filter:
        studies = studies.filter(modality=modality_filter)
    
    # Order by study date (newest first)
    studies = studies.order_by('-study_date', '-created_at')
    
    # Pagination
    paginator = Paginator(studies, 25)  # Show 25 studies per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'modality_filter': modality_filter,
        'user_profile': user_profile,
        'can_write_report': user_profile.role in ['radiologist', 'admin'],
        'can_print_report': user_profile.role in ['radiologist', 'admin', 'facility'],
    }
    
    return render(request, 'dicom_viewer/worklist.html', context)


@login_required
def launch_viewer(request):
    """Launch the DICOM viewer with a specific study"""
    study_id = request.GET.get('study_id')
    if not study_id:
        messages.error(request, 'No study ID provided')
        return redirect('worklist')
    
    try:
        study = get_object_or_404(DicomStudy, id=study_id)
        user_profile = get_object_or_404(UserProfile, user=request.user)
        
        # Check access permissions
        if user_profile.role not in ['radiologist', 'admin']:
            if study.facility != user_profile.facility:
                messages.error(request, 'Access denied to this study')
                return redirect('worklist')
        
        # Mark study as being viewed
        study.last_viewed = timezone.now()
        study.last_viewed_by = request.user
        study.save()
        
        return redirect(f"/viewer/?study_id={study_id}")
        
    except DicomStudy.DoesNotExist:
        messages.error(request, 'Study not found')
        return redirect('worklist')


@login_required
def viewer_page(request):
    """DICOM viewer page"""
    study_id = request.GET.get('study_id')
    series_id = request.GET.get('series_id')
    
    context = {
        'study_id': study_id,
        'series_id': series_id,
        'user_role': request.user.userprofile.role,
    }
    
    return render(request, 'dicom_viewer/viewer.html', context)


@login_required
def api_worklist_patients(request):
    """API endpoint for worklist patient data"""
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Filter studies based on user role
    if user_profile.role in ['radiologist', 'admin']:
        studies = DicomStudy.objects.all()
    else:
        studies = DicomStudy.objects.filter(facility=user_profile.facility)
    
    patients_data = []
    for study in studies[:50]:  # Limit to 50 for performance
        # Get clinical info and report
        clinical_info = ClinicalInfo.objects.filter(study=study).first()
        report = Report.objects.filter(study=study).first()
        
        patients_data.append({
            'id': study.id,
            'patient_id': study.patient_id,
            'name': study.patient_name,
            'birth_date': study.patient_birth_date.strftime('%Y-%m-%d') if study.patient_birth_date else '',
            'gender': study.patient_sex,
            'study_date': study.study_date.strftime('%Y-%m-%d') if study.study_date else '',
            'modality': study.modality,
            'status': study.status,
            'study_id': study.id,
            'clinical_info': clinical_info.content if clinical_info else '',
            'report': report.content if report else '',
            'facility': study.facility.name if study.facility else '',
        })
    
    return JsonResponse({'patients': patients_data})


@login_required
def api_studies(request):
    """API endpoint for DICOM studies"""
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    if user_profile.role in ['radiologist', 'admin']:
        studies = DicomStudy.objects.all()
    else:
        studies = DicomStudy.objects.filter(facility=user_profile.facility)
    
    studies_data = []
    for study in studies.order_by('-study_date')[:50]:
        studies_data.append({
            'id': study.id,
            'patient_name': study.patient_name,
            'patient_id': study.patient_id,
            'study_date': study.study_date.strftime('%Y-%m-%d') if study.study_date else '',
            'modality': study.modality,
            'study_description': study.study_description,
            'series_count': study.dicomseries_set.count(),
        })
    
    return JsonResponse(studies_data, safe=False)


@login_required
def api_study_images(request, study_id):
    """API endpoint for study images"""
    try:
        study = get_object_or_404(DicomStudy, id=study_id)
        user_profile = get_object_or_404(UserProfile, user=request.user)
        
        # Check access permissions
        if user_profile.role not in ['radiologist', 'admin']:
            if study.facility != user_profile.facility:
                return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get all series for this study
        series_list = []
        for series in study.dicomseries_set.all():
            images = []
            for image in series.dicomimage_set.all().order_by('instance_number'):
                images.append({
                    'id': image.id,
                    'instance_number': image.instance_number,
                    'image_position': [float(x) for x in image.image_position.split(',') if x] if image.image_position else [],
                    'pixel_spacing': [float(x) for x in image.pixel_spacing.split(',') if x] if image.pixel_spacing else [],
                    'window_width': image.window_width,
                    'window_center': image.window_center,
                })
            
            series_list.append({
                'id': series.id,
                'series_number': series.series_number,
                'series_description': series.series_description,
                'modality': series.modality,
                'image_count': series.dicomimage_set.count(),
                'images': images,
            })
        
        response_data = {
            'study': {
                'id': study.id,
                'patient_name': study.patient_name,
                'patient_id': study.patient_id,
                'study_date': study.study_date.strftime('%Y-%m-%d') if study.study_date else '',
                'modality': study.modality,
                'study_description': study.study_description,
            },
            'series': series_list,
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error loading study images: {e}")
        return JsonResponse({'error': 'Failed to load study images'}, status=500)


@login_required
def api_image_data(request, image_id):
    """API endpoint for DICOM image data"""
    try:
        image = get_object_or_404(DicomImage, id=image_id)
        
        # Check access permissions
        user_profile = get_object_or_404(UserProfile, user=request.user)
        if user_profile.role not in ['radiologist', 'admin']:
            if image.series.study.facility != user_profile.facility:
                return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Load DICOM file
        if not os.path.exists(image.file_path):
            return JsonResponse({'error': 'Image file not found'}, status=404)
        
        ds = pydicom.dcmread(image.file_path)
        
        # Get window/level parameters from request
        window_width = int(request.GET.get('window_width', image.window_width or 400))
        window_center = int(request.GET.get('window_center', image.window_center or 40))
        inverted = request.GET.get('inverted', 'false').lower() == 'true'
        
        # Convert DICOM to displayable image
        pixel_array = ds.pixel_array.astype(np.float64)
        
        # Apply window/level
        img_min = window_center - window_width // 2
        img_max = window_center + window_width // 2
        pixel_array = np.clip(pixel_array, img_min, img_max)
        
        # Normalize to 0-255
        pixel_array = ((pixel_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
        
        # Invert if requested
        if inverted:
            pixel_array = 255 - pixel_array
        
        # Convert to PIL Image
        pil_image = Image.fromarray(pixel_array)
        
        # Convert to base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        # Get metadata
        metadata = {
            'rows': int(ds.Rows),
            'columns': int(ds.Columns),
            'pixel_spacing': [float(ds.PixelSpacing[0]), float(ds.PixelSpacing[1])] if hasattr(ds, 'PixelSpacing') else [1.0, 1.0],
            'slice_thickness': float(ds.SliceThickness) if hasattr(ds, 'SliceThickness') else None,
            'window_width': window_width,
            'window_center': window_center,
            'rescale_intercept': float(ds.RescaleIntercept) if hasattr(ds, 'RescaleIntercept') else 0,
            'rescale_slope': float(ds.RescaleSlope) if hasattr(ds, 'RescaleSlope') else 1,
        }
        
        return JsonResponse({
            'image_data': f'data:image/png;base64,{img_str}',
            'metadata': metadata,
        })
        
    except Exception as e:
        logger.error(f"Error loading image data: {e}")
        return JsonResponse({'error': 'Failed to load image data'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_measurement(request):
    """API endpoint to save measurements"""
    try:
        data = json.loads(request.body)
        
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        # Check access permissions
        user_profile = get_object_or_404(UserProfile, user=request.user)
        if user_profile.role not in ['radiologist', 'admin']:
            if image.series.study.facility != user_profile.facility:
                return JsonResponse({'error': 'Access denied'}, status=403)
        
        measurement = Measurement.objects.create(
            image=image,
            user=request.user,
            measurement_type=data['type'],
            coordinates=json.dumps(data['coordinates']),
            value=data['value'],
            unit=data['unit'],
            metadata=json.dumps(data.get('metadata', {}))
        )
        
        return JsonResponse({'success': True, 'id': measurement.id})
        
    except Exception as e:
        logger.error(f"Error saving measurement: {e}")
        return JsonResponse({'error': 'Failed to save measurement'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_annotation(request):
    """API endpoint to save annotations"""
    try:
        data = json.loads(request.body)
        
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        # Check access permissions
        user_profile = get_object_or_404(UserProfile, user=request.user)
        if user_profile.role not in ['radiologist', 'admin']:
            if image.series.study.facility != user_profile.facility:
                return JsonResponse({'error': 'Access denied'}, status=403)
        
        annotation = Annotation.objects.create(
            image=image,
            user=request.user,
            x_position=data['x'],
            y_position=data['y'],
            text=data['text'],
            font_size=data.get('font_size', 16),
            color=data.get('color', '#FFD700')
        )
        
        return JsonResponse({'success': True, 'id': annotation.id})
        
    except Exception as e:
        logger.error(f"Error saving annotation: {e}")
        return JsonResponse({'error': 'Failed to save annotation'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_clinical_info(request, patient_id):
    """API endpoint to save clinical information"""
    try:
        data = json.loads(request.body)
        
        study = get_object_or_404(DicomStudy, id=patient_id)
        
        # Check access permissions
        user_profile = get_object_or_404(UserProfile, user=request.user)
        if user_profile.role not in ['radiologist', 'admin']:
            if study.facility != user_profile.facility:
                return JsonResponse({'error': 'Access denied'}, status=403)
        
        clinical_info, created = ClinicalInfo.objects.get_or_create(
            study=study,
            defaults={'user': request.user}
        )
        
        clinical_info.content = data['clinical_info']
        clinical_info.user = request.user
        clinical_info.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Error saving clinical info: {e}")
        return JsonResponse({'error': 'Failed to save clinical information'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_report(request, patient_id):
    """API endpoint to save reports (radiologist/admin only)"""
    try:
        user_profile = get_object_or_404(UserProfile, user=request.user)
        
        if user_profile.role not in ['radiologist', 'admin']:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        data = json.loads(request.body)
        study = get_object_or_404(DicomStudy, id=patient_id)
        
        report, created = Report.objects.get_or_create(
            study=study,
            defaults={'user': request.user}
        )
        
        report.content = data['report']
        report.user = request.user
        report.save()
        
        # Update study status
        study.status = 'reported'
        study.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        return JsonResponse({'error': 'Failed to save report'}, status=500)


@login_required
def api_check_new_uploads(request):
    """API endpoint to check for new uploads (radiologist/admin only)"""
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    if user_profile.role not in ['radiologist', 'admin']:
        return JsonResponse({'new_uploads': []})
    
    # Get notifications from the last 5 minutes that haven't been seen
    cutoff_time = timezone.now() - timedelta(minutes=5)
    notifications = UploadNotification.objects.filter(
        created_at__gte=cutoff_time,
        is_seen=False
    ).select_related('study', 'study__facility')
    
    new_uploads = []
    for notification in notifications:
        new_uploads.append({
            'study_id': notification.study.id,
            'patient_name': notification.study.patient_name,
            'facility': notification.study.facility.name if notification.study.facility else 'Unknown',
            'upload_time': notification.created_at.isoformat(),
        })
        
        # Mark as seen
        notification.is_seen = True
        notification.save()
    
    return JsonResponse({'new_uploads': new_uploads})


@login_required
@require_http_methods(["POST"])
def api_ai_analysis(request):
    """API endpoint for AI analysis"""
    try:
        data = json.loads(request.body)
        
        image = get_object_or_404(DicomImage, id=data['image_id'])
        
        # Check access permissions
        user_profile = get_object_or_404(UserProfile, user=request.user)
        if user_profile.role not in ['radiologist', 'admin']:
            if image.series.study.facility != user_profile.facility:
                return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Simulate AI analysis (in real implementation, this would call actual AI services)
        analysis_type = data.get('analysis_type', 'general')
        user_message = data.get('message', '')
        
        # Generate AI response based on analysis type
        if analysis_type == 'virtual_surgery':
            ai_response = generate_virtual_surgery_response(image, user_message)
        elif analysis_type == 'hounsfield':
            ai_response = generate_hounsfield_analysis(image, data.get('roi_coordinates'))
        else:
            ai_response = generate_general_analysis(image, user_message)
        
        # Save AI analysis
        analysis = AIAnalysis.objects.create(
            image=image,
            user=request.user,
            analysis_type=analysis_type,
            input_data=json.dumps(data),
            result=ai_response,
            confidence=0.85  # Simulated confidence
        )
        
        return JsonResponse({
            'success': True,
            'response': ai_response,
            'analysis_id': analysis.id
        })
        
    except Exception as e:
        logger.error(f"Error in AI analysis: {e}")
        return JsonResponse({'error': 'AI analysis failed'}, status=500)


def generate_virtual_surgery_response(image, user_message):
    """Generate virtual surgery AI response"""
    responses = [
        "Based on the anatomical structures visible, I recommend careful consideration of the vascular architecture in this region.",
        "The bone density appears suitable for surgical intervention. Consider the proximity to critical structures.",
        "Virtual surgical planning suggests an optimal approach through the lateral aspect to minimize tissue damage.",
        "The imaging shows good tissue contrast. Consider pre-operative marking of critical landmarks.",
    ]
    
    # In a real implementation, this would use actual AI models
    import random
    return random.choice(responses)


def generate_hounsfield_analysis(image, roi_coordinates):
    """Generate Hounsfield unit analysis"""
    # In a real implementation, this would calculate actual HU values
    return {
        'mean_hu': 45.2,
        'min_hu': -15.0,
        'max_hu': 180.5,
        'std_hu': 25.3,
        'tissue_type': 'Soft tissue',
        'analysis': 'The Hounsfield unit values suggest normal soft tissue density with no signs of calcification or abnormal enhancement.'
    }


def generate_general_analysis(image, user_message):
    """Generate general AI analysis"""
    responses = [
        "I can see the anatomical structures clearly. The image quality is good for diagnostic purposes.",
        "The contrast and resolution allow for detailed analysis of the region of interest.",
        "Consider measuring the dimensions of the identified structure for comparison with normal values.",
        "The imaging demonstrates normal anatomical relationships without obvious pathology.",
    ]
    
    import random
    return random.choice(responses)


@login_required
def print_report(request, patient_id):
    """Generate printable report"""
    try:
        study = get_object_or_404(DicomStudy, id=patient_id)
        user_profile = get_object_or_404(UserProfile, user=request.user)
        
        # Check access permissions
        if user_profile.role not in ['radiologist', 'admin', 'facility']:
            return HttpResponse('Access denied', status=403)
        
        if user_profile.role == 'facility' and study.facility != user_profile.facility:
            return HttpResponse('Access denied', status=403)
        
        # Get report and clinical info
        report = Report.objects.filter(study=study).first()
        clinical_info = ClinicalInfo.objects.filter(study=study).first()
        
        context = {
            'study': study,
            'report': report,
            'clinical_info': clinical_info,
            'facility': study.facility,
            'print_date': timezone.now(),
            'printed_by': request.user,
        }
        
        return render(request, 'dicom_viewer/print_report.html', context)
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return HttpResponse('Error generating report', status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def upload_dicom(request):
    """Handle DICOM file uploads"""
    try:
        user_profile = get_object_or_404(UserProfile, user=request.user)
        
        if 'files' not in request.FILES:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        uploaded_files = request.FILES.getlist('files')
        study = None
        
        for uploaded_file in uploaded_files:
            if not uploaded_file.name.lower().endswith('.dcm'):
                continue
            
            # Save file temporarily
            temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', uploaded_file.name)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Parse DICOM
            try:
                ds = pydicom.dcmread(temp_path)
                
                # Create or get study
                study, created = DicomStudy.objects.get_or_create(
                    study_instance_uid=ds.StudyInstanceUID,
                    defaults={
                        'patient_name': str(ds.PatientName) if hasattr(ds, 'PatientName') else 'Unknown',
                        'patient_id': ds.PatientID if hasattr(ds, 'PatientID') else 'Unknown',
                        'patient_birth_date': ds.PatientBirthDate if hasattr(ds, 'PatientBirthDate') else None,
                        'patient_sex': ds.PatientSex if hasattr(ds, 'PatientSex') else 'U',
                        'study_date': ds.StudyDate if hasattr(ds, 'StudyDate') else None,
                        'study_time': ds.StudyTime if hasattr(ds, 'StudyTime') else None,
                        'accession_number': ds.AccessionNumber if hasattr(ds, 'AccessionNumber') else '',
                        'study_description': ds.StudyDescription if hasattr(ds, 'StudyDescription') else '',
                        'modality': ds.Modality if hasattr(ds, 'Modality') else 'Unknown',
                        'facility': user_profile.facility,
                        'status': 'pending',
                    }
                )
                
                # Create or get series
                series, created = DicomSeries.objects.get_or_create(
                    study=study,
                    series_instance_uid=ds.SeriesInstanceUID,
                    defaults={
                        'series_number': int(ds.SeriesNumber) if hasattr(ds, 'SeriesNumber') else 0,
                        'series_description': ds.SeriesDescription if hasattr(ds, 'SeriesDescription') else '',
                        'modality': ds.Modality if hasattr(ds, 'Modality') else 'Unknown',
                    }
                )
                
                # Move file to permanent location
                final_dir = os.path.join(
                    settings.MEDIA_ROOT, 
                    'dicom', 
                    str(study.id), 
                    str(series.id)
                )
                os.makedirs(final_dir, exist_ok=True)
                final_path = os.path.join(final_dir, uploaded_file.name)
                os.rename(temp_path, final_path)
                
                # Create image record
                DicomImage.objects.create(
                    series=series,
                    sop_instance_uid=ds.SOPInstanceUID,
                    instance_number=int(ds.InstanceNumber) if hasattr(ds, 'InstanceNumber') else 0,
                    file_path=final_path,
                    image_position=','.join(map(str, ds.ImagePositionPatient)) if hasattr(ds, 'ImagePositionPatient') else '',
                    image_orientation=','.join(map(str, ds.ImageOrientationPatient)) if hasattr(ds, 'ImageOrientationPatient') else '',
                    pixel_spacing=','.join(map(str, ds.PixelSpacing)) if hasattr(ds, 'PixelSpacing') else '',
                    slice_thickness=float(ds.SliceThickness) if hasattr(ds, 'SliceThickness') else None,
                    window_width=int(ds.WindowWidth[0]) if hasattr(ds, 'WindowWidth') and ds.WindowWidth else None,
                    window_center=int(ds.WindowCenter[0]) if hasattr(ds, 'WindowCenter') and ds.WindowCenter else None,
                )
                
            except Exception as e:
                logger.error(f"Error parsing DICOM file {uploaded_file.name}: {e}")
                continue
        
        if study:
            # Create upload notification for radiologists/admins
            UploadNotification.objects.create(
                study=study,
                uploaded_by=request.user,
                message=f"New study uploaded: {study.patient_name}"
            )
            
            return JsonResponse({
                'success': True,
                'study_id': study.id,
                'message': 'Files uploaded successfully'
            })
        else:
            return JsonResponse({'error': 'No valid DICOM files found'}, status=400)
            
    except Exception as e:
        logger.error(f"Error uploading DICOM files: {e}")
        return JsonResponse({'error': 'Upload failed'}, status=500)


# Utility functions for DICOM processing
def get_dicom_pixel_array(file_path, window_width=None, window_center=None):
    """Extract and process pixel array from DICOM file"""
    ds = pydicom.dcmread(file_path)
    pixel_array = ds.pixel_array.astype(np.float64)
    
    # Apply rescale slope and intercept if available
    if hasattr(ds, 'RescaleSlope'):
        pixel_array = pixel_array * float(ds.RescaleSlope)
    if hasattr(ds, 'RescaleIntercept'):
        pixel_array = pixel_array + float(ds.RescaleIntercept)
    
    # Apply window/level if specified
    if window_width and window_center:
        img_min = window_center - window_width // 2
        img_max = window_center + window_width // 2
        pixel_array = np.clip(pixel_array, img_min, img_max)
        pixel_array = ((pixel_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
    
    return pixel_array