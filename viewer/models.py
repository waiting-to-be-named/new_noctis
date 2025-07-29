# dicom_viewer/models.py
from django.db import models
from django.contrib.auth.models import User
import json
import os
import pydicom
from django.conf import settings
from PIL import Image
import numpy as np
import io
import base64
from django.utils import timezone


class Facility(models.Model):
    """Model to represent healthcare facilities"""
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    letterhead_logo = models.ImageField(upload_to='facility_logos/', null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='facility')
    ae_title = models.CharField(max_length=16, unique=True, help_text="DICOM Application Entity Title for PACS communication")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Facilities"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DicomStudy(models.Model):
    """Model to represent a DICOM study"""
    study_instance_uid = models.CharField(max_length=100, unique=True)
    patient_name = models.CharField(max_length=200)
    patient_id = models.CharField(max_length=100)
    study_date = models.DateField(null=True, blank=True)
    study_time = models.TimeField(null=True, blank=True)
    study_description = models.TextField(blank=True)
    modality = models.CharField(max_length=10)
    institution_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True)
    clinical_info = models.TextField(blank=True)
    accession_number = models.CharField(max_length=50, blank=True)
    referring_physician = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.patient_name} - {self.study_date} ({self.modality})"
    
    @property
    def series_count(self):
        return self.series.count()
    
    @property
    def total_images(self):
        return DicomImage.objects.filter(series__study=self).count()


class DicomSeries(models.Model):
    """Model to represent a DICOM series"""
    study = models.ForeignKey(DicomStudy, related_name='series', on_delete=models.CASCADE)
    series_instance_uid = models.CharField(max_length=100)
    series_number = models.IntegerField(default=0)
    series_description = models.CharField(max_length=200, blank=True)
    modality = models.CharField(max_length=10)
    body_part_examined = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['series_number']
        unique_together = ['study', 'series_instance_uid']
    
    def __str__(self):
        return f"Series {self.series_number}: {self.series_description}"
    
    @property
    def image_count(self):
        return self.images.count()


class DicomImage(models.Model):
    """Model to represent individual DICOM images"""
    series = models.ForeignKey(DicomSeries, related_name='images', on_delete=models.CASCADE)
    sop_instance_uid = models.CharField(max_length=100)
    instance_number = models.IntegerField(default=0)
    file_path = models.FileField(upload_to='dicom_files/')
    
    # Image properties
    rows = models.IntegerField(default=0)
    columns = models.IntegerField(default=0)
    pixel_spacing_x = models.FloatField(null=True, blank=True)
    pixel_spacing_y = models.FloatField(null=True, blank=True)
    slice_thickness = models.FloatField(null=True, blank=True)
    window_width = models.FloatField(null=True, blank=True)
    window_center = models.FloatField(null=True, blank=True)
    
    # Additional DICOM fields
    bits_allocated = models.IntegerField(null=True, blank=True)
    image_number = models.IntegerField(null=True, blank=True)
    photometric_interpretation = models.CharField(max_length=50, blank=True)
    pixel_spacing = models.CharField(max_length=100, blank=True)  # Store as string like "1.0\\1.0"
    samples_per_pixel = models.IntegerField(null=True, blank=True)
    
    # Cached processed image
    processed_image_cache = models.TextField(blank=True)  # Base64 encoded image
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['instance_number']
        unique_together = ['series', 'sop_instance_uid']
    
    def __str__(self):
        return f"Image {self.instance_number}"
    
    def load_dicom_data(self):
        """Load and return pydicom dataset"""
        if not self.file_path:
            print(f"No file path for DicomImage {self.id}")
            return None
            
        try:
            # Handle both FileField and string paths
            if hasattr(self.file_path, 'path'):
                file_path = self.file_path.path
            else:
                # Check if it's a relative path, make it absolute
                if not os.path.isabs(str(self.file_path)):
                    from django.conf import settings
                    file_path = os.path.join(settings.MEDIA_ROOT, str(self.file_path))
                else:
                    file_path = str(self.file_path)
            
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"DICOM file not found: {file_path}")
                print(f"Current working directory: {os.getcwd()}")
                print(f"File path from model: {self.file_path}")
                # Try alternative paths
                alt_paths = [
                    os.path.join(os.getcwd(), 'media', str(self.file_path).replace('dicom_files/', '')),
                    os.path.join(os.getcwd(), str(self.file_path)),
                    str(self.file_path)
                ]
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        print(f"Found file at alternative path: {alt_path}")
                        file_path = alt_path
                        break
                else:
                    print(f"File not found in any of the attempted paths: {alt_paths}")
                    return None
                
            return pydicom.dcmread(file_path)
        except Exception as e:
            print(f"Error loading DICOM from {self.file_path}: {e}")
            print(f"Attempted file path: {file_path if 'file_path' in locals() else 'unknown'}")
            return None
    
    def get_pixel_array(self):
        """Get pixel array from DICOM file"""
        dicom_data = self.load_dicom_data()
        if dicom_data and hasattr(dicom_data, 'pixel_array'):
            return dicom_data.pixel_array
        return None
    
    def apply_windowing(self, pixel_array, window_width=None, window_level=None, inverted=False):
        """Apply window/level to pixel array"""
        if pixel_array is None:
            return None
        
        try:
            # Use provided values or defaults from DICOM
            ww = window_width if window_width is not None else (self.window_width or 400)
            wl = window_level if window_level is not None else (self.window_center or 40)
            
            # Convert to float for calculations
            image_data = pixel_array.astype(np.float32)
            
            # Apply window/level
            min_val = wl - ww / 2
            max_val = wl + ww / 2
            
            # Clip and normalize
            image_data = np.clip(image_data, min_val, max_val)
            
            # Avoid division by zero
            if max_val - min_val > 0:
                image_data = (image_data - min_val) / (max_val - min_val) * 255
            else:
                image_data = np.zeros_like(image_data)
            
            if inverted:
                image_data = 255 - image_data
            
            return image_data.astype(np.uint8)
        except Exception as e:
            print(f"Error applying windowing: {e}")
            return None
    
    def get_processed_image_base64(self, window_width=None, window_level=None, inverted=False):
        """Get processed image as base64 string"""
        try:
            pixel_array = self.get_pixel_array()
            if pixel_array is None:
                print(f"Could not get pixel array for image {self.id}")
                return None
            
            processed_array = self.apply_windowing(pixel_array, window_width, window_level, inverted)
            if processed_array is None:
                print(f"Could not apply windowing for image {self.id}")
                return None
            
            # Convert to PIL Image
            pil_image = Image.fromarray(processed_array, mode='L')
            
            # Convert to base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{image_base64}"
        except Exception as e:
            print(f"Error processing image {self.id}: {e}")
            return None
    
    def save_dicom_metadata(self):
        """Extract and save metadata from DICOM file"""
        dicom_data = self.load_dicom_data()
        if not dicom_data:
            return
        
        # Update image properties
        self.rows = getattr(dicom_data, 'Rows', 0)
        self.columns = getattr(dicom_data, 'Columns', 0)
        
        pixel_spacing = getattr(dicom_data, 'PixelSpacing', None)
        if pixel_spacing and len(pixel_spacing) >= 2:
            self.pixel_spacing_x = float(pixel_spacing[0])
            self.pixel_spacing_y = float(pixel_spacing[1])
        
        self.slice_thickness = getattr(dicom_data, 'SliceThickness', None)
        self.window_width = getattr(dicom_data, 'WindowWidth', None)
        self.window_center = getattr(dicom_data, 'WindowCenter', None)
        
        self.save()


class Measurement(models.Model):
    """Model to store user measurements"""
    MEASUREMENT_TYPES = [
        ('line', 'Line Measurement'),
        ('angle', 'Angle Measurement'),
        ('area', 'Area Measurement'),
        ('ellipse', 'Ellipse HU Measurement'),
    ]
    
    image = models.ForeignKey(DicomImage, related_name='measurements', on_delete=models.CASCADE)
    measurement_type = models.CharField(max_length=10, choices=MEASUREMENT_TYPES, default='line')
    coordinates = models.JSONField()  # Store coordinates as JSON
    value = models.FloatField()  # Measurement value (distance, angle, area)
    unit = models.CharField(max_length=10, default='px')  # px, mm, cm
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    # For ellipse HU measurements
    hounsfield_mean = models.FloatField(null=True, blank=True)
    hounsfield_min = models.FloatField(null=True, blank=True)
    hounsfield_max = models.FloatField(null=True, blank=True)
    hounsfield_std = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.measurement_type}: {self.value} {self.unit}"


class Annotation(models.Model):
    """Model to store user annotations"""
    image = models.ForeignKey(DicomImage, related_name='annotations', on_delete=models.CASCADE)
    x_coordinate = models.FloatField()
    y_coordinate = models.FloatField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    font_size = models.IntegerField(default=14)
    color = models.CharField(max_length=7, default='#FFFF00')  # Hex color
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Annotation: {self.text[:50]}"


class Report(models.Model):
    """Model to store radiology reports"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('finalized', 'Finalized'),
        ('printed', 'Printed'),
    ]
    
    study = models.ForeignKey(DicomStudy, related_name='reports', on_delete=models.CASCADE)
    radiologist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='written_reports')
    findings = models.TextField()
    impression = models.TextField()
    recommendations = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report for {self.study.patient_name} - {self.status}"


class WorklistEntry(models.Model):
    """Model for DICOM worklist entries"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    patient_name = models.CharField(max_length=200)
    patient_id = models.CharField(max_length=100)
    accession_number = models.CharField(max_length=50, unique=True)
    scheduled_station_ae_title = models.CharField(max_length=16)
    scheduled_procedure_step_start_date = models.DateField()
    scheduled_procedure_step_start_time = models.TimeField()
    modality = models.CharField(max_length=10)
    scheduled_performing_physician = models.CharField(max_length=200)
    procedure_description = models.TextField()
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    study = models.ForeignKey(DicomStudy, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-scheduled_procedure_step_start_date', '-scheduled_procedure_step_start_time']
    
    def __str__(self):
        return f"{self.patient_name} - {self.accession_number}"


class AIAnalysis(models.Model):
    """Model to store AI analysis results"""
    image = models.ForeignKey(DicomImage, related_name='ai_analyses', on_delete=models.CASCADE)
    analysis_type = models.CharField(max_length=50)
    findings = models.JSONField()  # Store structured findings
    summary = models.TextField()
    confidence_score = models.FloatField()
    highlighted_regions = models.JSONField()  # Store coordinates of highlighted regions
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Analysis for {self.image} - {self.analysis_type}"


class Notification(models.Model):
    """Model for system notifications"""
    NOTIFICATION_TYPES = [
        ('new_study', 'New Study Upload'),
        ('report_ready', 'Report Ready'),
        ('ai_complete', 'AI Analysis Complete'),
        ('system_error', 'System Error'),
        ('system', 'System Message'),
        ('chat', 'Chat Message'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_study = models.ForeignKey(DicomStudy, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type}: {self.title}"


class ChatMessage(models.Model):
    """Model for chat messages between radiologist and facility"""
    MESSAGE_TYPES = [
        ('system_upload', 'System Upload'),
        ('user_chat', 'User Chat'),
    ]
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='user_chat')
    message = models.TextField()
    related_study = models.ForeignKey(DicomStudy, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username if self.recipient else 'Facility'}: {self.message[:50]}"