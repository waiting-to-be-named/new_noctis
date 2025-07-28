# dicom_viewer/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.views.generic import TemplateView, ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
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
    Facility, Report, WorklistEntry, AIAnalysis, Notification
)
from .serializers import DicomStudySerializer, DicomImageSerializer


def ensure_media_directories():
    """Ensure media directories exist"""
    media_root = default_storage.location
    dicom_dir = os.path.join(media_root, 'dicom_files')
    temp_dir = os.path.join(media_root, 'temp')
    
    for directory in [media_root, dicom_dir, temp_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")


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


# Admin functionality for facilities and radiologists
def is_admin(user):
    """Check if user is admin"""
    return user.is_superuser


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin access"""
    def test_func(self):
        return self.request.user.is_superuser


class FacilityListView(AdminRequiredMixin, ListView):
    """Admin view to list all facilities"""
    model = Facility
    template_name = 'admin/facility_list.html'
    context_object_name = 'facilities'
    paginate_by = 20


class FacilityCreateView(AdminRequiredMixin, CreateView):
    """Admin view to create new facility"""
    model = Facility
    template_name = 'admin/facility_form.html'
    fields = ['name', 'address', 'phone', 'email', 'letterhead_logo']
    success_url = reverse_lazy('viewer:facility_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Facility "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class FacilityUpdateView(AdminRequiredMixin, UpdateView):
    """Admin view to update facility"""
    model = Facility
    template_name = 'admin/facility_form.html'
    fields = ['name', 'address', 'phone', 'email', 'letterhead_logo']
    success_url = reverse_lazy('viewer:facility_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Facility "{form.instance.name}" updated successfully.')
        return super().form_valid(form)


class RadiologistListView(AdminRequiredMixin, ListView):
    """Admin view to list all radiologists"""
    model = User
    template_name = 'admin/radiologist_list.html'
    context_object_name = 'radiologists'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.filter(groups__name='Radiologists').distinct()


@login_required
@user_passes_test(is_admin)
def create_radiologist(request):
    """Admin view to create new radiologist"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'admin/radiologist_form.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        
        # Add to radiologists group
        radiologist_group, created = Group.objects.get_or_create(name='Radiologists')
        user.groups.add(radiologist_group)
        
        messages.success(request, f'Radiologist "{user.get_full_name()}" created successfully.')
        return redirect('viewer:radiologist_list')
    
    return render(request, 'admin/radiologist_form.html')


@csrf_exempt
@require_http_methods(['POST'])
def upload_dicom_files(request):
    """Handle DICOM file uploads with improved worklist integration"""
    try:
        # Ensure media directories exist
        ensure_media_directories()
        
        if 'files' not in request.FILES:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        files = request.FILES.getlist('files')
        uploaded_files = []
        study = None
        
        for file in files:
            try:
                # Validate file is a DICOM file
                if not file.name.lower().endswith(('.dcm', '.dicom')):
                    continue
                
                # Save file to proper DICOM directory
                file_path = default_storage.save(f'dicom_files/{file.name}', ContentFile(file.read()))
                
                # Read DICOM data
                try:
                    dicom_data = pydicom.dcmread(default_storage.path(file_path))
                except Exception as e:
                    print(f"Error reading DICOM file {file.name}: {e}")
                    # Clean up the saved file
                    default_storage.delete(file_path)
                    continue
                
                # Create/update study with facility association
                study_uid = str(dicom_data.get('StudyInstanceUID', ''))
                if not study_uid:
                    print(f"No StudyInstanceUID found in {file.name}")
                    default_storage.delete(file_path)
                    continue
                    
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
                            'accession_number': str(getattr(dicom_data, 'AccessionNumber', '')),
                            'referring_physician': str(getattr(dicom_data, 'ReferringPhysicianName', '')),
                        }
                    )
                    
                    # Create corresponding worklist entry
                    if created:
                        try:
                            WorklistEntry.objects.create(
                                patient_name=study.patient_name,
                                patient_id=study.patient_id,
                                accession_number=study.accession_number or f"ACC{study.id:06d}",
                                scheduled_station_ae_title="UPLOAD",
                                scheduled_procedure_step_start_date=study.study_date or datetime.now().date(),
                                scheduled_procedure_step_start_time=study.study_time or datetime.now().time(),
                                modality=study.modality,
                                scheduled_performing_physician=study.referring_physician or "Unknown",
                                procedure_description=study.study_description,
                                facility=study.facility or Facility.objects.first(),
                                study=study,
                                status='completed'
                            )
                        except Exception as e:
                            print(f"Error creating worklist entry: {e}")
                
                # If study was created, send notifications to radiologists
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
                
                # Create or get series
                series_uid = str(dicom_data.get('SeriesInstanceUID', ''))
                if not series_uid:
                    print(f"No SeriesInstanceUID found in {file.name}")
                    continue
                    
                series, created = DicomSeries.objects.get_or_create(
                    study=study,
                    series_instance_uid=series_uid,
                    defaults={
                        'series_number': int(dicom_data.get('SeriesNumber', 0)),
                        'series_description': str(getattr(dicom_data, 'SeriesDescription', '')),
                        'modality': str(dicom_data.Modality) if hasattr(dicom_data, 'Modality') else 'OT',
                    }
                )
                
                # Create image
                image_instance_uid = str(dicom_data.get('SOPInstanceUID', ''))
                if not image_instance_uid:
                    print(f"No SOPInstanceUID found in {file.name}")
                    continue
                    
                image, created = DicomImage.objects.get_or_create(
                    series=series,
                    sop_instance_uid=image_instance_uid,
                    defaults={
                        'image_number': int(dicom_data.get('InstanceNumber', 0)),
                        'file_path': file_path,
                        'rows': int(dicom_data.Rows) if hasattr(dicom_data, 'Rows') else 0,
                        'columns': int(dicom_data.Columns) if hasattr(dicom_data, 'Columns') else 0,
                        'bits_allocated': int(dicom_data.BitsAllocated) if hasattr(dicom_data, 'BitsAllocated') else 16,
                        'samples_per_pixel': int(dicom_data.SamplesPerPixel) if hasattr(dicom_data, 'SamplesPerPixel') else 1,
                        'photometric_interpretation': str(dicom_data.PhotometricInterpretation) if hasattr(dicom_data, 'PhotometricInterpretation') else 'MONOCHROME2',
                        'pixel_spacing': str(getattr(dicom_data, 'PixelSpacing', '')),
                        'slice_thickness': float(getattr(dicom_data, 'SliceThickness', 0)),
                        'window_center': str(getattr(dicom_data, 'WindowCenter', '')),
                        'window_width': str(getattr(dicom_data, 'WindowWidth', '')),
                    }
                )
                
                if created:
                    uploaded_files.append(file.name)
                
            except Exception as e:
                print(f"Error processing file {file.name}: {e}")
                if 'file_path' in locals():
                    try:
                        default_storage.delete(file_path)
                    except:
                        pass
                continue
        
        if not uploaded_files:
            return JsonResponse({'error': 'No valid DICOM files were uploaded'}, status=400)
        
        return JsonResponse({
            'message': f'Uploaded {len(uploaded_files)} files successfully',
            'uploaded_files': uploaded_files,
            'study_id': study.id if study else None
        })
        
    except Exception as e:
        print(f"Unexpected error in upload_dicom_files: {e}")
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def upload_dicom_folder(request):
    """Handle DICOM folder uploads"""
    try:
        if 'files' not in request.FILES:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        files = request.FILES.getlist('files')
        uploaded_files = []
        study = None
        
        # Group files by study
        studies = {}
        
        for file in files:
            try:
                # Validate file is a DICOM file
                if not file.name.lower().endswith(('.dcm', '.dicom')):
                    continue
                
                # Save file to proper DICOM directory
                file_path = default_storage.save(f'dicom_files/{file.name}', ContentFile(file.read()))
                
                # Read DICOM data
                try:
                    dicom_data = pydicom.dcmread(default_storage.path(file_path))
                except Exception as e:
                    print(f"Error reading DICOM file {file.name}: {e}")
                    default_storage.delete(file_path)
                    continue
                
                # Get study UID
                study_uid = str(dicom_data.get('StudyInstanceUID', ''))
                if not study_uid:
                    print(f"No StudyInstanceUID found in {file.name}")
                    default_storage.delete(file_path)
                    continue
                
                # Group by study
                if study_uid not in studies:
                    studies[study_uid] = {
                        'files': [],
                        'dicom_data': [],
                        'file_paths': []
                    }
                
                studies[study_uid]['files'].append(file.name)
                studies[study_uid]['dicom_data'].append(dicom_data)
                studies[study_uid]['file_paths'].append(file_path)
                
            except Exception as e:
                print(f"Error processing file {file.name}: {e}")
                if 'file_path' in locals():
                    try:
                        default_storage.delete(file_path)
                    except:
                        pass
                continue
        
        # Process each study
        for study_uid, study_data in studies.items():
            try:
                # Create study from first file
                first_dicom = study_data['dicom_data'][0]
                
                study, created = DicomStudy.objects.get_or_create(
                    study_instance_uid=study_uid,
                    defaults={
                        'patient_name': str(first_dicom.PatientName) if hasattr(first_dicom, 'PatientName') else 'Unknown',
                        'patient_id': str(first_dicom.PatientID) if hasattr(first_dicom, 'PatientID') else 'Unknown',
                        'study_date': parse_dicom_date(getattr(first_dicom, 'StudyDate', None)),
                        'study_time': parse_dicom_time(getattr(first_dicom, 'StudyTime', None)),
                        'study_description': str(getattr(first_dicom, 'StudyDescription', '')),
                        'modality': str(first_dicom.Modality) if hasattr(first_dicom, 'Modality') else 'OT',
                        'institution_name': str(getattr(first_dicom, 'InstitutionName', '')),
                        'uploaded_by': request.user if request.user.is_authenticated else None,
                        'facility': request.user.facility_staff.facility if hasattr(request.user, 'facility_staff') else None,
                        'accession_number': str(getattr(first_dicom, 'AccessionNumber', '')),
                        'referring_physician': str(getattr(first_dicom, 'ReferringPhysicianName', '')),
                    }
                )
                
                # Create worklist entry if study was created
                if created:
                    try:
                        WorklistEntry.objects.create(
                            patient_name=study.patient_name,
                            patient_id=study.patient_id,
                            accession_number=study.accession_number or f"ACC{study.id:06d}",
                            scheduled_station_ae_title="UPLOAD",
                            scheduled_procedure_step_start_date=study.study_date or datetime.now().date(),
                            scheduled_procedure_step_start_time=study.study_time or datetime.now().time(),
                            modality=study.modality,
                            scheduled_performing_physician=study.referring_physician or "Unknown",
                            procedure_description=study.study_description,
                            facility=study.facility or Facility.objects.first(),
                            study=study,
                            status='completed'
                        )
                    except Exception as e:
                        print(f"Error creating worklist entry: {e}")
                
                # Process each file in the study
                for i, dicom_data in enumerate(study_data['dicom_data']):
                    try:
                        # Create or get series
                        series_uid = str(dicom_data.get('SeriesInstanceUID', ''))
                        if not series_uid:
                            continue
                            
                        series, created = DicomSeries.objects.get_or_create(
                            study=study,
                            series_instance_uid=series_uid,
                            defaults={
                                'series_number': int(dicom_data.get('SeriesNumber', 0)),
                                'series_description': str(getattr(dicom_data, 'SeriesDescription', '')),
                                'modality': str(dicom_data.Modality) if hasattr(dicom_data, 'Modality') else 'OT',
                            }
                        )
                        
                        # Create image
                        image_instance_uid = str(dicom_data.get('SOPInstanceUID', ''))
                        if not image_instance_uid:
                            continue
                            
                        image, created = DicomImage.objects.get_or_create(
                            series=series,
                            sop_instance_uid=image_instance_uid,
                            defaults={
                                'image_number': int(dicom_data.get('InstanceNumber', 0)),
                                'file_path': study_data['file_paths'][i],
                                'rows': int(dicom_data.Rows) if hasattr(dicom_data, 'Rows') else 0,
                                'columns': int(dicom_data.Columns) if hasattr(dicom_data, 'Columns') else 0,
                                'bits_allocated': int(dicom_data.BitsAllocated) if hasattr(dicom_data, 'BitsAllocated') else 16,
                                'samples_per_pixel': int(dicom_data.SamplesPerPixel) if hasattr(dicom_data, 'SamplesPerPixel') else 1,
                                'photometric_interpretation': str(dicom_data.PhotometricInterpretation) if hasattr(dicom_data, 'PhotometricInterpretation') else 'MONOCHROME2',
                                'pixel_spacing': str(getattr(dicom_data, 'PixelSpacing', '')),
                                'slice_thickness': float(dicom_data.SliceThickness) if hasattr(dicom_data, 'SliceThickness') else 0,
                                'window_center': str(dicom_data.WindowCenter) if hasattr(dicom_data, 'WindowCenter') else '',
                                'window_width': str(dicom_data.WindowWidth) if hasattr(dicom_data, 'WindowWidth') else '',
                            }
                        )
                        
                        if created:
                            uploaded_files.append(study_data['files'][i])
                            
                    except Exception as e:
                        print(f"Error processing image in study {study_uid}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error processing study {study_uid}: {e}")
                continue
        
        if not uploaded_files:
            return JsonResponse({'error': 'No valid DICOM files were uploaded'}, status=400)
        
        return JsonResponse({
            'message': f'Uploaded {len(uploaded_files)} files from {len(studies)} study(ies)',
            'uploaded_files': uploaded_files,
            'study_id': study.id if study else None
        })
        
    except Exception as e:
        print(f"Unexpected error in upload_dicom_folder: {e}")
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@api_view(['GET'])
def get_studies(request):
    """Get all studies"""
    studies = DicomStudy.objects.all()[:20]  # Limit to recent studies
    serializer = DicomStudySerializer(studies, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_study_images(request, study_id):
    """Get all images for a study"""
    try:
        study = DicomStudy.objects.get(id=study_id)
        images = DicomImage.objects.filter(series__study=study).order_by('series__series_number', 'instance_number')
        
        images_data = []
        for image in images:
            image_data = {
                'id': image.id,
                'instance_number': image.instance_number,
                'series_number': image.series.series_number,
                'series_description': image.series.series_description,
                'rows': image.rows,
                'columns': image.columns,
                'pixel_spacing_x': image.pixel_spacing_x,
                'pixel_spacing_y': image.pixel_spacing_y,
                'slice_thickness': image.slice_thickness,
                'window_width': image.window_width,
                'window_center': image.window_center,
            }
            images_data.append(image_data)
        
        return Response({
            'study': {
                'id': study.id,
                'patient_name': study.patient_name,
                'study_date': study.study_date,
                'modality': study.modality,
                'study_description': study.study_description,
            },
            'images': images_data
        })
    except DicomStudy.DoesNotExist:
        return Response({'error': 'Study not found'}, status=404)


@api_view(['GET'])
def get_image_data(request, image_id):
    """Get processed image data"""
    try:
        image = DicomImage.objects.get(id=image_id)
        
        # Get query parameters
        window_width = request.GET.get('window_width', image.window_width)
        window_level = request.GET.get('window_level', image.window_center)
        inverted = request.GET.get('inverted', 'false').lower() == 'true'
        
        # Convert to appropriate types
        if window_width:
            window_width = float(window_width)
        if window_level:
            window_level = float(window_level)
        
        # Get processed image
        image_base64 = image.get_processed_image_base64(window_width, window_level, inverted)
        
        if image_base64:
            return Response({
                'image_data': image_base64,
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
        else:
            return Response({'error': 'Could not process image'}, status=500)
            
    except DicomImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=404)


@csrf_exempt
@require_http_methods(['POST'])
def save_measurement(request):
    """Save measurement with improved calculations"""
    try:
        data = json.loads(request.body)
        image = DicomImage.objects.get(id=data['image_id'])
        
        measurement_type = data.get('type', 'line')
        coordinates = data['coordinates']
        
        # Calculate measurement value based on type
        if measurement_type == 'line':
            # Line distance measurement
            start = coordinates[0]
            end = coordinates[1]
            pixel_distance = np.sqrt((end['x'] - start['x'])**2 + (end['y'] - start['y'])**2)
            
            # Convert to real-world units if pixel spacing available
            if image.pixel_spacing_x and image.pixel_spacing_y:
                avg_spacing = (image.pixel_spacing_x + image.pixel_spacing_y) / 2
                real_distance = pixel_distance * avg_spacing  # in mm
                unit = data.get('unit', 'mm')
                
                if unit == 'cm':
                    value = real_distance / 10.0
                else:
                    value = real_distance
            else:
                value = pixel_distance
                unit = 'px'
                
        elif measurement_type == 'area':
            # Area measurement for polygons
            points = coordinates
            if len(points) >= 3:
                # Calculate area using shoelace formula
                area_px = 0.5 * abs(sum(
                    points[i]['x'] * (points[(i + 1) % len(points)]['y'] - points[(i - 1) % len(points)]['y'])
                    for i in range(len(points))
                ))
                
                if image.pixel_spacing_x and image.pixel_spacing_y:
                    pixel_area_mm2 = image.pixel_spacing_x * image.pixel_spacing_y
                    value = area_px * pixel_area_mm2  # in mm²
                    unit = 'mm²'
                else:
                    value = area_px
                    unit = 'px²'
            else:
                value = 0
                unit = 'px²'
                
        elif measurement_type == 'volume':
            # Volume measurement for 3D regions
            # This is a simplified calculation - would need slice data for accurate volume
            area = data.get('area', 0)  # Area from contour
            if image.slice_thickness and image.pixel_spacing_x and image.pixel_spacing_y:
                pixel_area_mm2 = image.pixel_spacing_x * image.pixel_spacing_y
                volume_mm3 = area * pixel_area_mm2 * image.slice_thickness
                unit = data.get('unit', 'mm³')
                
                if unit == 'cm³':
                    value = volume_mm3 / 1000.0  # Convert mm³ to cm³
                else:
                    value = volume_mm3
            else:
                value = area * (image.slice_thickness or 1)
                unit = 'px³'
                
        elif measurement_type == 'angle':
            # Angle measurement
            if len(coordinates) >= 3:
                p1, vertex, p2 = coordinates[:3]
                
                # Calculate vectors
                v1 = np.array([p1['x'] - vertex['x'], p1['y'] - vertex['y']])
                v2 = np.array([p2['x'] - vertex['x'], p2['y'] - vertex['y']])
                
                # Calculate angle
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                angle_rad = np.arccos(np.clip(cos_angle, -1.0, 1.0))
                value = np.degrees(angle_rad)
                unit = '°'
            else:
                value = 0
                unit = '°'
        else:
            value = data.get('value', 0)
            unit = data.get('unit', 'px')
        
        # Save measurement
        measurement = Measurement.objects.create(
            image=image,
            measurement_type=measurement_type,
            coordinates=coordinates,
            value=value,
            unit=unit,
            notes=data.get('notes', ''),
            created_by=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'id': measurement.id,
            'value': value,
            'unit': unit,
            'type': measurement_type
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['POST'])
def measure_hu(request):
    """Measure Hounsfield Units with proper radiological reference data"""
    try:
        data = json.loads(request.body)
        image = DicomImage.objects.get(id=data['image_id'])
        
        # Load DICOM data
        dicom_data = image.load_dicom_data()
        if not dicom_data:
            return JsonResponse({'error': 'Could not load DICOM data'}, status=400)
        
        pixel_array = image.get_pixel_array()
        if pixel_array is None:
            return JsonResponse({'error': 'Could not get pixel data'}, status=400)
        
        # Get ellipse coordinates
        x0, y0 = int(data['x0']), int(data['y0'])
        x1, y1 = int(data['x1']), int(data['y1'])
        
        # Create ellipse mask
        center_x = (x0 + x1) / 2
        center_y = (y0 + y1) / 2
        a = abs(x1 - x0) / 2  # semi-major axis
        b = abs(y1 - y0) / 2  # semi-minor axis
        
        # Create coordinate grids
        y_coords, x_coords = np.ogrid[:pixel_array.shape[0], :pixel_array.shape[1]]
        
        # Ellipse equation: ((x-cx)/a)² + ((y-cy)/b)² <= 1
        mask = ((x_coords - center_x) / a) ** 2 + ((y_coords - center_y) / b) ** 2 <= 1
        
        # Extract pixel values within ellipse
        roi_pixels = pixel_array[mask]
        
        if len(roi_pixels) == 0:
            return JsonResponse({'error': 'No pixels in ROI'}, status=400)
        
        # Convert to Hounsfield Units
        # Check if we have rescale slope and intercept
        rescale_slope = getattr(dicom_data, 'RescaleSlope', 1)
        rescale_intercept = getattr(dicom_data, 'RescaleIntercept', 0)
        
        # Apply rescaling to get HU values
        hu_values = roi_pixels * rescale_slope + rescale_intercept
        
        # Calculate statistics
        mean_hu = float(np.mean(hu_values))
        min_hu = float(np.min(hu_values))
        max_hu = float(np.max(hu_values))
        std_hu = float(np.std(hu_values))
        
        # Radiological interpretation based on HU values
        interpretation = get_hu_interpretation(mean_hu)
        
        # Save measurement
        measurement = Measurement.objects.create(
            image=image,
            measurement_type='ellipse',
            coordinates=[{'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1}],
            value=mean_hu,
            unit='HU',
            hounsfield_mean=mean_hu,
            hounsfield_min=min_hu,
            hounsfield_max=max_hu,
            hounsfield_std=std_hu,
            notes=f"Interpretation: {interpretation}",
            created_by=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'mean_hu': mean_hu,
            'min_hu': min_hu,
            'max_hu': max_hu,
            'std_hu': std_hu,
            'pixel_count': len(roi_pixels),
            'interpretation': interpretation,
            'measurement_id': measurement.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def get_hu_interpretation(hu_value):
    """
    Provide radiological interpretation based on Hounsfield Unit values
    Based on standard radiological reference values
    """
    if hu_value < -900:
        return "Air/Gas"
    elif -900 <= hu_value < -500:
        return "Lung tissue"
    elif -500 <= hu_value < -100:
        return "Fat tissue"
    elif -100 <= hu_value < -50:
        return "Fat/Soft tissue interface"
    elif -50 <= hu_value < 0:
        return "Soft tissue (low density)"
    elif 0 <= hu_value < 20:
        return "Water/CSF"
    elif 20 <= hu_value < 40:
        return "Soft tissue (muscle)"
    elif 40 <= hu_value < 80:
        return "Soft tissue (liver, spleen)"
    elif 80 <= hu_value < 120:
        return "Soft tissue (kidney)"
    elif 120 <= hu_value < 200:
        return "Soft tissue (dense)"
    elif 200 <= hu_value < 400:
        return "Calcification/Contrast"
    elif 400 <= hu_value < 1000:
        return "Bone (cancellous)"
    elif 1000 <= hu_value < 2000:
        return "Bone (cortical)"
    else:
        return "Metal/Dense material"


@csrf_exempt
@require_http_methods(['POST'])
def save_annotation(request):
    """Save annotation"""
    try:
        data = json.loads(request.body)
        image = DicomImage.objects.get(id=data['image_id'])
        
        annotation = Annotation.objects.create(
            image=image,
            x_coordinate=data['x'],
            y_coordinate=data['y'],
            text=data['text'],
            created_by=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({'id': annotation.id})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def get_measurements(request, image_id):
    """Get measurements for an image"""
    try:
        measurements = Measurement.objects.filter(image_id=image_id)
        data = []
        
        for m in measurements:
            measurement_data = {
                'id': m.id,
                'type': m.measurement_type,
                'coordinates': m.coordinates,
                'value': m.value,
                'unit': m.unit,
                'notes': m.notes,
                'created_at': m.created_at.isoformat()
            }
            
            # Add HU-specific data if available
            if m.measurement_type == 'ellipse' and m.hounsfield_mean is not None:
                measurement_data.update({
                    'hounsfield_mean': m.hounsfield_mean,
                    'hounsfield_min': m.hounsfield_min,
                    'hounsfield_max': m.hounsfield_max,
                    'hounsfield_std': m.hounsfield_std,
                })
            
            data.append(measurement_data)
        
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
def get_annotations(request, image_id):
    """Get annotations for an image"""
    try:
        annotations = Annotation.objects.filter(image_id=image_id)
        data = [{
            'id': a.id,
            'x': a.x_coordinate,
            'y': a.y_coordinate,
            'text': a.text,
            'font_size': a.font_size,
            'color': a.color,
            'created_at': a.created_at.isoformat()
        } for a in annotations]
        
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['DELETE'])
def clear_measurements(request, image_id):
    """Clear all measurements and annotations for an image"""
    try:
        Measurement.objects.filter(image_id=image_id).delete()
        Annotation.objects.filter(image_id=image_id).delete()
        return JsonResponse({'message': 'Measurements cleared'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['POST'])
def perform_ai_analysis(request, image_id):
    """Perform AI analysis on image (placeholder implementation)"""
    try:
        image = DicomImage.objects.get(id=image_id)
        
        # This is a placeholder - would integrate with actual AI models
        # For now, return mock results
        mock_results = {
            'analysis_type': 'anomaly_detection',
            'summary': 'AI analysis completed. No significant abnormalities detected.',
            'confidence_score': 0.85,
            'findings': [
                {
                    'type': 'Normal structure',
                    'location': {'x': 100, 'y': 150},
                    'size': 25,
                    'confidence': 0.9
                }
            ],
            'highlighted_regions': [
                {'x': 90, 'y': 140, 'width': 20, 'height': 20, 'type': 'normal'}
            ]
        }
        
        # Save AI analysis result
        ai_analysis = AIAnalysis.objects.create(
            image=image,
            analysis_type='anomaly_detection',
            findings=mock_results['findings'],
            summary=mock_results['summary'],
            confidence_score=mock_results['confidence_score'],
            highlighted_regions=mock_results['highlighted_regions']
        )
        
        return JsonResponse(mock_results)
        
    except DicomImage.DoesNotExist:
        return JsonResponse({'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def get_3d_reconstruction(request, series_id):
    """Get 3D reconstruction data (placeholder implementation)"""
    try:
        series = DicomSeries.objects.get(id=series_id)
        reconstruction_type = request.GET.get('type', 'mpr')
        
        # This is a placeholder - would implement actual 3D reconstruction
        mock_data = {
            'type': reconstruction_type,
            'data_url': '/static/images/3d_placeholder.png',
            'message': f'{reconstruction_type.upper()} reconstruction generated'
        }
        
        return Response(mock_data)
        
    except DicomSeries.DoesNotExist:
        return Response({'error': 'Series not found'}, status=404)


# Utility functions
def parse_dicom_date(date_str):
    """Parse DICOM date string to Python date"""
    if date_str:
        try:
            return datetime.strptime(str(date_str), '%Y%m%d').date()
        except:
            pass
    return None


def parse_dicom_time(time_str):
    """Parse DICOM time string to Python time"""
    if time_str:
        try:
            # Handle various time formats
            time_str = str(time_str)[:6]  # Take first 6 digits (HHMMSS)
            return datetime.strptime(time_str, '%H%M%S').time()
        except:
            pass
    return None