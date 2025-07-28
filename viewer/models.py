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


class Facility(models.Model):
    """Model to represent healthcare facilities"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Extended user profile with role and facility"""
    USER_ROLES = [
        ('radiologist', 'Radiologist'),
        ('admin', 'Administrator'),
        ('technologist', 'Technologist'),
        ('facility_staff', 'Facility Staff'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=USER_ROLES, default='facility_staff')
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    @property
    def can_view_all_facilities(self):
        return self.role in ['radiologist', 'admin']
    
    @property
    def can_create_reports(self):
        return self.role in ['radiologist', 'admin']


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
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, default='new', choices=[
        ('new', 'New'),
        ('pending', 'Pending Review'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ])
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
    
    # Hounsfield units properties
    rescale_intercept = models.FloatField(null=True, blank=True)
    rescale_slope = models.FloatField(null=True, blank=True)
    
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
        if dicom_data:
            return dicom_data.pixel_array
        return None
    
    def apply_windowing(self, pixel_array, window_width=None, window_level=None, inverted=False):
        """Apply window/level transformation to pixel array"""
        if pixel_array is None:
            return None
        
        # Get window parameters
        ww = window_width or self.window_width or 400
        wl = window_level or self.window_center or 40
        
        # Apply window/level transformation
        min_val = wl - ww / 2
        max_val = wl + ww / 2
        
        # Clip values
        windowed = np.clip(pixel_array, min_val, max_val)
        
        # Normalize to 0-255
        if max_val > min_val:
            normalized = ((windowed - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(windowed, dtype=np.uint8)
        
        # Invert if requested
        if inverted:
            normalized = 255 - normalized
        
        return normalized
    
    def get_hounsfield_units(self, x, y, radius=5):
        """Get Hounsfield units for a region around the specified point"""
        pixel_array = self.get_pixel_array()
        if pixel_array is None:
            return None
        
        # Get region around point
        y_min = max(0, int(y - radius))
        y_max = min(pixel_array.shape[0], int(y + radius))
        x_min = max(0, int(x - radius))
        x_max = min(pixel_array.shape[1], int(x + radius))
        
        region = pixel_array[y_min:y_max, x_min:x_max]
        
        # Apply rescale parameters if available
        if self.rescale_slope and self.rescale_intercept:
            hu_values = region * self.rescale_slope + self.rescale_intercept
        else:
            hu_values = region
        
        return {
            'mean': float(np.mean(hu_values)),
            'min': float(np.min(hu_values)),
            'max': float(np.max(hu_values)),
            'std': float(np.std(hu_values))
        }
    
    def get_processed_image_base64(self, window_width=None, window_level=None, inverted=False):
        """Get processed image as base64 string"""
        pixel_array = self.get_pixel_array()
        if pixel_array is None:
            return None
        
        # Apply windowing
        processed = self.apply_windowing(pixel_array, window_width, window_level, inverted)
        if processed is None:
            return None
        
        # Convert to PIL Image
        img = Image.fromarray(processed)
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def save_dicom_metadata(self):
        """Save DICOM metadata to model fields"""
        dicom_data = self.load_dicom_data()
        if not dicom_data:
            return
        
        # Basic image properties
        self.rows = getattr(dicom_data, 'Rows', 0)
        self.columns = getattr(dicom_data, 'Columns', 0)
        
        # Pixel spacing
        pixel_spacing = getattr(dicom_data, 'PixelSpacing', None)
        if pixel_spacing and len(pixel_spacing) >= 2:
            self.pixel_spacing_x = float(pixel_spacing[0])
            self.pixel_spacing_y = float(pixel_spacing[1])
        
        # Slice thickness
        slice_thickness = getattr(dicom_data, 'SliceThickness', None)
        if slice_thickness:
            self.slice_thickness = float(slice_thickness)
        
        # Window parameters
        window_width = getattr(dicom_data, 'WindowWidth', None)
        if window_width:
            self.window_width = float(window_width)
        
        window_center = getattr(dicom_data, 'WindowCenter', None)
        if window_center:
            self.window_center = float(window_center)
        
        # Hounsfield units parameters
        rescale_intercept = getattr(dicom_data, 'RescaleIntercept', None)
        if rescale_intercept is not None:
            self.rescale_intercept = float(rescale_intercept)
        
        rescale_slope = getattr(dicom_data, 'RescaleSlope', None)
        if rescale_slope is not None:
            self.rescale_slope = float(rescale_slope)
        
        self.save()


class Measurement(models.Model):
    """Model to store user measurements"""
    MEASUREMENT_TYPES = [
        ('line', 'Line Measurement'),
        ('angle', 'Angle Measurement'),
        ('area', 'Area Measurement'),
        ('ellipse', 'Ellipse Measurement'),
    ]
    
    image = models.ForeignKey(DicomImage, related_name='measurements', on_delete=models.CASCADE)
    measurement_type = models.CharField(max_length=10, choices=MEASUREMENT_TYPES, default='line')
    coordinates = models.JSONField()  # Store coordinates as JSON
    value = models.FloatField()  # Measurement value (distance, angle, area)
    unit = models.CharField(max_length=10, default='px')  # px, mm, cm
    hounsfield_value = models.FloatField(null=True, blank=True)  # For ellipse measurements
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_measurement_type_display()} - {self.value} {self.unit}"


class Annotation(models.Model):
    """Model to store user annotations"""
    image = models.ForeignKey(DicomImage, related_name='annotations', on_delete=models.CASCADE)
    x_coordinate = models.FloatField()
    y_coordinate = models.FloatField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Annotation at ({self.x_coordinate}, {self.y_coordinate})"


class RadiologyReport(models.Model):
    """Model to store radiology reports"""
    study = models.ForeignKey(DicomStudy, related_name='reports', on_delete=models.CASCADE)
    clinical_information = models.TextField(blank=True)
    findings = models.TextField(blank=True)
    impression = models.TextField(blank=True)
    recommendation = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='draft', choices=[
        ('draft', 'Draft'),
        ('final', 'Final'),
        ('amended', 'Amended'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    signed_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='signed_reports')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report for {self.study.patient_name} - {self.created_at.date()}"
    
    @property
    def is_signed(self):
        return self.status == 'final' and self.signed_at is not None


class Notification(models.Model):
    """Model to store system notifications"""
    NOTIFICATION_TYPES = [
        ('new_upload', 'New Upload'),
        ('report_ready', 'Report Ready'),
        ('system_alert', 'System Alert'),
    ]
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()}: {self.title}"