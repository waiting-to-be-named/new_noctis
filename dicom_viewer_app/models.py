from django.db import models
from django.contrib.auth.models import User
import json
import os
import pydicom
from django.conf import settings
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import io
import base64


class DicomStudy(models.Model):
    """Enhanced model to represent a DICOM study"""
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
    """Enhanced model to represent a DICOM series"""
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
    """Enhanced model for individual DICOM images with better processing"""
    series = models.ForeignKey(DicomSeries, related_name='images', on_delete=models.CASCADE)
    sop_instance_uid = models.CharField(max_length=100)
    instance_number = models.IntegerField(default=0)
    file_path = models.FileField(upload_to='dicom_files/')
    
    # Enhanced image properties
    rows = models.IntegerField(default=0)
    columns = models.IntegerField(default=0)
    pixel_spacing_x = models.FloatField(null=True, blank=True)
    pixel_spacing_y = models.FloatField(null=True, blank=True)
    slice_thickness = models.FloatField(null=True, blank=True)
    window_width = models.FloatField(null=True, blank=True)
    window_center = models.FloatField(null=True, blank=True)
    
    # Enhanced image metadata
    bits_allocated = models.IntegerField(null=True, blank=True)
    bits_stored = models.IntegerField(null=True, blank=True)
    high_bit = models.IntegerField(null=True, blank=True)
    pixel_representation = models.IntegerField(null=True, blank=True)
    rescale_intercept = models.FloatField(null=True, blank=True)
    rescale_slope = models.FloatField(null=True, blank=True)
    
    # Cached processed image
    processed_image_cache = models.TextField(blank=True)
    
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
        """Get pixel array from DICOM file with enhanced processing"""
        dicom_data = self.load_dicom_data()
        if dicom_data and hasattr(dicom_data, 'pixel_array'):
            pixel_array = dicom_data.pixel_array
            
            # Apply rescale slope and intercept if available
            if hasattr(dicom_data, 'RescaleSlope') and hasattr(dicom_data, 'RescaleIntercept'):
                pixel_array = pixel_array * float(dicom_data.RescaleSlope) + float(dicom_data.RescaleIntercept)
            
            return pixel_array
        return None
    
    def apply_enhanced_windowing(self, pixel_array, window_width=None, window_level=None, inverted=False):
        """Apply enhanced window/level with superior image quality"""
        if pixel_array is None:
            return None
        
        # Use provided values or defaults from DICOM
        ww = window_width if window_width is not None else (self.window_width or 400)
        wl = window_level if window_level is not None else (self.window_center or 40)
        
        # Convert to float for calculations
        image_data = pixel_array.astype(np.float64)
        
        # Apply window/level with enhanced contrast
        min_val = wl - ww / 2
        max_val = wl + ww / 2
        
        # Clip and normalize with smooth transitions
        image_data = np.clip(image_data, min_val, max_val)
        image_data = (image_data - min_val) / (max_val - min_val)
        
        # Apply enhanced gamma correction for better visibility
        image_data = np.power(image_data, 0.75)
        
        # Scale to 8-bit with enhanced precision
        image_data = (image_data * 255).astype(np.uint8)
        
        if inverted:
            image_data = 255 - image_data
        
        return image_data
    
    def get_high_quality_image_base64(self, window_width=None, window_level=None, inverted=False):
        """Get processed image as base64 string with maximum quality"""
        pixel_array = self.get_pixel_array()
        if pixel_array is None:
            return None
        
        processed_array = self.apply_enhanced_windowing(pixel_array, window_width, window_level, inverted)
        
        # Convert to PIL Image with enhanced processing
        pil_image = Image.fromarray(processed_array, mode='L')
        
        # Apply subtle sharpening for medical images
        pil_image = pil_image.filter(ImageFilter.UnsharpMask(radius=0.3, percent=110, threshold=1))
        
        # Enhance contrast slightly
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(1.05)
        
        # Convert to base64 with maximum quality
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG', optimize=False)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{image_base64}"
    
    def save_enhanced_dicom_metadata(self):
        """Extract and save enhanced metadata from DICOM file"""
        dicom_data = self.load_dicom_data()
        if not dicom_data:
            return
        
        # Update enhanced image properties
        self.rows = getattr(dicom_data, 'Rows', 0)
        self.columns = getattr(dicom_data, 'Columns', 0)
        self.bits_allocated = getattr(dicom_data, 'BitsAllocated', None)
        self.bits_stored = getattr(dicom_data, 'BitsStored', None)
        self.high_bit = getattr(dicom_data, 'HighBit', None)
        self.pixel_representation = getattr(dicom_data, 'PixelRepresentation', None)
        self.rescale_intercept = getattr(dicom_data, 'RescaleIntercept', None)
        self.rescale_slope = getattr(dicom_data, 'RescaleSlope', None)
        
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
    ]
    
    image = models.ForeignKey(DicomImage, related_name='measurements', on_delete=models.CASCADE)
    measurement_type = models.CharField(max_length=10, choices=MEASUREMENT_TYPES, default='line')
    coordinates = models.JSONField()
    value = models.FloatField()
    unit = models.CharField(max_length=10, default='px')
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
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Annotation: {self.text[:50]}"