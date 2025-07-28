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


class UserProfile(models.Model):
    """Extended user profile with role and facility information"""
    ROLE_CHOICES = [
        ('radiologist', 'Radiologist'),
        ('admin', 'Administrator'),
        ('technician', 'Technician'),
        ('facility', 'Facility Staff'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='technician')
    facility = models.ForeignKey('Facility', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Facility(models.Model):
    """Model to represent medical facilities"""
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    letterhead_logo = models.ImageField(upload_to='facility_logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
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
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True)
    clinical_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
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
        if self.file_path and os.path.exists(self.file_path.path):
            try:
                return pydicom.dcmread(self.file_path.path)
            except Exception as e:
                print(f"Error loading DICOM: {e}")
                return None
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
        image_data = (image_data - min_val) / (max_val - min_val) * 255
        
        if inverted:
            image_data = 255 - image_data
        
        return image_data.astype(np.uint8)
    
    def get_processed_image_base64(self, window_width=None, window_level=None, inverted=False):
        """Get processed image as base64 string"""
        pixel_array = self.get_pixel_array()
        if pixel_array is None:
            return None
        
        processed_array = self.apply_windowing(pixel_array, window_width, window_level, inverted)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(processed_array, mode='L')
        
        # Convert to base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{image_base64}"
    
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
        ('ellipse', 'Ellipse Measurement'),
        ('hounsfield', 'Hounsfield Units'),
    ]
    
    UNIT_CHOICES = [
        ('px', 'Pixels'),
        ('mm', 'Millimeters'),
        ('cm', 'Centimeters'),
        ('hu', 'Hounsfield Units'),
    ]
    
    image = models.ForeignKey(DicomImage, related_name='measurements', on_delete=models.CASCADE)
    measurement_type = models.CharField(max_length=10, choices=MEASUREMENT_TYPES, default='line')
    coordinates = models.JSONField()  # Store coordinates as JSON
    value = models.FloatField()  # Measurement value (distance, angle, area)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='px')  # px, mm, cm, hu
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
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
    font_size = models.IntegerField(default=12)
    is_draggable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Annotation: {self.text[:50]}"


class Report(models.Model):
    """Model to store radiology reports"""
    REPORT_STATUS = [
        ('draft', 'Draft'),
        ('final', 'Final'),
        ('preliminary', 'Preliminary'),
    ]
    
    study = models.ForeignKey(DicomStudy, related_name='reports', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    findings = models.TextField(blank=True)
    impression = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report for {self.study.patient_name} - {self.created_at.date()}"


class Notification(models.Model):
    """Model to store user notifications"""
    NOTIFICATION_TYPES = [
        ('new_upload', 'New DICOM Upload'),
        ('report_ready', 'Report Ready'),
        ('system_alert', 'System Alert'),
    ]
    
    user = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_study = models.ForeignKey(DicomStudy, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"


class AIAnalysis(models.Model):
    """Model to store AI analysis results"""
    image = models.ForeignKey(DicomImage, related_name='ai_analyses', on_delete=models.CASCADE)
    analysis_type = models.CharField(max_length=50)  # e.g., 'tumor_detection', 'fracture_detection'
    confidence_score = models.FloatField()
    findings = models.TextField()
    highlighted_regions = models.JSONField()  # Store coordinates of highlighted areas
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Analysis: {self.analysis_type} - {self.confidence_score}%"


class Reconstruction3D(models.Model):
    """Model to store 3D reconstruction settings and results"""
    RECONSTRUCTION_TYPES = [
        ('mpr', 'Multi-Planar Reconstruction'),
        ('bone', '3D Bone Reconstruction'),
        ('angio', 'Angiography Reconstruction'),
        ('virtual_surgery', 'Virtual Surgery'),
    ]
    
    study = models.ForeignKey(DicomStudy, related_name='reconstructions', on_delete=models.CASCADE)
    reconstruction_type = models.CharField(max_length=20, choices=RECONSTRUCTION_TYPES)
    settings = models.JSONField()  # Store reconstruction parameters
    result_file = models.FileField(upload_to='3d_reconstructions/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_reconstruction_type_display()} - {self.study.patient_name}"