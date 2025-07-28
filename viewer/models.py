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
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    letterhead_logo = models.ImageField(upload_to='facility_logos/', blank=True)
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
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    
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


class ClinicalInformation(models.Model):
    """Model to store clinical information for studies"""
    study = models.OneToOneField(DicomStudy, on_delete=models.CASCADE, related_name='clinical_info')
    chief_complaint = models.TextField(blank=True)
    clinical_history = models.TextField(blank=True)
    physical_examination = models.TextField(blank=True)
    clinical_diagnosis = models.TextField(blank=True)
    referring_physician = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"Clinical Info - {self.study.patient_name}"


class Report(models.Model):
    """Model to store radiology reports"""
    REPORT_STATUS = [
        ('draft', 'Draft'),
        ('final', 'Final'),
        ('preliminary', 'Preliminary'),
    ]
    
    study = models.OneToOneField(DicomStudy, on_delete=models.CASCADE, related_name='report')
    title = models.CharField(max_length=200, default='Radiology Report')
    findings = models.TextField()
    impression = models.TextField()
    recommendations = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"Report - {self.study.patient_name}"


class Notification(models.Model):
    """Model to store notifications for radiologists and admins"""
    NOTIFICATION_TYPES = [
        ('new_upload', 'New Upload'),
        ('report_ready', 'Report Ready'),
        ('urgent_case', 'Urgent Case'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    study = models.ForeignKey(DicomStudy, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} - {self.recipient.username}"


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
        if dicom_data:
            return dicom_data.pixel_array
        return None
    
    def apply_windowing(self, pixel_array, window_width=None, window_level=None, inverted=False):
        """Apply window/level transformation to pixel array"""
        if pixel_array is None:
            return None
        
        # Use stored values if not provided
        if window_width is None:
            window_width = self.window_width or 400
        if window_level is None:
            window_level = self.window_center or 40
        
        # Normalize to 0-255 range
        min_val = window_level - window_width / 2
        max_val = window_level + window_width / 2
        
        # Clip values
        pixel_array = np.clip(pixel_array, min_val, max_val)
        
        # Normalize to 0-255
        pixel_array = ((pixel_array - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        
        if inverted:
            pixel_array = 255 - pixel_array
        
        return pixel_array
    
    def get_processed_image_base64(self, window_width=None, window_level=None, inverted=False):
        """Get processed image as base64 string"""
        pixel_array = self.get_pixel_array()
        if pixel_array is None:
            return None
        
        # Apply windowing
        processed_array = self.apply_windowing(pixel_array, window_width, window_level, inverted)
        
        # Convert to PIL Image
        image = Image.fromarray(processed_array)
        
        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def save_dicom_metadata(self):
        """Extract and save DICOM metadata"""
        dicom_data = self.load_dicom_data()
        if dicom_data:
            self.rows = dicom_data.Rows
            self.columns = dicom_data.Columns
            
            # Pixel spacing
            if hasattr(dicom_data, 'PixelSpacing'):
                self.pixel_spacing_x = float(dicom_data.PixelSpacing[0])
                self.pixel_spacing_y = float(dicom_data.PixelSpacing[1])
            
            # Slice thickness
            if hasattr(dicom_data, 'SliceThickness'):
                self.slice_thickness = float(dicom_data.SliceThickness)
            
            # Window settings
            if hasattr(dicom_data, 'WindowWidth'):
                self.window_width = float(dicom_data.WindowWidth)
            if hasattr(dicom_data, 'WindowCenter'):
                self.window_center = float(dicom_data.WindowCenter)
            
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
    hounsfield_units = models.FloatField(null=True, blank=True)  # For HU measurements
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.measurement_type} - {self.value}{self.unit}"


class Annotation(models.Model):
    """Model to store user annotations"""
    image = models.ForeignKey(DicomImage, related_name='annotations', on_delete=models.CASCADE)
    x_coordinate = models.FloatField()
    y_coordinate = models.FloatField()
    text = models.TextField()
    font_size = models.IntegerField(default=14)
    color = models.CharField(max_length=7, default='#FF0000')  # Hex color
    is_draggable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Annotation at ({self.x_coordinate}, {self.y_coordinate})"