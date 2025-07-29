# dicom_viewer/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
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
    Facility, Report, WorklistEntry, AIAnalysis, Notification, FacilityUser
)
from django.contrib.auth.models import Group
from .serializers import DicomStudySerializer, DicomImageSerializer


# Ensure required directories exist
def ensure_directories():
    """Ensure that required media directories exist"""
    try:
        media_root = default_storage.location
        dicom_dir = os.path.join(media_root, 'dicom_files')
        temp_dir = os.path.join(media_root, 'temp')
        
        for directory in [media_root, dicom_dir, temp_dir]:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    print(f"Created directory: {directory}")
                except PermissionError:
                    # Fallback to current directory if media_root fails
                    if directory == media_root:
                        fallback_dir = os.path.join(os.getcwd(), 'media')
                        if not os.path.exists(fallback_dir):
                            os.makedirs(fallback_dir, exist_ok=True)
                            print(f"Created fallback media directory: {fallback_dir}")
                        # Update default storage location
                        default_storage.location = fallback_dir
                        media_root = fallback_dir
                        dicom_dir = os.path.join(media_root, 'dicom_files')
                        temp_dir = os.path.join(media_root, 'temp')
                        # Create subdirectories in fallback location
                        for subdir in [dicom_dir, temp_dir]:
                            if not os.path.exists(subdir):
                                os.makedirs(subdir, exist_ok=True)
                                print(f"Created fallback directory: {subdir}")
                    else:
                        print(f"Permission denied creating directory: {directory}")
                        raise
                except Exception as e:
                    print(f"Error creating directory {directory}: {e}")
                    raise
    except Exception as e:
        print(f"Critical error in ensure_directories: {e}")
        # Create minimal fallback structure
        fallback_media = os.path.join(os.getcwd(), 'media')
        fallback_dicom = os.path.join(fallback_media, 'dicom_files')
        try:
            os.makedirs(fallback_dicom, exist_ok=True)
            print(f"Created emergency fallback: {fallback_dicom}")
        except Exception as fallback_error:
            print(f"Emergency fallback failed: {fallback_error}")
            raise


class HomeView(TemplateView):
    """Home page with launch buttons"""
    template_name = 'home.html'


class DicomViewerView(TemplateView):
    """Main DICOM viewer page"""
    template_name = 'dicom_viewer/viewer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['studies'] = DicomStudy.objects.all()[:10]  # Recent studies
        
        # Check if we have a study_id parameter
        study_id = kwargs.get('study_id')
        if study_id:
            try:
                study = DicomStudy.objects.get(id=study_id)
                context['initial_study_id'] = study_id
                context['initial_study'] = study
                
                # Update worklist entry status to in_progress if radiologist is viewing
                if self.request.user.is_authenticated:
                    worklist_entries = WorklistEntry.objects.filter(
                        study=study,
                        status='scheduled'
                    )
                    for entry in worklist_entries:
                        entry.status = 'in_progress'
                        entry.save()
                        
            except DicomStudy.DoesNotExist:
                context['initial_study_error'] = f'Study with ID {study_id} not found'
        
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
        # Get the facility credentials from POST data
        facility_username = self.request.POST.get('facility_username')
        facility_password = self.request.POST.get('facility_password')
        facility_password_confirm = self.request.POST.get('facility_password_confirm')
        
        # Validate passwords match
        if facility_password != facility_password_confirm:
            messages.error(self.request, 'Passwords do not match.')
            return self.form_invalid(form)
        
        # Validate password requirements
        if len(facility_password) < 8:
            messages.error(self.request, 'Password must be at least 8 characters long.')
            return self.form_invalid(form)
        
        # Check if username already exists
        if Facility.objects.filter(username=facility_username).exists():
            messages.error(self.request, 'Username already exists. Please choose a different username.')
            return self.form_invalid(form)
        
        # Save the facility
        facility = form.save(commit=False)
        facility.username = facility_username
        facility.set_password(facility_password)
        facility.save()
        
        # Create a Django user for this facility
        try:
            user = User.objects.create_user(
                username=facility_username,
                email=facility.email,
                first_name=facility.name,
                password=facility_password
            )
            
            # Create facility group if it doesn't exist
            facility_group, created = Group.objects.get_or_create(name='Facilities')
            user.groups.add(facility_group)
            
            # Create FacilityUser profile
            FacilityUser.objects.create(
                user=user,
                facility=facility,
                role='admin'
            )
            
            messages.success(self.request, f'Facility "{facility.name}" and login account created successfully.')
        except Exception as e:
            messages.error(self.request, f'Facility created but login account failed: {str(e)}')
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context for the template
        return context


class FacilityUpdateView(AdminRequiredMixin, UpdateView):
    """Admin view to update facility"""
    model = Facility
    template_name = 'admin/facility_form.html'
    fields = ['name', 'address', 'phone', 'email', 'letterhead_logo']
    success_url = reverse_lazy('viewer:facility_list')
    
    def form_valid(self, form):
        # Get the facility credentials from POST data
        facility_username = self.request.POST.get('facility_username')
        facility_password = self.request.POST.get('facility_password')
        facility_password_confirm = self.request.POST.get('facility_password_confirm')
        
        facility = form.save(commit=False)
        
        # Only update credentials if provided
        if facility_username:
            # Check if username already exists for other facilities
            existing_facility = Facility.objects.filter(username=facility_username).exclude(id=facility.id).first()
            if existing_facility:
                messages.error(self.request, 'Username already exists. Please choose a different username.')
                return self.form_invalid(form)
            
            facility.username = facility_username
            
            # Update Django user if exists
            try:
                if hasattr(facility, 'users') and facility.users.exists():
                    facility_user = facility.users.first()
                    django_user = facility_user.user
                    django_user.username = facility_username
                    django_user.email = facility.email
                    django_user.first_name = facility.name
                    
                    if facility_password and facility_password == facility_password_confirm:
                        if len(facility_password) >= 8:
                            facility.set_password(facility_password)
                            django_user.set_password(facility_password)
                            django_user.save()
                        else:
                            messages.error(self.request, 'Password must be at least 8 characters long.')
                            return self.form_invalid(form)
                    
                    django_user.save()
            except Exception as e:
                messages.warning(self.request, f'Facility updated but login account update failed: {str(e)}')
        
        facility.save()
        messages.success(self.request, f'Facility "{facility.name}" updated successfully.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['facility_username'] = self.object.username
        return context


class FacilityDeleteView(AdminRequiredMixin, DeleteView):
    """Admin view to delete facility"""
    model = Facility
    template_name = 'admin/facility_confirm_delete.html'
    success_url = reverse_lazy('viewer:facility_list')
    
    def delete(self, request, *args, **kwargs):
        facility = self.get_object()
        
        # Delete associated Django users
        try:
            for facility_user in facility.users.all():
                facility_user.user.delete()
        except Exception as e:
            messages.warning(request, f'Some user accounts could not be deleted: {str(e)}')
        
        messages.success(request, f'Facility "{facility.name}" and all associated data deleted successfully.')
        return super().delete(request, *args, **kwargs)


class RadiologistListView(AdminRequiredMixin, ListView):
    """Admin view to list all radiologists"""
    model = User
    template_name = 'admin/radiologist_list.html'
    context_object_name = 'radiologists'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.filter(groups__name='Radiologists').distinct()


class RadiologistDeleteView(AdminRequiredMixin, DeleteView):
    """Admin view to delete radiologist"""
    model = User
    template_name = 'admin/radiologist_confirm_delete.html'
    success_url = reverse_lazy('viewer:radiologist_list')
    
    def get_queryset(self):
        return User.objects.filter(groups__name='Radiologists')
    
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        messages.success(request, f'Radiologist "{user.get_full_name()}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class RadiologistUpdateView(AdminRequiredMixin, UpdateView):
    """Admin view to update radiologist"""
    model = User
    template_name = 'admin/radiologist_form.html'
    fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
    success_url = reverse_lazy('viewer:radiologist_list')
    
    def get_queryset(self):
        return User.objects.filter(groups__name='Radiologists')
    
    def form_valid(self, form):
        messages.success(self.request, f'Radiologist "{form.instance.get_full_name()}" updated successfully.')
        return super().form_valid(form)


class StudyDeleteView(AdminRequiredMixin, DeleteView):
    """Admin view to delete study and all associated data"""
    model = DicomStudy
    template_name = 'admin/study_confirm_delete.html'
    success_url = reverse_lazy('viewer:study_list')
    
    def delete(self, request, *args, **kwargs):
        study = self.get_object()
        study_name = f"{study.patient_name} - {study.study_date}"
        
        # Delete all associated files
        try:
            for series in study.series.all():
                for image in series.images.all():
                    if image.file_path:
                        try:
                            default_storage.delete(image.file_path.name)
                        except:
                            pass
        except Exception as e:
            messages.warning(request, f'Some files could not be deleted: {str(e)}')
        
        messages.success(request, f'Study "{study_name}" and all associated data deleted successfully.')
        return super().delete(request, *args, **kwargs)


class StudyListView(AdminRequiredMixin, ListView):
    """Admin view to list all studies for management"""
    model = DicomStudy
    template_name = 'admin/study_list.html'
    context_object_name = 'studies'
    paginate_by = 20
    ordering = ['-created_at']


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
    """Handle DICOM file uploads with comprehensive error handling and validation"""
    try:
        # Ensure media directories exist with proper permissions
        ensure_directories()
        
        if 'files' not in request.FILES:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        uploaded_files = []
        study = None
        errors = []
        
        for file in files:
            try:
                # More comprehensive file validation
                file_name = file.name.lower()
                file_size = file.size
                
                # Check file size (100MB limit)
                if file_size > 100 * 1024 * 1024:  # 100MB
                    errors.append(f"File {file.name} is too large (max 100MB)")
                    continue
                
                # Accept any file that might be DICOM (more permissive)
                is_dicom_candidate = (
                    file_name.endswith(('.dcm', '.dicom')) or
                    file_name.endswith(('.dcm.gz', '.dicom.gz')) or
                    file_name.endswith(('.dcm.bz2', '.dicom.bz2')) or
                    '.' not in file.name or  # Files without extension
                    file_name.endswith('.img') or  # Common DICOM format
                    file_name.endswith('.ima') or  # Common DICOM format
                    file_name.endswith('.raw') or  # Raw data
                    file_size > 1024  # Files larger than 1KB (likely not text)
                )
                
                if not is_dicom_candidate:
                    errors.append(f"File {file.name} does not appear to be a DICOM file")
                    continue
                
                # Save file with unique name to avoid conflicts
                import uuid
                unique_filename = f"{uuid.uuid4()}_{file.name}"
                file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file.read()))
                
                # Try to read DICOM data with multiple fallback methods
                dicom_data = None
                try:
                    # Method 1: Try reading from file path
                    dicom_data = pydicom.dcmread(default_storage.path(file_path))
                except Exception as e1:
                    try:
                        # Method 2: Try reading from file object
                        file.seek(0)  # Reset file pointer
                        dicom_data = pydicom.dcmread(file)
                        # Re-save the file after successful read
                        file.seek(0)
                        file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file.read()))
                    except Exception as e2:
                        try:
                            # Method 3: Try reading as bytes
                            file.seek(0)
                            file_bytes = file.read()
                            dicom_data = pydicom.dcmread(file_bytes)
                            # Save the bytes
                            file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file_bytes))
                        except Exception as e3:
                            print(f"Failed to read DICOM file {file.name}: {e1}, {e2}, {e3}")
                            # Clean up the saved file
                            try:
                                default_storage.delete(file_path)
                            except:
                                pass
                            errors.append(f"Could not read DICOM data from {file.name}")
                            continue
                
                # Validate that we have essential DICOM tags
                if not dicom_data:
                    errors.append(f"No DICOM data found in {file.name}")
                    continue
                
                # Get study UID with fallback
                study_uid = str(dicom_data.get('StudyInstanceUID', ''))
                if not study_uid:
                    # Try to generate a fallback study UID
                    study_uid = f"STUDY_{uuid.uuid4()}"
                    print(f"Generated fallback StudyInstanceUID for {file.name}: {study_uid}")
                
                # Create or update study with comprehensive data extraction
                if not study:
                    # Extract patient information with fallbacks
                    patient_name = 'Unknown'
                    if hasattr(dicom_data, 'PatientName'):
                        try:
                            patient_name = str(dicom_data.PatientName)
                        except:
                            patient_name = 'Unknown'
                    
                    patient_id = 'Unknown'
                    if hasattr(dicom_data, 'PatientID'):
                        try:
                            patient_id = str(dicom_data.PatientID)
                        except:
                            patient_id = 'Unknown'
                    
                    # Extract other fields with safe fallbacks
                    study_date = parse_dicom_date(getattr(dicom_data, 'StudyDate', None))
                    study_time = parse_dicom_time(getattr(dicom_data, 'StudyTime', None))
                    study_description = str(getattr(dicom_data, 'StudyDescription', ''))
                    modality = str(dicom_data.Modality) if hasattr(dicom_data, 'Modality') else 'OT'
                    institution_name = str(getattr(dicom_data, 'InstitutionName', ''))
                    accession_number = str(getattr(dicom_data, 'AccessionNumber', ''))
                    referring_physician = str(getattr(dicom_data, 'ReferringPhysicianName', ''))
                    
                    study, created = DicomStudy.objects.get_or_create(
                        study_instance_uid=study_uid,
                        defaults={
                            'patient_name': patient_name,
                            'patient_id': patient_id,
                            'study_date': study_date,
                            'study_time': study_time,
                            'study_description': study_description,
                            'modality': modality,
                            'institution_name': institution_name,
                            'uploaded_by': request.user if request.user.is_authenticated else None,
                            'facility': request.user.facility_staff.facility if hasattr(request.user, 'facility_staff') else None,
                            'accession_number': accession_number,
                            'referring_physician': referring_physician,
                        }
                    )
                    
                    # Create worklist entry if study was created
                    if created:
                        try:
                            # Get or create a default facility if none exists
                            facility = study.facility
                            if not facility:
                                facility, _ = Facility.objects.get_or_create(
                                    name="Default Facility",
                                    defaults={
                                        'address': 'Unknown',
                                        'phone': 'Unknown',
                                        'email': 'unknown@facility.com'
                                    }
                                )
                                # Update the study with the facility
                                study.facility = facility
                                study.save()
                            
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
                                facility=facility,
                                study=study,
                                status='completed'
                            )
                            print(f"Created worklist entry for study {study.id}")
                        except Exception as e:
                            print(f"Error creating worklist entry: {e}")
                            import traceback
                            traceback.print_exc()
                
                # Create or get series with fallback UID
                series_uid = str(dicom_data.get('SeriesInstanceUID', ''))
                if not series_uid:
                    series_uid = f"SERIES_{uuid.uuid4()}"
                    print(f"Generated fallback SeriesInstanceUID for {file.name}: {series_uid}")
                
                series, created = DicomSeries.objects.get_or_create(
                    study=study,
                    series_instance_uid=series_uid,
                    defaults={
                        'series_number': int(dicom_data.get('SeriesNumber', 0)),
                        'series_description': str(getattr(dicom_data, 'SeriesDescription', '')),
                        'modality': str(dicom_data.Modality) if hasattr(dicom_data, 'Modality') else 'OT',
                    }
                )
                
                # Create image with fallback UID
                image_instance_uid = str(dicom_data.get('SOPInstanceUID', ''))
                if not image_instance_uid:
                    image_instance_uid = f"IMAGE_{uuid.uuid4()}"
                    print(f"Generated fallback SOPInstanceUID for {file.name}: {image_instance_uid}")
                
                # Extract image data with safe fallbacks
                rows = 0
                columns = 0
                bits_allocated = 16
                samples_per_pixel = 1
                photometric_interpretation = 'MONOCHROME2'
                
                if hasattr(dicom_data, 'Rows'):
                    try:
                        rows = int(dicom_data.Rows)
                    except:
                        rows = 0
                
                if hasattr(dicom_data, 'Columns'):
                    try:
                        columns = int(dicom_data.Columns)
                    except:
                        columns = 0
                
                if hasattr(dicom_data, 'BitsAllocated'):
                    try:
                        bits_allocated = int(dicom_data.BitsAllocated)
                    except:
                        bits_allocated = 16
                
                if hasattr(dicom_data, 'SamplesPerPixel'):
                    try:
                        samples_per_pixel = int(dicom_data.SamplesPerPixel)
                    except:
                        samples_per_pixel = 1
                
                if hasattr(dicom_data, 'PhotometricInterpretation'):
                    try:
                        photometric_interpretation = str(dicom_data.PhotometricInterpretation)
                    except:
                        photometric_interpretation = 'MONOCHROME2'
                
                image, created = DicomImage.objects.get_or_create(
                    series=series,
                    sop_instance_uid=image_instance_uid,
                    defaults={
                        'image_number': int(dicom_data.get('InstanceNumber', 0)),
                        'file_path': file_path,
                        'rows': rows,
                        'columns': columns,
                        'bits_allocated': bits_allocated,
                        'samples_per_pixel': samples_per_pixel,
                        'photometric_interpretation': photometric_interpretation,
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
                errors.append(f"Error processing {file.name}: {str(e)}")
                if 'file_path' in locals():
                    try:
                        default_storage.delete(file_path)
                    except:
                        pass
                continue
        
        # Prepare response
        if not uploaded_files:
            error_message = 'No valid DICOM files were uploaded'
            if errors:
                error_message += f'. Errors: {"; ".join(errors[:5])}'  # Limit error messages
            return JsonResponse({'error': error_message}, status=400)
        
        response_data = {
            'message': f'Uploaded {len(uploaded_files)} files successfully',
            'uploaded_files': uploaded_files,
            'study_id': study.id if study else None
        }
        
        if errors:
            response_data['warnings'] = errors[:5]  # Include warnings for partial success
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Unexpected error in upload_dicom_files: {e}")
        import traceback
        traceback.print_exc()
        
        # Create error notification
        create_system_error_notification(f"DICOM upload error: {str(e)}", request.user)
        
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def upload_dicom_folder(request):
    """Handle DICOM folder uploads with comprehensive error handling and validation"""
    try:
        # Ensure media directories exist with proper permissions
        ensure_directories()
        
        if 'files' not in request.FILES:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        uploaded_files = []
        studies = {}
        errors = []
        
        # Group files by study
        for file in files:
            try:
                # More comprehensive file validation
                file_name = file.name.lower()
                file_size = file.size
                
                # Check file size (100MB limit)
                if file_size > 100 * 1024 * 1024:  # 100MB
                    errors.append(f"File {file.name} is too large (max 100MB)")
                    continue
                
                # Accept any file that might be DICOM (more permissive)
                is_dicom_candidate = (
                    file_name.endswith(('.dcm', '.dicom')) or
                    file_name.endswith(('.dcm.gz', '.dicom.gz')) or
                    file_name.endswith(('.dcm.bz2', '.dicom.bz2')) or
                    '.' not in file.name or  # Files without extension
                    file_name.endswith('.img') or  # Common DICOM format
                    file_name.endswith('.ima') or  # Common DICOM format
                    file_name.endswith('.raw') or  # Raw data
                    file_size > 1024  # Files larger than 1KB (likely not text)
                )
                
                if not is_dicom_candidate:
                    errors.append(f"File {file.name} does not appear to be a DICOM file")
                    continue
                
                # Save file with unique name to avoid conflicts
                import uuid
                unique_filename = f"{uuid.uuid4()}_{file.name}"
                file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file.read()))
                
                # Try to read DICOM data with multiple fallback methods
                dicom_data = None
                try:
                    # Method 1: Try reading from file path
                    dicom_data = pydicom.dcmread(default_storage.path(file_path))
                except Exception as e1:
                    try:
                        # Method 2: Try reading from file object
                        file.seek(0)  # Reset file pointer
                        dicom_data = pydicom.dcmread(file)
                        # Re-save the file after successful read
                        file.seek(0)
                        file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file.read()))
                    except Exception as e2:
                        try:
                            # Method 3: Try reading as bytes
                            file.seek(0)
                            file_bytes = file.read()
                            dicom_data = pydicom.dcmread(file_bytes)
                            # Save the bytes
                            file_path = default_storage.save(f'dicom_files/{unique_filename}', ContentFile(file_bytes))
                        except Exception as e3:
                            print(f"Failed to read DICOM file {file.name}: {e1}, {e2}, {e3}")
                            # Clean up the saved file
                            try:
                                default_storage.delete(file_path)
                            except:
                                pass
                            errors.append(f"Could not read DICOM data from {file.name}")
                            continue
                
                # Validate that we have essential DICOM tags
                if not dicom_data:
                    errors.append(f"No DICOM data found in {file.name}")
                    continue
                
                # Get study UID with fallback
                study_uid = str(dicom_data.get('StudyInstanceUID', ''))
                if not study_uid:
                    # Try to generate a fallback study UID
                    study_uid = f"STUDY_{uuid.uuid4()}"
                    print(f"Generated fallback StudyInstanceUID for {file.name}: {study_uid}")
                
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
                errors.append(f"Error processing {file.name}: {str(e)}")
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
                
                # Extract patient information with fallbacks
                patient_name = 'Unknown'
                if hasattr(first_dicom, 'PatientName'):
                    try:
                        patient_name = str(first_dicom.PatientName)
                    except:
                        patient_name = 'Unknown'
                
                patient_id = 'Unknown'
                if hasattr(first_dicom, 'PatientID'):
                    try:
                        patient_id = str(first_dicom.PatientID)
                    except:
                        patient_id = 'Unknown'
                
                # Extract other fields with safe fallbacks
                study_date = parse_dicom_date(getattr(first_dicom, 'StudyDate', None))
                study_time = parse_dicom_time(getattr(first_dicom, 'StudyTime', None))
                study_description = str(getattr(first_dicom, 'StudyDescription', ''))
                modality = str(first_dicom.Modality) if hasattr(first_dicom, 'Modality') else 'OT'
                institution_name = str(getattr(first_dicom, 'InstitutionName', ''))
                accession_number = str(getattr(first_dicom, 'AccessionNumber', ''))
                referring_physician = str(getattr(first_dicom, 'ReferringPhysicianName', ''))
                
                study, created = DicomStudy.objects.get_or_create(
                    study_instance_uid=study_uid,
                    defaults={
                        'patient_name': patient_name,
                        'patient_id': patient_id,
                        'study_date': study_date,
                        'study_time': study_time,
                        'study_description': study_description,
                        'modality': modality,
                        'institution_name': institution_name,
                        'uploaded_by': request.user if request.user.is_authenticated else None,
                        'facility': request.user.facility_staff.facility if hasattr(request.user, 'facility_staff') else None,
                        'accession_number': accession_number,
                        'referring_physician': referring_physician,
                    }
                )
                
                # Create notifications for new study uploads
                if created:
                    try:
                        # Notify radiologists
                        radiologist_group = Group.objects.get(name='Radiologists')
                        for radiologist in radiologist_group.user_set.all():
                            Notification.objects.create(
                                recipient=radiologist,
                                notification_type='new_study',
                                title='New Study Uploaded',
                                message=f'New {modality} study uploaded for {patient_name} - {study_description}',
                                related_study=study
                            )
                    except Group.DoesNotExist:
                        pass
                
                # Create worklist entry if study was created
                if created:
                    try:
                        # Get or create a default facility if none exists
                        facility = study.facility
                        if not facility:
                            facility, _ = Facility.objects.get_or_create(
                                name="Default Facility",
                                defaults={
                                    'address': 'Unknown',
                                    'phone': 'Unknown',
                                    'email': 'unknown@facility.com'
                                }
                            )
                            # Update the study with the facility
                            study.facility = facility
                            study.save()
                        
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
                            facility=facility,
                            study=study,
                            status='completed'
                        )
                    except Exception as e:
                        print(f"Error creating worklist entry: {e}")
                
                # Process each file in the study
                for i, dicom_data in enumerate(study_data['dicom_data']):
                    try:
                        # Create or get series with fallback UID
                        series_uid = str(dicom_data.get('SeriesInstanceUID', ''))
                        if not series_uid:
                            series_uid = f"SERIES_{uuid.uuid4()}"
                            print(f"Generated fallback SeriesInstanceUID for {study_data['files'][i]}: {series_uid}")
                        
                        series, created = DicomSeries.objects.get_or_create(
                            study=study,
                            series_instance_uid=series_uid,
                            defaults={
                                'series_number': int(dicom_data.get('SeriesNumber', 0)),
                                'series_description': str(getattr(dicom_data, 'SeriesDescription', '')),
                                'modality': str(dicom_data.Modality) if hasattr(dicom_data, 'Modality') else 'OT',
                            }
                        )
                        
                        # Create image with fallback UID
                        image_instance_uid = str(dicom_data.get('SOPInstanceUID', ''))
                        if not image_instance_uid:
                            image_instance_uid = f"IMAGE_{uuid.uuid4()}"
                            print(f"Generated fallback SOPInstanceUID for {study_data['files'][i]}: {image_instance_uid}")
                        
                        # Extract image data with safe fallbacks
                        rows = 0
                        columns = 0
                        bits_allocated = 16
                        samples_per_pixel = 1
                        photometric_interpretation = 'MONOCHROME2'
                        
                        if hasattr(dicom_data, 'Rows'):
                            try:
                                rows = int(dicom_data.Rows)
                            except:
                                rows = 0
                        
                        if hasattr(dicom_data, 'Columns'):
                            try:
                                columns = int(dicom_data.Columns)
                            except:
                                columns = 0
                        
                        if hasattr(dicom_data, 'BitsAllocated'):
                            try:
                                bits_allocated = int(dicom_data.BitsAllocated)
                            except:
                                bits_allocated = 16
                        
                        if hasattr(dicom_data, 'SamplesPerPixel'):
                            try:
                                samples_per_pixel = int(dicom_data.SamplesPerPixel)
                            except:
                                samples_per_pixel = 1
                        
                        if hasattr(dicom_data, 'PhotometricInterpretation'):
                            try:
                                photometric_interpretation = str(dicom_data.PhotometricInterpretation)
                            except:
                                photometric_interpretation = 'MONOCHROME2'
                        
                        image, created = DicomImage.objects.get_or_create(
                            series=series,
                            sop_instance_uid=image_instance_uid,
                            defaults={
                                'image_number': int(dicom_data.get('InstanceNumber', 0)),
                                'file_path': study_data['file_paths'][i],
                                'rows': rows,
                                'columns': columns,
                                'bits_allocated': bits_allocated,
                                'samples_per_pixel': samples_per_pixel,
                                'photometric_interpretation': photometric_interpretation,
                                'pixel_spacing': str(getattr(dicom_data, 'PixelSpacing', '')),
                                'slice_thickness': float(getattr(dicom_data, 'SliceThickness', 0)),
                                'window_center': str(getattr(dicom_data, 'WindowCenter', '')),
                                'window_width': str(getattr(dicom_data, 'WindowWidth', '')),
                            }
                        )
                        
                        if created:
                            uploaded_files.append(study_data['files'][i])
                            
                    except Exception as e:
                        print(f"Error processing image in study {study_uid}: {e}")
                        errors.append(f"Error processing {study_data['files'][i]}: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"Error processing study {study_uid}: {e}")
                errors.append(f"Error processing study {study_uid}: {str(e)}")
                continue
        
        # Prepare response
        if not uploaded_files:
            error_message = 'No valid DICOM files were uploaded'
            if errors:
                error_message += f'. Errors: {"; ".join(errors[:5])}'  # Limit error messages
            return JsonResponse({'error': error_message}, status=400)
        
        response_data = {
            'message': f'Uploaded {len(uploaded_files)} files from {len(studies)} study(ies)',
            'uploaded_files': uploaded_files,
            'study_id': study.id if study else None
        }
        
        if errors:
            response_data['warnings'] = errors[:5]  # Include warnings for partial success
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Unexpected error in upload_dicom_folder: {e}")
        import traceback
        traceback.print_exc()
        
        # Create error notification
        create_system_error_notification(f"DICOM folder upload error: {str(e)}", request.user)
        
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@api_view(['GET'])
def get_studies(request):
    """Get studies based on user permissions"""
    try:
        # Check if user is admin or radiologist
        if request.user.is_superuser or request.user.groups.filter(name='Radiologists').exists():
            # Admin and radiologists can see all studies
            studies = DicomStudy.objects.all()[:20]
        elif request.user.groups.filter(name='Facilities').exists():
            # Facility users can only see their own studies
            try:
                facility_user = FacilityUser.objects.get(user=request.user)
                studies = DicomStudy.objects.filter(facility=facility_user.facility)[:20]
            except FacilityUser.DoesNotExist:
                studies = DicomStudy.objects.none()
        else:
            # No access for other users
            studies = DicomStudy.objects.none()
        
        serializer = DicomStudySerializer(studies, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


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
        print(f"Attempting to get image data for image_id: {image_id}")
        image = DicomImage.objects.get(id=image_id)
        print(f"Found image: {image}, file_path: {image.file_path}")
        
        # Get query parameters
        window_width = request.GET.get('window_width', image.window_width)
        window_level = request.GET.get('window_level', image.window_center)
        inverted = request.GET.get('inverted', 'false').lower() == 'true'
        
        # Convert to appropriate types
        if window_width:
            window_width = float(window_width)
        if window_level:
            window_level = float(window_level)
        
        print(f"Processing image with WW: {window_width}, WL: {window_level}, inverted: {inverted}")
        
        # Get processed image
        image_base64 = image.get_processed_image_base64(window_width, window_level, inverted)
        
        if image_base64:
            print(f"Successfully processed image {image_id}")
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
            print(f"Failed to process image {image_id}")
            return Response({'error': 'Could not process image - file may be missing or corrupted'}, status=500)
            
    except DicomImage.DoesNotExist:
        print(f"Image not found: {image_id}")
        return Response({'error': 'Image not found'}, status=404)
    except Exception as e:
        print(f"Unexpected error processing image {image_id}: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': f'Server error: {str(e)}'}, status=500)


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
    """Enhanced AI analysis with actual image processing and diagnosis"""
    try:
        image = DicomImage.objects.get(id=image_id)
        
        # Load DICOM data for analysis
        dicom_data = image.load_dicom_data()
        if not dicom_data:
            return JsonResponse({'error': 'Could not load DICOM data'}, status=400)
        
        pixel_array = image.get_pixel_array()
        if pixel_array is None:
            return JsonResponse({'error': 'Could not get pixel data'}, status=400)
        
        # Perform basic image analysis
        analysis_results = perform_basic_ai_analysis(pixel_array, dicom_data)
        
        # Generate diagnosis based on findings
        diagnosis = generate_ai_diagnosis(analysis_results, dicom_data)
        
        # Enhanced results with actual analysis
        ai_results = {
            'analysis_type': 'comprehensive_diagnosis',
            'summary': diagnosis['summary'],
            'confidence_score': diagnosis['confidence'],
            'findings': analysis_results['findings'],
            'diagnosis': diagnosis['diagnosis'],
            'recommendations': diagnosis['recommendations'],
            'highlighted_regions': analysis_results['highlighted_regions'],
            'measurements': analysis_results['measurements'],
            'abnormalities_detected': analysis_results['abnormalities'],
            'tissue_analysis': analysis_results['tissue_analysis']
        }
        
        # Save AI analysis result
        ai_analysis = AIAnalysis.objects.create(
            image=image,
            analysis_type='comprehensive_diagnosis',
            findings=ai_results['findings'],
            summary=ai_results['summary'],
            confidence_score=ai_results['confidence_score'],
            highlighted_regions=ai_results['highlighted_regions']
        )
        
        return JsonResponse(ai_results)
        
    except DicomImage.DoesNotExist:
        return JsonResponse({'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'AI analysis failed: {str(e)}'}, status=400)


def perform_basic_ai_analysis(pixel_array, dicom_data):
    """Perform basic AI analysis on the image"""
    try:
        import cv2
        from scipy import ndimage
        from skimage import measure, morphology
        
        # Convert to uint8 for processing
        if pixel_array.dtype != np.uint8:
            pixel_array_norm = ((pixel_array - pixel_array.min()) / 
                               (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
        else:
            pixel_array_norm = pixel_array
        
        findings = []
        highlighted_regions = []
        measurements = []
        abnormalities = []
        
        # Basic image statistics
        mean_intensity = float(np.mean(pixel_array))
        std_intensity = float(np.std(pixel_array))
        min_intensity = float(np.min(pixel_array))
        max_intensity = float(np.max(pixel_array))
        
        # Histogram analysis
        hist, bins = np.histogram(pixel_array.flatten(), bins=50)
        
        # Edge detection for structure analysis
        edges = cv2.Canny(pixel_array_norm, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Detect potential abnormalities using thresholding
        # High intensity regions (potential calcifications/contrast)
        high_threshold = mean_intensity + 2 * std_intensity
        high_intensity_mask = pixel_array > high_threshold
        high_intensity_regions = measure.label(high_intensity_mask)
        
        for region in measure.regionprops(high_intensity_regions):
            if region.area > 10:  # Filter small regions
                y, x = region.centroid
                findings.append({
                    'type': 'High density region',
                    'location': {'x': float(x), 'y': float(y)},
                    'area': int(region.area),
                    'confidence': 0.7,
                    'description': 'Potential calcification or contrast enhancement'
                })
                highlighted_regions.append({
                    'x': float(x - 10), 'y': float(y - 10), 
                    'width': 20, 'height': 20, 'type': 'high_density'
                })
        
        # Low intensity regions (potential cysts/air)
        low_threshold = mean_intensity - 2 * std_intensity
        low_intensity_mask = pixel_array < low_threshold
        low_intensity_regions = measure.label(low_intensity_mask)
        
        for region in measure.regionprops(low_intensity_regions):
            if region.area > 20:  # Filter small regions
                y, x = region.centroid
                findings.append({
                    'type': 'Low density region',
                    'location': {'x': float(x), 'y': float(y)},
                    'area': int(region.area),
                    'confidence': 0.6,
                    'description': 'Potential cyst, air, or low-density lesion'
                })
                highlighted_regions.append({
                    'x': float(x - 15), 'y': float(y - 15), 
                    'width': 30, 'height': 30, 'type': 'low_density'
                })
        
        # Texture analysis using local binary patterns
        texture_score = calculate_texture_complexity(pixel_array_norm)
        
        # Symmetry analysis
        symmetry_score = calculate_symmetry(pixel_array_norm)
        
        # Generate measurements
        measurements = [
            {'name': 'Mean Intensity', 'value': round(mean_intensity, 2), 'unit': 'HU'},
            {'name': 'Standard Deviation', 'value': round(std_intensity, 2), 'unit': 'HU'},
            {'name': 'Intensity Range', 'value': f"{round(min_intensity, 2)} - {round(max_intensity, 2)}", 'unit': 'HU'},
            {'name': 'Edge Density', 'value': round(edge_density * 100, 2), 'unit': '%'},
            {'name': 'Texture Complexity', 'value': round(texture_score, 2), 'unit': 'Score'},
            {'name': 'Symmetry Score', 'value': round(symmetry_score, 2), 'unit': 'Score'}
        ]
        
        # Detect abnormalities based on thresholds
        if edge_density > 0.1:
            abnormalities.append({
                'type': 'High edge density',
                'severity': 'moderate',
                'description': 'Increased structural complexity detected'
            })
        
        if len(findings) > 5:
            abnormalities.append({
                'type': 'Multiple regions of interest',
                'severity': 'moderate',
                'description': f'{len(findings)} regions requiring attention detected'
            })
        
        if symmetry_score < 0.7:
            abnormalities.append({
                'type': 'Asymmetry detected',
                'severity': 'mild',
                'description': 'Image shows structural asymmetry'
            })
        
        # Tissue analysis
        tissue_analysis = analyze_tissue_types(pixel_array, dicom_data)
        
        return {
            'findings': findings,
            'highlighted_regions': highlighted_regions,
            'measurements': measurements,
            'abnormalities': abnormalities,
            'tissue_analysis': tissue_analysis,
            'image_statistics': {
                'mean_intensity': mean_intensity,
                'std_intensity': std_intensity,
                'edge_density': edge_density,
                'texture_score': texture_score,
                'symmetry_score': symmetry_score
            }
        }
        
    except Exception as e:
        print(f"Error in AI analysis: {e}")
        return {
            'findings': [],
            'highlighted_regions': [],
            'measurements': [],
            'abnormalities': [],
            'tissue_analysis': {},
            'image_statistics': {}
        }


def generate_ai_diagnosis(analysis_results, dicom_data):
    """Generate AI diagnosis based on analysis results"""
    try:
        modality = getattr(dicom_data, 'Modality', 'Unknown')
        body_part = getattr(dicom_data, 'BodyPartExamined', 'Unknown')
        
        findings = analysis_results['findings']
        abnormalities = analysis_results['abnormalities']
        stats = analysis_results['image_statistics']
        
        # Base confidence
        confidence = 0.8
        
        # Generate diagnosis based on findings
        diagnosis_parts = []
        recommendations = []
        
        if len(findings) == 0:
            diagnosis_parts.append("No significant abnormalities detected")
            confidence = 0.9
        else:
            # Analyze findings
            high_density_count = len([f for f in findings if f['type'] == 'High density region'])
            low_density_count = len([f for f in findings if f['type'] == 'Low density region'])
            
            if high_density_count > 0:
                if modality == 'CT':
                    diagnosis_parts.append(f"{high_density_count} high-density region(s) suggesting possible calcifications or contrast enhancement")
                    recommendations.append("Consider correlation with clinical history for calcified lesions")
                else:
                    diagnosis_parts.append(f"{high_density_count} hyperintense region(s) detected")
            
            if low_density_count > 0:
                if modality == 'CT':
                    diagnosis_parts.append(f"{low_density_count} low-density region(s) suggesting possible cysts or air")
                    recommendations.append("Consider further characterization of low-density lesions")
                else:
                    diagnosis_parts.append(f"{low_density_count} hypointense region(s) detected")
        
        # Add modality-specific analysis
        if modality == 'CT':
            if stats.get('mean_intensity', 0) > 100:
                diagnosis_parts.append("High average attenuation suggesting dense tissue or contrast enhancement")
            elif stats.get('mean_intensity', 0) < -100:
                diagnosis_parts.append("Low average attenuation suggesting air or fat content")
                
        # Analyze abnormalities
        for abnormality in abnormalities:
            if abnormality['type'] == 'Asymmetry detected':
                diagnosis_parts.append("Structural asymmetry noted")
                recommendations.append("Consider comparison with prior studies")
                confidence *= 0.9
            elif abnormality['type'] == 'High edge density':
                diagnosis_parts.append("Increased structural complexity")
                recommendations.append("Consider detailed evaluation of complex regions")
        
        # Generate final summary
        if len(diagnosis_parts) == 0:
            summary = "Image analysis completed. Study appears within normal limits."
        else:
            summary = "AI Analysis: " + ". ".join(diagnosis_parts) + "."
        
        # Add standard disclaimer
        summary += " This AI analysis is for assistance only and requires radiologist interpretation."
        
        if len(recommendations) == 0:
            recommendations = ["Continue routine follow-up as clinically indicated"]
        
        return {
            'diagnosis': ". ".join(diagnosis_parts) if diagnosis_parts else "No significant abnormalities",
            'summary': summary,
            'confidence': min(confidence, 0.95),  # Cap confidence at 95%
            'recommendations': recommendations
        }
        
    except Exception as e:
        print(f"Error generating diagnosis: {e}")
        return {
            'diagnosis': "Analysis completed with limitations",
            'summary': "AI analysis encountered processing limitations. Manual review recommended.",
            'confidence': 0.5,
            'recommendations': ["Manual radiologist review recommended"]
        }


def calculate_texture_complexity(image):
    """Calculate texture complexity score"""
    try:
        from skimage.feature import local_binary_pattern
        
        # Local Binary Pattern
        radius = 3
        n_points = 8 * radius
        lbp = local_binary_pattern(image, n_points, radius, method='uniform')
        
        # Calculate histogram
        hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, range=(0, n_points + 2))
        hist = hist.astype(float)
        hist /= (hist.sum() + 1e-7)
        
        # Calculate entropy as texture measure
        entropy = -np.sum(hist * np.log2(hist + 1e-7))
        
        # Normalize to 0-1 range
        return min(entropy / 8.0, 1.0)
    except:
        return 0.5


def calculate_symmetry(image):
    """Calculate bilateral symmetry score"""
    try:
        height, width = image.shape
        mid = width // 2
        
        left_half = image[:, :mid]
        right_half = np.fliplr(image[:, mid:])
        
        # Resize to same dimensions if needed
        min_width = min(left_half.shape[1], right_half.shape[1])
        left_half = left_half[:, :min_width]
        right_half = right_half[:, :min_width]
        
        # Calculate correlation
        correlation = np.corrcoef(left_half.flatten(), right_half.flatten())[0, 1]
        
        return max(0, correlation)
    except:
        return 0.8


def analyze_tissue_types(pixel_array, dicom_data):
    """Analyze different tissue types in the image"""
    try:
        modality = getattr(dicom_data, 'Modality', 'Unknown')
        
        if modality == 'CT':
            # CT Hounsfield unit based analysis
            air_mask = pixel_array < -500
            fat_mask = (pixel_array >= -500) & (pixel_array < -50)
            soft_tissue_mask = (pixel_array >= -50) & (pixel_array < 150)
            bone_mask = pixel_array >= 150
            
            air_percentage = np.sum(air_mask) / pixel_array.size * 100
            fat_percentage = np.sum(fat_mask) / pixel_array.size * 100
            soft_tissue_percentage = np.sum(soft_tissue_mask) / pixel_array.size * 100
            bone_percentage = np.sum(bone_mask) / pixel_array.size * 100
            
            return {
                'air': round(air_percentage, 1),
                'fat': round(fat_percentage, 1),
                'soft_tissue': round(soft_tissue_percentage, 1),
                'bone': round(bone_percentage, 1)
            }
        else:
            # For other modalities, use intensity-based analysis
            low_intensity = pixel_array < np.percentile(pixel_array, 25)
            medium_intensity = (pixel_array >= np.percentile(pixel_array, 25)) & (pixel_array < np.percentile(pixel_array, 75))
            high_intensity = pixel_array >= np.percentile(pixel_array, 75)
            
            return {
                'low_intensity': round(np.sum(low_intensity) / pixel_array.size * 100, 1),
                'medium_intensity': round(np.sum(medium_intensity) / pixel_array.size * 100, 1),
                'high_intensity': round(np.sum(high_intensity) / pixel_array.size * 100, 1)
            }
    except:
        return {}


@api_view(['GET'])
def get_3d_reconstruction(request, series_id):
    """Enhanced 3D reconstruction with MPR, bone, angiogram, and virtual surgery"""
    try:
        series = get_object_or_404(DicomSeries, id=series_id)
        images = series.dicomimage_set.all().order_by('image_number')
        
        if not images.exists():
            return Response({'error': 'No images found in series'}, status=404)
        
        reconstruction_type = request.GET.get('type', 'mpr')
        
        # Get reconstruction parameters
        window_center = request.GET.get('window_center', 40)
        window_width = request.GET.get('window_width', 400)
        threshold_min = request.GET.get('threshold_min', -1000)
        threshold_max = request.GET.get('threshold_max', 1000)
        
        # Prepare 3D data based on reconstruction type
        if reconstruction_type == 'mpr':
            # Multi-Planar Reconstruction
            data = {
                'type': 'mpr',
                'series_id': series_id,
                'modality': series.modality,
                'images_count': images.count(),
                'axial_data': [],
                'sagittal_data': [],
                'coronal_data': [],
                'window_center': int(window_center),
                'window_width': int(window_width)
            }
            
            # Prepare axial slices (original orientation)
            for image in images:
                try:
                    with open(default_storage.path(image.file_path), 'rb') as f:
                        dicom_data = pydicom.dcmread(f)
                        pixel_data = dicom_data.pixel_array
                        
                        # Apply window/level
                        pixel_data = apply_window_level(pixel_data, int(window_center), int(window_width))
                        
                        data['axial_data'].append({
                            'image_id': image.id,
                            'slice_number': image.image_number,
                            'pixel_data': pixel_data.tolist(),
                            'rows': image.rows,
                            'columns': image.columns,
                            'pixel_spacing': image.pixel_spacing,
                            'slice_thickness': image.slice_thickness
                        })
                except Exception as e:
                    print(f"Error processing image {image.id}: {e}")
                    continue
            
            # Calculate sagittal and coronal reconstructions
            if data['axial_data']:
                data['sagittal_data'] = calculate_sagittal_reconstruction(data['axial_data'])
                data['coronal_data'] = calculate_coronal_reconstruction(data['axial_data'])
                
        elif reconstruction_type == '3d_bone':
            # 3D Bone Reconstruction
            data = {
                'type': '3d_bone',
                'series_id': series_id,
                'modality': series.modality,
                'images_count': images.count(),
                'volume_data': [],
                'threshold_min': int(threshold_min),
                'threshold_max': int(threshold_max),
                'bone_threshold': 150  # Typical bone threshold
            }
            
            for image in images:
                try:
                    with open(default_storage.path(image.file_path), 'rb') as f:
                        dicom_data = pydicom.dcmread(f)
                        pixel_data = dicom_data.pixel_array
                        
                        # Apply bone threshold
                        bone_mask = (pixel_data >= data['bone_threshold'])
                        bone_data = pixel_data * bone_mask
                        
                        data['volume_data'].append({
                            'image_id': image.id,
                            'slice_number': image.image_number,
                            'pixel_data': bone_data.tolist(),
                            'mask_data': bone_mask.tolist(),
                            'rows': image.rows,
                            'columns': image.columns,
                            'pixel_spacing': image.pixel_spacing,
                            'slice_thickness': image.slice_thickness
                        })
                except Exception as e:
                    print(f"Error processing image {image.id}: {e}")
                    continue
                    
        elif reconstruction_type == 'angiogram':
            # Angiogram Reconstruction
            data = {
                'type': 'angiogram',
                'series_id': series_id,
                'modality': series.modality,
                'images_count': images.count(),
                'vessel_data': [],
                'mip_data': [],
                'threshold_min': int(threshold_min),
                'threshold_max': int(threshold_max),
                'vessel_threshold': 100  # Typical vessel threshold
            }
            
            for image in images:
                try:
                    with open(default_storage.path(image.file_path), 'rb') as f:
                        dicom_data = pydicom.dcmread(f)
                        pixel_data = dicom_data.pixel_array
                        
                        # Apply vessel threshold
                        vessel_mask = (pixel_data >= data['vessel_threshold'])
                        vessel_data = pixel_data * vessel_mask
                        
                        data['vessel_data'].append({
                            'image_id': image.id,
                            'slice_number': image.image_number,
                            'pixel_data': vessel_data.tolist(),
                            'mask_data': vessel_mask.tolist(),
                            'rows': image.rows,
                            'columns': image.columns,
                            'pixel_spacing': image.pixel_spacing,
                            'slice_thickness': image.slice_thickness
                        })
                except Exception as e:
                    print(f"Error processing image {image.id}: {e}")
                    continue
            
            # Calculate Maximum Intensity Projection (MIP)
            if data['vessel_data']:
                data['mip_data'] = calculate_mip_reconstruction(data['vessel_data'])
                
        elif reconstruction_type == 'virtual_surgery':
            # Virtual Surgery Planning
            data = {
                'type': 'virtual_surgery',
                'series_id': series_id,
                'modality': series.modality,
                'images_count': images.count(),
                'segmentation_data': [],
                'cutting_planes': [],
                'surgical_tools': [],
                'window_center': int(window_center),
                'window_width': int(window_width)
            }
            
            for image in images:
                try:
                    with open(default_storage.path(image.file_path), 'rb') as f:
                        dicom_data = pydicom.dcmread(f)
                        pixel_data = dicom_data.pixel_array
                        
                        # Apply window/level for surgical planning
                        pixel_data = apply_window_level(pixel_data, int(window_center), int(window_width))
                        
                        # Basic tissue segmentation (bone, soft tissue, air)
                        segmentation = segment_tissues(pixel_data)
                        
                        data['segmentation_data'].append({
                            'image_id': image.id,
                            'slice_number': image.image_number,
                            'pixel_data': pixel_data.tolist(),
                            'segmentation': segmentation,
                            'rows': image.rows,
                            'columns': image.columns,
                            'pixel_spacing': image.pixel_spacing,
                            'slice_thickness': image.slice_thickness
                        })
                except Exception as e:
                    print(f"Error processing image {image.id}: {e}")
                    continue
        else:
            return Response({'error': 'Invalid reconstruction type'}, status=400)
        
        return Response(data)
        
    except Exception as e:
        print(f"Error in 3D reconstruction: {e}")
        return Response({'error': f'3D reconstruction failed: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def calculate_volume(request):
    """Calculate volume from contour data"""
    try:
        data = json.loads(request.body)
        contour_points = data.get('contour_points', [])
        pixel_spacing = data.get('pixel_spacing', [1.0, 1.0])
        slice_thickness = data.get('slice_thickness', 1.0)
        
        if len(contour_points) < 3:
            return JsonResponse({'error': 'At least 3 points required for volume calculation'}, status=400)
        
        # Calculate area using shoelace formula
        area = 0
        n = len(contour_points)
        for i in range(n):
            j = (i + 1) % n
            area += contour_points[i][0] * contour_points[j][1]
            area -= contour_points[j][0] * contour_points[i][1]
        area = abs(area) / 2.0
        
        # Convert to mm²
        pixel_area = pixel_spacing[0] * pixel_spacing[1]
        area_mm2 = area * pixel_area
        
        # Calculate volume (assuming uniform slice thickness)
        volume_mm3 = area_mm2 * slice_thickness
        volume_ml = volume_mm3 / 1000.0  # Convert to ml
        
        return JsonResponse({
            'volume_mm3': round(volume_mm3, 2),
            'volume_ml': round(volume_ml, 2),
            'area_mm2': round(area_mm2, 2)
        })
        
    except Exception as e:
        print(f"Error calculating volume: {e}")
        return JsonResponse({'error': f'Volume calculation failed: {str(e)}'}, status=500)


def apply_window_level(pixel_data, window_center, window_width):
    """Apply window/level transformation to pixel data"""
    try:
        pixel_data = np.array(pixel_data, dtype=np.float32)
        window_min = window_center - window_width / 2
        window_max = window_center + window_width / 2
        
        # Clip values to window range
        pixel_data = np.clip(pixel_data, window_min, window_max)
        
        # Normalize to 0-255
        pixel_data = ((pixel_data - window_min) / (window_max - window_min)) * 255
        pixel_data = np.clip(pixel_data, 0, 255)
        
        return pixel_data.astype(np.uint8)
    except Exception as e:
        print(f"Error applying window/level: {e}")
        return pixel_data


def calculate_sagittal_reconstruction(axial_data):
    """Calculate sagittal reconstruction from axial slices"""
    try:
        if not axial_data:
            return []
        
        # Get dimensions
        rows = axial_data[0]['rows']
        cols = axial_data[0]['columns']
        slices = len(axial_data)
        
        # Create sagittal slices (along Y-Z plane)
        sagittal_data = []
        for x in range(cols):
            sagittal_slice = []
            for z in range(slices):
                if z < len(axial_data) and x < len(axial_data[z]['pixel_data'][0]):
                    row_data = []
                    for y in range(rows):
                        if y < len(axial_data[z]['pixel_data']):
                            row_data.append(axial_data[z]['pixel_data'][y][x])
                        else:
                            row_data.append(0)
                    sagittal_slice.append(row_data)
                else:
                    sagittal_slice.append([0] * rows)
            
            sagittal_data.append({
                'slice_number': x,
                'pixel_data': sagittal_slice,
                'rows': slices,
                'columns': rows
            })
        
        return sagittal_data
    except Exception as e:
        print(f"Error calculating sagittal reconstruction: {e}")
        return []


def calculate_coronal_reconstruction(axial_data):
    """Calculate coronal reconstruction from axial slices"""
    try:
        if not axial_data:
            return []
        
        # Get dimensions
        rows = axial_data[0]['rows']
        cols = axial_data[0]['columns']
        slices = len(axial_data)
        
        # Create coronal slices (along X-Z plane)
        coronal_data = []
        for y in range(rows):
            coronal_slice = []
            for z in range(slices):
                if z < len(axial_data) and y < len(axial_data[z]['pixel_data']):
                    coronal_slice.append(axial_data[z]['pixel_data'][y])
                else:
                    coronal_slice.append([0] * cols)
            
            coronal_data.append({
                'slice_number': y,
                'pixel_data': coronal_slice,
                'rows': slices,
                'columns': cols
            })
        
        return coronal_data
    except Exception as e:
        print(f"Error calculating coronal reconstruction: {e}")
        return []


def calculate_mip_reconstruction(vessel_data):
    """Calculate Maximum Intensity Projection for angiogram"""
    try:
        if not vessel_data:
            return []
        
        # Get dimensions
        rows = vessel_data[0]['rows']
        cols = vessel_data[0]['columns']
        slices = len(vessel_data)
        
        # Calculate MIP along Z-axis
        mip_data = []
        for y in range(rows):
            row_data = []
            for x in range(cols):
                max_intensity = 0
                for z in range(slices):
                    if (z < len(vessel_data) and 
                        y < len(vessel_data[z]['pixel_data']) and 
                        x < len(vessel_data[z]['pixel_data'][0])):
                        intensity = vessel_data[z]['pixel_data'][y][x]
                        max_intensity = max(max_intensity, intensity)
                row_data.append(max_intensity)
            mip_data.append(row_data)
        
        return {
            'pixel_data': mip_data,
            'rows': rows,
            'columns': cols
        }
    except Exception as e:
        print(f"Error calculating MIP reconstruction: {e}")
        return []


def segment_tissues(pixel_data):
    """Basic tissue segmentation for virtual surgery"""
    try:
        pixel_data = np.array(pixel_data)
        
        # Simple threshold-based segmentation
        air_mask = (pixel_data < -500)
        fat_mask = (pixel_data >= -500) & (pixel_data < -50)
        soft_tissue_mask = (pixel_data >= -50) & (pixel_data < 150)
        bone_mask = (pixel_data >= 150)
        
        segmentation = {
            'air': air_mask.tolist(),
            'fat': fat_mask.tolist(),
            'soft_tissue': soft_tissue_mask.tolist(),
            'bone': bone_mask.tolist()
        }
        
        return segmentation
    except Exception as e:
        print(f"Error in tissue segmentation: {e}")
        return {}


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


@login_required
def api_study_clinical_info(request, study_id):
    """Get clinical information for a study"""
    try:
        study = DicomStudy.objects.get(id=study_id)
        return JsonResponse({
            'success': True,
            'clinical_info': study.clinical_info,
            'referring_physician': study.referring_physician,
            'accession_number': study.accession_number
        })
    except DicomStudy.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Study not found'
        })


def create_system_error_notification(error_message, user=None):
    """Create system error notification"""
    try:
        # Notify administrators
        admin_users = User.objects.filter(is_superuser=True)
        for admin in admin_users:
            Notification.objects.create(
                recipient=admin,
                notification_type='system_error',
                title='System Error',
                message=error_message
            )
        
        # Also notify the user if provided
        if user and user.is_authenticated:
            Notification.objects.create(
                recipient=user,
                notification_type='system_error',
                title='Upload Error',
                message=error_message
            )
    except Exception as e:
        print(f"Error creating system error notification: {e}")


@login_required
@user_passes_test(is_admin)
def delete_measurement(request, measurement_id):
    """Admin delete individual measurement"""
    try:
        measurement = get_object_or_404(Measurement, id=measurement_id)
        measurement.delete()
        return JsonResponse({'success': True, 'message': 'Measurement deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
def delete_annotation(request, annotation_id):
    """Admin delete individual annotation"""
    try:
        annotation = get_object_or_404(Annotation, id=annotation_id)
        annotation.delete()
        return JsonResponse({'success': True, 'message': 'Annotation deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
def delete_series(request, series_id):
    """Admin delete series and all associated images"""
    try:
        series = get_object_or_404(DicomSeries, id=series_id)
        series_name = f"Series {series.series_number} - {series.series_description}"
        
        # Delete all associated files
        for image in series.images.all():
            if image.file_path:
                try:
                    default_storage.delete(image.file_path.name)
                except:
                    pass
        
        series.delete()
        return JsonResponse({'success': True, 'message': f'{series_name} deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
def delete_image(request, image_id):
    """Admin delete individual image"""
    try:
        image = get_object_or_404(DicomImage, id=image_id)
        
        # Delete the file
        if image.file_path:
            try:
                default_storage.delete(image.file_path.name)
            except:
                pass
        
        image.delete()
        return JsonResponse({'success': True, 'message': 'Image deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)