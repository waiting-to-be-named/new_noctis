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
import random
import string


class Facility(models.Model):
    """Model to represent healthcare facilities"""
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    letterhead_logo = models.ImageField(upload_to='facility_logos/', null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='facility')
    created_at = models.DateTimeField(auto_now_add=True)
    ae_title = models.CharField(max_length=16, unique=True, null=True, blank=True, help_text="DICOM AE Title automatically generated for this facility")
    dicom_port = models.IntegerField(unique=True, null=True, blank=True, help_text="DICOM C-STORE SCP port automatically assigned for this facility")
    
    class Meta:
        verbose_name_plural = "Facilities"
        ordering = ['name']
    
    def __str__(self):
        return self.name

    def generate_ae_title(self):
        """Generate a unique 16-character AE Title based on facility name"""
        # Base component derives from alphanumeric chars of the name (max 10 chars)
        base = "".join(c for c in self.name.upper() if c.isalnum())[:10]
        # Remaining length is filled with random uppercase letters/digits
        remaining_len = 16 - len(base)
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=remaining_len))
        return (base + suffix)[:16]
    
    def generate_dicom_port(self):
        """Generate a unique DICOM port number for this facility"""
        # Start from port 11112 and find next available port
        base_port = 11112
        max_port = 11200  # Limit to reasonable range
        
        for port in range(base_port, max_port):
            if not Facility.objects.filter(dicom_port=port).exclude(pk=self.pk).exists():
                return port
        
        # If no ports available in range, use a random port in higher range
        import random as rnd
        for _ in range(50):  # Try 50 times to find a random port
            port = rnd.randint(11200, 11299)
            if not Facility.objects.filter(dicom_port=port).exclude(pk=self.pk).exists():
                return port
        
        raise ValueError("No available DICOM ports found")

    def save(self, *args, **kwargs):
        # Auto-generate AE title if not provided
        if not self.ae_title or self.ae_title.strip() == "":
            # Ensure uniqueness by retrying generation if collision occurs
            for _ in range(5):
                candidate = self.generate_ae_title()
                if not Facility.objects.filter(ae_title=candidate).exclude(pk=self.pk).exists():
                    self.ae_title = candidate
                    break
        
        # Auto-generate DICOM port if not provided
        if not self.dicom_port:
            self.dicom_port = self.generate_dicom_port()
        
        super().save(*args, **kwargs)


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
    
    # Test data flag (removed for compatibility)
    # test_data = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['instance_number']
        unique_together = ['series', 'sop_instance_uid']
    
    def __str__(self):
        return f"Image {self.instance_number}"
    
    def load_dicom_data(self):
        """Load and return pydicom dataset - PRIORITIZE ACTUAL DICOM FILES"""
        # ALWAYS try to load actual DICOM files first, ignore cached data
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
                
            # ALWAYS use force=True to handle files without proper DICOM headers
            try:
                # Method 1: Force reading (most permissive)
                dicom_data = pydicom.dcmread(file_path, force=True)
                print(f"✅ Successfully loaded DICOM data for image {self.id} using force=True")
                return dicom_data
            except Exception as e1:
                print(f"Force DICOM reading failed: {e1}")
                try:
                    # Method 2: Read as bytes with force
                    with open(file_path, 'rb') as f:
                        file_bytes = f.read()
                    dicom_data = pydicom.dcmread(io.BytesIO(file_bytes), force=True)
                    print(f"✅ Successfully loaded DICOM data for image {self.id} using bytes method")
                    return dicom_data
                except Exception as e2:
                    print(f"Bytes DICOM reading failed: {e2}")
                    return None
                        
        except Exception as e:
            print(f"Error loading DICOM from {self.file_path}: {e}")
            print(f"Attempted file path: {file_path if 'file_path' in locals() else 'unknown'}")
            return None
    
    def get_pixel_array(self):
        """Get pixel array from DICOM file - CRITICAL FIX: ALWAYS load actual DICOM data"""
        try:
            # CRITICAL FIX: Always try to load actual DICOM data, ignore cached data
            print(f"🔄 Loading actual DICOM pixel array for image {self.id}")
            dicom_data = self.load_dicom_data()
            if dicom_data and hasattr(dicom_data, 'pixel_array'):
                pixel_array = dicom_data.pixel_array
                print(f"✅ Successfully loaded pixel array for image {self.id}, shape: {pixel_array.shape}")
                return pixel_array
            else:
                print(f"❌ No pixel array found in DICOM data for image {self.id}")
                return None
        except Exception as e:
            print(f"❌ Error getting pixel array for image {self.id}: {e}")
            return None
    
    def apply_windowing(self, pixel_array, window_width=None, window_level=None, inverted=False):
        """Apply window/level to pixel array with improved brightness handling"""
        if pixel_array is None:
            return None
        
        try:
            # Use provided values or defaults from DICOM
            ww = window_width if window_width is not None else (self.window_width or 400)
            wl = window_level if window_level is not None else (self.window_center or 40)
            
            # Convert to float for calculations
            image_data = pixel_array.astype(np.float32)
            
            # Get image statistics for better default values
            min_pixel = np.min(image_data)
            max_pixel = np.max(image_data)
            pixel_range = max_pixel - min_pixel
            
            # If no window/level provided, use image statistics for better defaults
            if window_width is None and window_level is None:
                if pixel_range > 0:
                    # Use 95% of the pixel range for better contrast
                    wl = min_pixel + pixel_range * 0.5
                    ww = pixel_range * 0.95
                else:
                    # Fallback to reasonable defaults
                    wl = 40
                    ww = 400
            
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
            
            # Ensure the result is in valid range
            image_data = np.clip(image_data, 0, 255)
            
            return image_data.astype(np.uint8)
        except Exception as e:
            print(f"Error applying windowing: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_processed_image_base64(self, window_width=None, window_level=None, inverted=False):
        """Get processed image as base64 string with enhanced quality preservation"""
        try:
            # Get pixel data
            pixel_array = self.get_pixel_array()
            if pixel_array is None:
                return None
            
            # Apply windowing with enhanced precision
            processed_array = self.apply_windowing(pixel_array, window_width, window_level, inverted)
            
            # Preserve original bit depth for better quality
            if processed_array.dtype != np.uint8:
                # Use more precise scaling to preserve detail
                min_val = processed_array.min()
                max_val = processed_array.max()
                if max_val > min_val:
                    processed_array = ((processed_array - min_val) / (max_val - min_val) * 255.0)
                else:
                    processed_array = processed_array * 0  # Handle constant arrays
                processed_array = np.clip(processed_array, 0, 255).astype(np.uint8)
            
            # Create PIL Image with quality preservation
            image = Image.fromarray(processed_array, mode='L')
            
            # Enhance sharpness for medical images slightly (with fallback)
            try:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(1.1)  # Slight sharpening
            except ImportError:
                # Skip enhancement if PIL.ImageEnhance is not available
                pass
            
            # Convert to base64 with high quality PNG
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', optimize=False, compress_level=1)  # Minimal compression for quality
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error processing image {self.id}: {e}")
            return None
    
    def get_enhanced_processed_image_base64(self, window_width=None, window_level=None, inverted=False, 
                                                   resolution_factor=1.0, density_enhancement=True, contrast_boost=1.0):
        """FIXED: Process actual uploaded DICOM files and remote machine data"""
        try:
            # Step 1: Try to load actual DICOM file
            if self.file_path:
                file_path = None
                
                # Handle FileField vs string paths
                if hasattr(self.file_path, 'path'):
                    file_path = self.file_path.path
                else:
                    # Check various path possibilities
                    possible_paths = [
                        os.path.join(settings.MEDIA_ROOT, str(self.file_path)),
                        os.path.join(settings.MEDIA_ROOT, 'dicom_files', os.path.basename(str(self.file_path))),
                        str(self.file_path),
                        os.path.join('/workspace/media', str(self.file_path)),
                        os.path.join('/workspace/media/dicom_files', os.path.basename(str(self.file_path)))
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            file_path = path
                            break
                
                if file_path and os.path.exists(file_path):
                    print(f"🎯 Processing actual DICOM file: {file_path}")
                    
                    try:
                        # Load actual DICOM data
                        dicom_data = pydicom.dcmread(file_path, force=True)
                        if hasattr(dicom_data, 'pixel_array'):
                            pixel_array = dicom_data.pixel_array
                            
                            # Process with enhanced quality
                            result = self.process_actual_dicom_data(
                                pixel_array, dicom_data, window_width, window_level, 
                                inverted, resolution_factor, density_enhancement, contrast_boost
                            )
                            
                            if result:
                                print(f"✅ Successfully processed actual DICOM file for image {self.id}")
                                return result
                        
                    except Exception as dicom_error:
                        print(f"Error processing DICOM file {file_path}: {dicom_error}")
            
            # Step 2: If no actual file, try the fallback method
            print(f"⚠️  No actual DICOM file found for image {self.id}, using fallback")
            return self.get_enhanced_processed_image_base64_original(
                window_width, window_level, inverted, resolution_factor, density_enhancement, contrast_boost
            )
            
        except Exception as e:
            print(f"❌ Error in enhanced processing for image {self.id}: {e}")
            return None
    
    def process_actual_dicom_data(self, pixel_array, dicom_data, window_width=None, window_level=None, 
                                 inverted=False, resolution_factor=1.0, density_enhancement=True, contrast_boost=1.0):
        """Process actual DICOM pixel data with medical-grade quality"""
        try:
            import numpy as np
            from PIL import Image, ImageEnhance
            import io
            import base64
            from skimage import exposure, filters
            
            # Use DICOM metadata for optimal windowing
            if window_width is None and hasattr(dicom_data, 'WindowWidth'):
                if isinstance(dicom_data.WindowWidth, (list, tuple)):
                    window_width = float(dicom_data.WindowWidth[0])
                else:
                    window_width = float(dicom_data.WindowWidth)
            
            if window_level is None and hasattr(dicom_data, 'WindowCenter'):
                if isinstance(dicom_data.WindowCenter, (list, tuple)):
                    window_level = float(dicom_data.WindowCenter[0])
                else:
                    window_level = float(dicom_data.WindowCenter)
            
            # Set medical imaging defaults if still None
            if window_width is None:
                window_width = 1500  # Good for chest X-rays
            if window_level is None:
                window_level = -600   # Lung window
            
            # Convert to float for processing
            pixel_array = pixel_array.astype(np.float32)
            
            # Apply rescale slope and intercept if available
            if hasattr(dicom_data, 'RescaleSlope') and hasattr(dicom_data, 'RescaleIntercept'):
                pixel_array = pixel_array * float(dicom_data.RescaleSlope) + float(dicom_data.RescaleIntercept)
            
            # Enhanced windowing
            window_min = window_level - window_width / 2
            window_max = window_level + window_width / 2
            
            # Apply windowing
            pixel_array = np.clip(pixel_array, window_min, window_max)
            pixel_array = ((pixel_array - window_min) / (window_max - window_min)) * 255
            
            # Apply density enhancement for better tissue differentiation
            if density_enhancement:
                pixel_array = exposure.equalize_adapthist(pixel_array / 255.0, clip_limit=0.01) * 255
            
            # Convert to uint8
            pixel_array = np.clip(pixel_array, 0, 255).astype(np.uint8)
            
            # Apply inversion if requested
            if inverted:
                pixel_array = 255 - pixel_array
            
            # Create PIL image
            image = Image.fromarray(pixel_array, mode='L')
            
            # Apply contrast boost
            if contrast_boost != 1.0:
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(contrast_boost)
            
            # Apply resolution enhancement
            if resolution_factor != 1.0:
                new_size = (int(image.width * resolution_factor), int(image.height * resolution_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', optimize=False, compress_level=0)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error processing actual DICOM data: {e}")
            return None
    
    def get_enhanced_processed_image_base64_original(self, window_width=None, window_level=None, inverted=False, 
                                          resolution_factor=2.0, density_enhancement=True, contrast_boost=1.5, thumbnail_size=None):
        """Get enhanced processed image with superior diagnostic quality for medical imaging - PRIORITIZE ACTUAL DICOM"""
        try:
            # CRITICAL FIX: Don't check cached data first - always try actual DICOM files
            # Get pixel data from actual DICOM file
            pixel_array = self.get_pixel_array()
            if pixel_array is None:
                print(f"❌ No pixel array available for image {self.id}")
                return None
            
            # Apply diagnostic-grade preprocessing
            pixel_array = self.apply_diagnostic_preprocessing(pixel_array)
            
            # Apply enhanced windowing with superior tissue differentiation
            processed_array = self.apply_diagnostic_windowing(
                pixel_array, window_width, window_level, inverted, 
                density_enhancement, contrast_boost
            )
            
            # Apply resolution enhancement for diagnostic clarity
            if resolution_factor != 1.0:
                processed_array = self.apply_diagnostic_resolution_enhancement(processed_array, resolution_factor)
            
            # Apply advanced tissue differentiation
            if density_enhancement:
                processed_array = self.apply_advanced_tissue_differentiation(processed_array)
            
            # Convert to PIL Image with diagnostic quality
            if processed_array.dtype != np.uint8:
                processed_array = np.clip(processed_array, 0, 255).astype(np.uint8)
            
            image = Image.fromarray(processed_array, mode='L')
            
            # Apply final diagnostic quality enhancements
            try:
                image = self.apply_diagnostic_quality_enhancement(image)
            except AttributeError as e:
                print(f"Warning: apply_diagnostic_quality_enhancement method not found: {e}")
                # Fallback to basic enhancement
                try:
                    from PIL import ImageEnhance
                    enhancer = ImageEnhance.Contrast(image)
                    image = enhancer.enhance(1.1)
                except Exception as fallback_error:
                    print(f"Fallback enhancement also failed: {fallback_error}")
                    # Return image as-is if all enhancements fail
                    pass
            
            # Resize for thumbnail if requested
            if thumbnail_size:
                image = image.resize(thumbnail_size, Image.Resampling.LANCZOS)
            
            # Convert to base64 with maximum diagnostic quality
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', optimize=False, compress_level=0)  # No compression for diagnostic quality
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error processing diagnostic image {self.id}: {e}")
            return None

    def apply_enhanced_windowing(self, pixel_array, window_width=None, window_level=None, inverted=False,
                                density_enhancement=False, contrast_boost=1.0):
        """Apply enhanced windowing with superior density differentiation for medical imaging"""
        try:
            # Use default values if not provided
            if window_width is None:
                window_width = self.window_width or 400
            if window_level is None:
                window_level = self.window_center or 40
            
            # Convert to float for better precision
            pixel_array = pixel_array.astype(np.float32)
            
            # Pre-process for noise reduction while preserving edges
            pixel_array = self.apply_medical_preprocessing(pixel_array)
            
            # Apply adaptive contrast boost based on tissue characteristics
            if contrast_boost != 1.0:
                pixel_array = self.apply_adaptive_contrast_boost(pixel_array, contrast_boost, window_level)
            
            # Apply enhanced windowing with gamma correction for better tissue visualization
            window_min = window_level - window_width / 2
            window_max = window_level + window_width / 2
            
            # Clip values to window range
            pixel_array = np.clip(pixel_array, window_min, window_max)
            
            # Apply non-linear windowing for better density differentiation
            if density_enhancement:
                pixel_array = self.apply_nonlinear_windowing(pixel_array, window_min, window_max)
            else:
                # Standard linear windowing
                pixel_array = ((pixel_array - window_min) / (window_max - window_min)) * 255
            
            # Apply density enhancement if requested
            if density_enhancement:
                pixel_array = self.apply_density_enhancement(pixel_array)
            
            # Apply inversion if requested
            if inverted:
                pixel_array = 255 - pixel_array
            
            # Final enhancement for medical imaging
            pixel_array = self.apply_final_medical_enhancement(pixel_array)
            
            return pixel_array
            
        except Exception as e:
            print(f"Error in enhanced windowing: {e}")
            return pixel_array
    
    def apply_medical_preprocessing(self, pixel_array):
        """Apply medical imaging specific preprocessing"""
        try:
            from scipy.ndimage import median_filter
            
            # Light denoising to preserve fine structures
            if pixel_array.size > 10000:  # Only for larger images
                denoised = median_filter(pixel_array, size=3)
                # Blend to preserve details
                alpha = 0.7  # Preserve 70% of original detail
                pixel_array = alpha * pixel_array + (1 - alpha) * denoised
            
            return pixel_array
        except Exception as e:
            print(f"Error in medical preprocessing: {e}")
            return pixel_array
    
    def apply_adaptive_contrast_boost(self, pixel_array, contrast_boost, window_level):
        """Apply adaptive contrast boost based on tissue type"""
        try:
            # Different boost factors for different tissue types based on HU values
            if window_level < -500:  # Air/lung tissue
                effective_boost = contrast_boost * 1.1
            elif -200 <= window_level <= 200:  # Soft tissue
                effective_boost = contrast_boost * 1.2  # Higher boost for soft tissue contrast
            elif window_level > 200:  # Bone tissue
                effective_boost = contrast_boost * 0.9
            else:
                effective_boost = contrast_boost
            
            return pixel_array * effective_boost
        except Exception as e:
            print(f"Error in adaptive contrast boost: {e}")
            return pixel_array
    
    def apply_nonlinear_windowing(self, pixel_array, window_min, window_max):
        """Apply non-linear windowing for enhanced density differentiation"""
        try:
            # Normalize to 0-1 range first
            normalized = (pixel_array - window_min) / (window_max - window_min)
            
            # Apply gamma correction for better tissue contrast
            gamma = 0.8  # Slightly enhance darker regions
            enhanced = np.power(normalized, gamma)
            
            # Apply S-curve for better contrast in mid-range densities
            enhanced = self.apply_s_curve_enhancement(enhanced)
            
            # Convert back to 0-255 range
            return enhanced * 255
            
        except Exception as e:
            print(f"Error in nonlinear windowing: {e}")
            # Fallback to linear windowing
            return ((pixel_array - window_min) / (window_max - window_min)) * 255
    
    def apply_s_curve_enhancement(self, normalized_array):
        """Apply S-curve enhancement for better mid-tone contrast"""
        try:
            # S-curve function for enhanced contrast
            # f(x) = 0.5 * (1 + tanh(k * (x - 0.5)))
            k = 3.0  # Curve steepness
            enhanced = 0.5 * (1 + np.tanh(k * (normalized_array - 0.5)))
            return enhanced
        except Exception as e:
            print(f"Error in S-curve enhancement: {e}")
            return normalized_array
    
    def apply_final_medical_enhancement(self, pixel_array):
        """Apply final enhancement specifically for medical imaging"""
        try:
            # Ensure proper range
            pixel_array = np.clip(pixel_array, 0, 255)
            
            # Apply histogram stretching for better utilization of dynamic range
            min_val = np.percentile(pixel_array, 1)
            max_val = np.percentile(pixel_array, 99)
            
            if max_val > min_val:
                pixel_array = ((pixel_array - min_val) / (max_val - min_val)) * 255
                pixel_array = np.clip(pixel_array, 0, 255)
            
            return pixel_array
        except Exception as e:
            print(f"Error in final medical enhancement: {e}")
            return pixel_array
    
    def apply_final_quality_enhancement(self, image):
        """Apply final quality enhancements to PIL image for superior medical imaging"""
        try:
            from PIL import ImageEnhance
            
            # Apply subtle sharpening for medical detail preservation
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)  # Slight sharpening
            
            # Apply subtle contrast enhancement
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.1)  # Slight contrast boost
            
            # Apply subtle brightness optimization
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.05)  # Slight brightness adjustment
            
            return image
        except Exception as e:
            print(f"Error in final quality enhancement: {e}")
            return image
    
    def apply_density_enhancement(self, pixel_array):
        """Apply density enhancement for better tissue differentiation"""
        try:
            # Apply histogram equalization for better contrast
            from skimage import exposure
            
            # Convert to uint8 for histogram equalization
            pixel_array_uint8 = np.clip(pixel_array, 0, 255).astype(np.uint8)
            
            # Apply adaptive histogram equalization
            enhanced = exposure.equalize_adapthist(pixel_array_uint8, clip_limit=0.03)
            
            # Convert back to 0-255 range
            enhanced = (enhanced * 255).astype(np.float32)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in density enhancement: {e}")
            return pixel_array
    
    def apply_density_differentiation(self, pixel_array):
        """Apply enhanced density differentiation for superior tissue visualization"""
        try:
            # Apply multi-scale processing with medical imaging optimization
            from scipy import ndimage
            from scipy.ndimage import uniform_filter
            
            # Enhanced multi-scale approach for better tissue contrast
            scales = [0.5, 1.0, 2.0, 4.0]  # Added finer scale for detail preservation
            processed_scales = []
            
            for scale in scales:
                if scale == 1.0:
                    processed_scales.append(pixel_array)
                elif scale < 1.0:
                    # High-pass filtering for edge enhancement
                    sigma = scale
                    smoothed = ndimage.gaussian_filter(pixel_array, sigma=sigma)
                    high_pass = pixel_array - smoothed
                    processed_scales.append(pixel_array + 0.3 * high_pass)  # Enhance edges
                else:
                    # Low-pass filtering for structure enhancement
                    sigma = scale
                    blurred = ndimage.gaussian_filter(pixel_array, sigma=sigma)
                    processed_scales.append(blurred)
            
            # Apply density-aware weighted combination
            enhanced = np.zeros_like(pixel_array, dtype=np.float32)
            weights = [0.2, 0.4, 0.25, 0.15]  # Optimized weights for medical imaging
            
            for i, scale_data in enumerate(processed_scales):
                enhanced += weights[i] * scale_data.astype(np.float32)
            
            # Apply local contrast enhancement using CLAHE-like technique
            enhanced = self.apply_local_contrast_enhancement(enhanced)
            
            # Apply edge-preserving smoothing to reduce noise while maintaining boundaries
            enhanced = self.apply_edge_preserving_filter(enhanced)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in enhanced density differentiation: {e}")
            return pixel_array
    
    def apply_local_contrast_enhancement(self, pixel_array):
        """Apply local contrast enhancement for better tissue differentiation"""
        try:
            from scipy.ndimage import uniform_filter
            
            # Calculate local mean and standard deviation
            kernel_size = min(16, max(8, int(min(pixel_array.shape) / 32)))
            local_mean = uniform_filter(pixel_array, size=kernel_size)
            
            # Calculate local variance
            local_variance = uniform_filter(pixel_array**2, size=kernel_size) - local_mean**2
            local_std = np.sqrt(np.maximum(local_variance, 1e-6))
            
            # Apply adaptive contrast enhancement
            contrast_factor = 1.0 + 0.5 * (local_std / (np.mean(local_std) + 1e-6))
            contrast_factor = np.clip(contrast_factor, 0.8, 1.5)
            
            enhanced = local_mean + contrast_factor * (pixel_array - local_mean)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in local contrast enhancement: {e}")
            return pixel_array
    
    def apply_edge_preserving_filter(self, pixel_array):
        """Apply edge-preserving filter to maintain tissue boundaries while reducing noise"""
        try:
            from scipy.ndimage import median_filter
            
            # Apply bilateral-like filtering using median filter for edge preservation
            # Use small kernel to preserve fine details
            kernel_size = 3
            filtered = median_filter(pixel_array, size=kernel_size)
            
            # Blend original and filtered based on local gradients
            # Calculate gradients to detect edges
            grad_x = np.gradient(pixel_array, axis=1)
            grad_y = np.gradient(pixel_array, axis=0)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            # Create edge-aware blending weights
            edge_threshold = np.percentile(gradient_magnitude, 75)
            edge_weights = np.clip(gradient_magnitude / (edge_threshold + 1e-6), 0, 1)
            
            # Blend: use original data at edges, filtered data in smooth regions
            result = edge_weights * pixel_array + (1 - edge_weights) * filtered
            
            return result
            
        except Exception as e:
            print(f"Error in edge preserving filter: {e}")
            return pixel_array
    
    def apply_resolution_enhancement(self, pixel_array, resolution_factor):
        """Apply enhanced resolution enhancement with medical image optimization"""
        try:
            if resolution_factor == 1.0:
                return pixel_array
            
            # Try to use scipy for high-quality interpolation
            try:
                from scipy import ndimage
                # Pre-process to reduce noise while preserving edges
                try:
                    from skimage import filters
                    smoothed = filters.gaussian(pixel_array, sigma=0.5, preserve_range=True)
                except ImportError:
                    # Fallback: simple smoothing using numpy
                    from scipy.ndimage import gaussian_filter
                    smoothed = gaussian_filter(pixel_array, sigma=0.5)
                
                # Apply high-quality bicubic interpolation
                enhanced = ndimage.zoom(smoothed, resolution_factor, order=3, mode='nearest')
                
                # Post-process to enhance medical details
                if resolution_factor > 1.0:
                    # Apply unsharp masking to enhance fine details
                    from scipy.ndimage import gaussian_filter
                    gaussian_filtered = gaussian_filter(enhanced, sigma=1.0)
                    unsharp_mask = enhanced - gaussian_filtered
                    enhanced = enhanced + 0.3 * unsharp_mask  # Moderate enhancement
                    
                    # Preserve original intensity range
                    original_min, original_max = pixel_array.min(), pixel_array.max()
                    enhanced_min, enhanced_max = enhanced.min(), enhanced.max()
                    
                    if enhanced_max > enhanced_min:
                        enhanced = (enhanced - enhanced_min) / (enhanced_max - enhanced_min)
                        enhanced = enhanced * (original_max - original_min) + original_min
                
                return enhanced
                
            except ImportError:
                # Fallback: use PIL for basic resizing
                from PIL import Image
                
                # Convert to PIL Image
                if pixel_array.dtype != np.uint8:
                    display_array = np.clip((pixel_array - pixel_array.min()) / 
                                          (pixel_array.max() - pixel_array.min()) * 255, 0, 255).astype(np.uint8)
                else:
                    display_array = pixel_array
                
                pil_image = Image.fromarray(display_array, mode='L')
                
                # Calculate new size
                new_width = int(pil_image.width * resolution_factor)
                new_height = int(pil_image.height * resolution_factor)
                
                # Resize with high quality
                resized = pil_image.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert back to numpy array
                enhanced = np.array(resized, dtype=pixel_array.dtype)
                
                return enhanced
                
        except Exception as e:
            print(f"Error in resolution enhancement: {e}")
            return pixel_array
    
    def get_multi_scale_processed_image(self, window_width=None, window_level=None, inverted=False):
        """Get multi-scale processed image for better detail visualization"""
        try:
            # Get pixel data
            pixel_array = self.get_pixel_array()
            if pixel_array is None:
                return None
            
            # Apply multi-scale processing
            processed_array = self.apply_multi_scale_processing(
                pixel_array, window_width, window_level, inverted
            )
            
            # Convert to PIL Image
            if processed_array.dtype != np.uint8:
                processed_array = np.clip(processed_array, 0, 255).astype(np.uint8)
            
            image = Image.fromarray(processed_array, mode='L')
            
            # Convert to base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', optimize=True)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error in multi-scale processing: {e}")
            return None
    
    def apply_multi_scale_processing(self, pixel_array, window_width=None, window_level=None, inverted=False):
        """Apply multi-scale processing for enhanced detail visualization"""
        try:
            from scipy import ndimage
            
            # Apply basic windowing first
            processed_array = self.apply_enhanced_windowing(
                pixel_array, window_width, window_level, inverted
            )
            
            # Create multi-scale representation
            scales = [1.0, 0.5, 0.25]
            scale_images = []
            
            for scale in scales:
                if scale == 1.0:
                    scale_images.append(processed_array)
                else:
                    # Downsample
                    downsampled = ndimage.zoom(processed_array, scale, order=1)
                    # Upsample back to original size
                    upsampled = ndimage.zoom(downsampled, 1/scale, order=1)
                    scale_images.append(upsampled)
            
            # Combine scales with different weights
            enhanced = np.zeros_like(processed_array)
            weights = [0.6, 0.3, 0.1]  # Emphasize fine details
            
            for i, scale_img in enumerate(scale_images):
                enhanced += weights[i] * scale_img
            
            return enhanced
            
        except Exception as e:
            print(f"Error in multi-scale processing: {e}")
            return processed_array
    
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
    ANALYSIS_TYPES = [
        ('chest_xray', 'Chest X-Ray Analysis'),
        ('ct_lung', 'CT Lung Analysis'),
        ('bone_fracture', 'Bone Fracture Detection'),
        ('brain_mri', 'Brain MRI Analysis'),
        ('cardiac_analysis', 'Cardiac Analysis'),
        ('general', 'General Analysis'),
        ('pneumonia_detection', 'Pneumonia Detection'),
        ('tumor_detection', 'Tumor Detection'),
        ('vessel_analysis', 'Vessel Analysis'),
    ]
    
    image = models.ForeignKey(DicomImage, related_name='ai_analyses', on_delete=models.CASCADE)
    analysis_type = models.CharField(max_length=50, choices=ANALYSIS_TYPES)
    findings = models.JSONField()  # Store structured findings
    summary = models.TextField()
    confidence_score = models.FloatField()
    highlighted_regions = models.JSONField()  # Store coordinates of highlighted regions
    processing_time = models.FloatField(default=0.0)  # Time taken for analysis
    model_version = models.CharField(max_length=50, default='v1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Analysis for {self.image} - {self.analysis_type}"


class MPRReconstruction(models.Model):
    """Model to store Multi-Planar Reconstruction data"""
    RECONSTRUCTION_TYPES = [
        ('axial', 'Axial View'),
        ('sagittal', 'Sagittal View'),
        ('coronal', 'Coronal View'),
        ('oblique', 'Oblique View'),
        ('curved', 'Curved MPR'),
    ]
    
    series = models.ForeignKey(DicomSeries, related_name='mpr_reconstructions', on_delete=models.CASCADE)
    reconstruction_type = models.CharField(max_length=20, choices=RECONSTRUCTION_TYPES)
    slice_position = models.FloatField(default=0.0)
    slice_thickness = models.FloatField(default=1.0)
    reconstruction_data = models.JSONField()  # Store reconstruction parameters
    image_data = models.TextField()  # Base64 encoded image
    window_width = models.FloatField(null=True, blank=True)
    window_level = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['series', 'reconstruction_type', 'slice_position']
    
    def __str__(self):
        return f"MPR {self.reconstruction_type} for {self.series}"


class VolumeRendering(models.Model):
    """Model to store 3D volume rendering data"""
    RENDERING_TYPES = [
        ('mip', 'Maximum Intensity Projection'),
        ('minip', 'Minimum Intensity Projection'),
        ('average', 'Average Intensity Projection'),
        ('volume', 'Volume Rendering'),
        ('surface', 'Surface Rendering'),
        ('bone_3d', 'Bone 3D Reconstruction'),
        ('angiogram', 'Angiogram Reconstruction'),
        ('cardiac_4d', 'Cardiac 4D Reconstruction'),
        ('neurological', 'Neurological Reconstruction'),
        ('orthopedic', 'Orthopedic Reconstruction'),
        ('dental', 'Dental 3D Reconstruction'),
    ]
    
    series = models.ForeignKey(DicomSeries, related_name='volume_renderings', on_delete=models.CASCADE)
    rendering_type = models.CharField(max_length=20, choices=RENDERING_TYPES)
    rendering_parameters = models.JSONField()  # Store rendering parameters
    volume_data = models.TextField()  # Base64 encoded volume data
    opacity_function = models.JSONField(default=dict)  # Opacity transfer function
    color_function = models.JSONField(default=dict)  # Color transfer function
    threshold_values = models.JSONField(default=dict)  # HU threshold values for different tissues
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Volume Rendering {self.rendering_type} for {self.series}"


class BoneReconstruction(models.Model):
    """Model for advanced bone reconstruction and analysis"""
    BONE_TYPES = [
        ('skull', 'Skull Reconstruction'),
        ('spine', 'Spine Reconstruction'),
        ('pelvis', 'Pelvis Reconstruction'),
        ('ribs', 'Rib Cage Reconstruction'),
        ('long_bones', 'Long Bones Reconstruction'),
        ('joints', 'Joint Reconstruction'),
        ('dental', 'Dental/Maxillofacial'),
        ('fracture_analysis', 'Fracture Analysis'),
    ]
    
    series = models.ForeignKey(DicomSeries, related_name='bone_reconstructions', on_delete=models.CASCADE)
    bone_type = models.CharField(max_length=20, choices=BONE_TYPES)
    reconstruction_data = models.TextField()  # Base64 encoded 3D bone data
    fracture_detected = models.BooleanField(default=False)
    fracture_locations = models.JSONField(default=list)  # Coordinates of detected fractures
    bone_density_analysis = models.JSONField(default=dict)  # Bone density measurements
    hounsfield_thresholds = models.JSONField(default=dict)  # HU values for bone classification
    surgical_planning_data = models.JSONField(default=dict)  # Data for surgical planning
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Bone Reconstruction {self.bone_type} for {self.series}"


class AngiogramAnalysis(models.Model):
    """Model for angiogram analysis and vessel reconstruction"""
    VESSEL_TYPES = [
        ('coronary', 'Coronary Arteries'),
        ('cerebral', 'Cerebral Vessels'),
        ('pulmonary', 'Pulmonary Vessels'),
        ('renal', 'Renal Vessels'),
        ('peripheral', 'Peripheral Vessels'),
        ('aorta', 'Aortic Analysis'),
        ('carotid', 'Carotid Arteries'),
        ('venous', 'Venous System'),
    ]
    
    STENOSIS_LEVELS = [
        ('none', 'No Stenosis (0-25%)'),
        ('mild', 'Mild Stenosis (25-50%)'),
        ('moderate', 'Moderate Stenosis (50-75%)'),
        ('severe', 'Severe Stenosis (75-90%)'),
        ('critical', 'Critical Stenosis (90-99%)'),
        ('occlusion', 'Complete Occlusion (100%)'),
    ]
    
    series = models.ForeignKey(DicomSeries, related_name='angiogram_analyses', on_delete=models.CASCADE)
    vessel_type = models.CharField(max_length=20, choices=VESSEL_TYPES)
    vessel_tree_data = models.TextField()  # Base64 encoded vessel tree reconstruction
    stenosis_detected = models.BooleanField(default=False)
    stenosis_locations = models.JSONField(default=list)  # Locations and severity of stenosis
    vessel_measurements = models.JSONField(default=dict)  # Diameter, length, tortuosity measurements
    contrast_analysis = models.JSONField(default=dict)  # Contrast enhancement analysis
    flow_analysis = models.JSONField(default=dict)  # Blood flow analysis if available
    ai_confidence_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Angiogram Analysis {self.vessel_type} for {self.series}"


class CardiacAnalysis(models.Model):
    """Model for cardiac imaging analysis"""
    CARDIAC_PHASES = [
        ('systole', 'Systolic Phase'),
        ('diastole', 'Diastolic Phase'),
        ('full_cycle', 'Full Cardiac Cycle'),
    ]
    
    series = models.ForeignKey(DicomSeries, related_name='cardiac_analyses', on_delete=models.CASCADE)
    cardiac_phase = models.CharField(max_length=20, choices=CARDIAC_PHASES)
    ejection_fraction = models.FloatField(null=True, blank=True)
    wall_motion_analysis = models.JSONField(default=dict)  # Regional wall motion
    chamber_volumes = models.JSONField(default=dict)  # LV, RV, LA, RA volumes
    valve_analysis = models.JSONField(default=dict)  # Valve function analysis
    perfusion_data = models.JSONField(default=dict)  # Myocardial perfusion
    coronary_calcium_score = models.FloatField(null=True, blank=True)
    rhythm_analysis = models.JSONField(default=dict)  # If ECG-gated
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Cardiac Analysis for {self.series}"


class NeurologicalAnalysis(models.Model):
    """Model for neurological imaging analysis"""
    BRAIN_REGIONS = [
        ('frontal', 'Frontal Lobe'),
        ('parietal', 'Parietal Lobe'),
        ('temporal', 'Temporal Lobe'),
        ('occipital', 'Occipital Lobe'),
        ('cerebellum', 'Cerebellum'),
        ('brainstem', 'Brainstem'),
        ('basal_ganglia', 'Basal Ganglia'),
        ('white_matter', 'White Matter'),
        ('ventricles', 'Ventricular System'),
    ]
    
    series = models.ForeignKey(DicomSeries, related_name='neurological_analyses', on_delete=models.CASCADE)
    brain_segmentation = models.JSONField(default=dict)  # Segmented brain regions
    lesion_detection = models.JSONField(default=list)  # Detected lesions
    brain_volume_analysis = models.JSONField(default=dict)  # Volume measurements
    white_matter_analysis = models.JSONField(default=dict)  # White matter integrity
    vascular_analysis = models.JSONField(default=dict)  # Cerebral vessels
    atrophy_analysis = models.JSONField(default=dict)  # Brain atrophy measurements
    symmetry_analysis = models.JSONField(default=dict)  # Brain symmetry analysis
    hemorrhage_detection = models.JSONField(default=list)  # Detected hemorrhages
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Neurological Analysis for {self.series}"


class OrthopedicAnalysis(models.Model):
    """Model for orthopedic imaging analysis"""
    JOINT_TYPES = [
        ('knee', 'Knee Joint'),
        ('hip', 'Hip Joint'),
        ('shoulder', 'Shoulder Joint'),
        ('elbow', 'Elbow Joint'),
        ('wrist', 'Wrist Joint'),
        ('ankle', 'Ankle Joint'),
        ('spine', 'Spinal Joints'),
        ('temporomandibular', 'TMJ'),
    ]
    
    series = models.ForeignKey(DicomSeries, related_name='orthopedic_analyses', on_delete=models.CASCADE)
    joint_type = models.CharField(max_length=20, choices=JOINT_TYPES)
    joint_space_measurements = models.JSONField(default=dict)  # Joint space width
    cartilage_analysis = models.JSONField(default=dict)  # Cartilage thickness and quality
    bone_quality_analysis = models.JSONField(default=dict)  # Bone density and quality
    alignment_analysis = models.JSONField(default=dict)  # Joint alignment measurements
    arthritis_assessment = models.JSONField(default=dict)  # Arthritis severity
    implant_analysis = models.JSONField(default=dict)  # For post-surgical cases
    range_of_motion = models.JSONField(default=dict)  # If dynamic imaging
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Orthopedic Analysis {self.joint_type} for {self.series}"


class AIChat(models.Model):
    """Model for AI-powered chat assistant"""
    MESSAGE_TYPES = [
        ('user', 'User Message'),
        ('ai', 'AI Response'),
        ('system', 'System Message'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_chats')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    message = models.TextField()
    context_study = models.ForeignKey(DicomStudy, on_delete=models.SET_NULL, null=True, blank=True)
    context_image = models.ForeignKey(DicomImage, on_delete=models.SET_NULL, null=True, blank=True)
    ai_confidence = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(default=dict)  # Store additional context
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.message_type} from {self.user.username}: {self.message[:50]}"


class SmartMeasurement(models.Model):
    """Model for AI-powered smart measurements"""
    MEASUREMENT_TYPES = [
        ('distance', 'Distance Measurement'),
        ('area', 'Area Measurement'),
        ('volume', 'Volume Measurement'),
        ('angle', 'Angle Measurement'),
        ('hounsfield', 'Hounsfield Units'),
        ('density', 'Density Measurement'),
        ('organ_volume', 'Organ Volume'),
        ('lesion_size', 'Lesion Size'),
    ]
    
    image = models.ForeignKey(DicomImage, related_name='smart_measurements', on_delete=models.CASCADE)
    measurement_type = models.CharField(max_length=20, choices=MEASUREMENT_TYPES)
    coordinates = models.JSONField()  # Store measurement coordinates
    value = models.FloatField()
    unit = models.CharField(max_length=20)
    ai_detected = models.BooleanField(default=False)  # Whether AI automatically detected this
    confidence_score = models.FloatField(null=True, blank=True)
    anatomical_structure = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.measurement_type} on {self.image}: {self.value} {self.unit}"


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

    def apply_diagnostic_preprocessing(self, pixel_array):
        """Apply diagnostic-grade preprocessing for superior image quality"""
        try:
            from scipy.ndimage import median_filter, gaussian_filter
            from scipy.signal import wiener
            
            # Convert to float for precision
            pixel_array = pixel_array.astype(np.float32)
            
            # Apply noise reduction while preserving diagnostic details
            # Use adaptive filtering based on image characteristics
            noise_level = np.std(pixel_array)
            if noise_level > 10:  # High noise image
                # Wiener filter for noise reduction
                pixel_array = wiener(pixel_array, (3, 3))
            elif noise_level > 5:  # Moderate noise
                # Gaussian filter with small kernel
                pixel_array = gaussian_filter(pixel_array, sigma=0.5)
            
            # Edge-preserving smoothing for diagnostic clarity
            pixel_array = self.apply_edge_preserving_smoothing(pixel_array)
            
            # Normalize for optimal processing
            pixel_array = self.normalize_for_diagnostic_processing(pixel_array)
            
            return pixel_array
            
        except Exception as e:
            print(f"Error in diagnostic preprocessing: {e}")
            return pixel_array

    def apply_diagnostic_windowing(self, pixel_array, window_width=None, window_level=None, inverted=False,
                                  density_enhancement=True, contrast_boost=1.5):
        """Apply diagnostic-grade windowing with superior tissue differentiation"""
        try:
            # Use optimal defaults for diagnostic imaging
            if window_width is None:
                window_width = self.window_width or 1500
            if window_level is None:
                window_level = self.window_center or -600
            
            # Convert to float for precision
            pixel_array = pixel_array.astype(np.float32)
            
            # Apply diagnostic contrast enhancement
            if contrast_boost != 1.0:
                pixel_array = self.apply_diagnostic_contrast_enhancement(pixel_array, contrast_boost, window_level)
            
            # Apply diagnostic windowing with gamma correction
            window_min = window_level - window_width / 2
            window_max = window_level + window_width / 2
            
            # Clip values to window range
            pixel_array = np.clip(pixel_array, window_min, window_max)
            
            # Apply diagnostic non-linear windowing for superior tissue visualization
            if density_enhancement:
                pixel_array = self.apply_diagnostic_nonlinear_windowing(pixel_array, window_min, window_max)
            else:
                # Enhanced linear windowing with gamma correction
                pixel_array = self.apply_enhanced_linear_windowing(pixel_array, window_min, window_max)
            
            # Apply diagnostic density enhancement
            if density_enhancement:
                pixel_array = self.apply_diagnostic_density_enhancement(pixel_array)
            
            # Apply inversion if requested
            if inverted:
                pixel_array = 255 - pixel_array
            
            # Final diagnostic enhancement
            pixel_array = self.apply_final_diagnostic_enhancement(pixel_array)
            
            return pixel_array
            
        except Exception as e:
            print(f"Error in diagnostic windowing: {e}")
            return pixel_array

    def apply_diagnostic_resolution_enhancement(self, pixel_array, resolution_factor):
        """Apply diagnostic-grade resolution enhancement"""
        try:
            from scipy.ndimage import zoom
            
            # Use Lanczos interpolation for superior quality
            enhanced_array = zoom(pixel_array, resolution_factor, order=3)
            
            # Apply edge enhancement for diagnostic clarity
            enhanced_array = self.apply_diagnostic_edge_enhancement(enhanced_array)
            
            return enhanced_array
            
        except Exception as e:
            print(f"Error in diagnostic resolution enhancement: {e}")
            return pixel_array

    def apply_advanced_tissue_differentiation(self, pixel_array):
        """Apply advanced tissue differentiation for superior diagnostic capability"""
        try:
            # Multi-scale tissue analysis
            tissue_enhanced = self.apply_multi_scale_tissue_analysis(pixel_array)
            
            # Adaptive contrast enhancement based on tissue characteristics
            tissue_enhanced = self.apply_adaptive_tissue_contrast(tissue_enhanced)
            
            # Local contrast enhancement for diagnostic details
            tissue_enhanced = self.apply_local_diagnostic_contrast(tissue_enhanced)
            
            return tissue_enhanced
            
        except Exception as e:
            print(f"Error in advanced tissue differentiation: {e}")
            return pixel_array

    def apply_diagnostic_quality_enhancement(self, image):
        """Apply final diagnostic quality enhancements"""
        try:
            # Basic quality enhancement that won't fail
            import numpy as np
            from PIL import Image, ImageEnhance
            
            # If it's a numpy array, convert to PIL Image
            if isinstance(image, np.ndarray):
                if len(image.shape) == 2:
                    pil_image = Image.fromarray(image.astype(np.uint8), mode='L')
                else:
                    pil_image = Image.fromarray(image.astype(np.uint8))
            else:
                pil_image = image
            
            # Apply basic contrast enhancement
            enhancer = ImageEnhance.Contrast(pil_image)
            enhanced = enhancer.enhance(1.2)  # 20% contrast boost
            
            # Apply basic sharpness enhancement
            sharpness_enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = sharpness_enhancer.enhance(1.1)  # 10% sharpness boost
            
            return enhanced
            
        except Exception as e:
            print(f"Error in diagnostic quality enhancement: {e}")
            return image
    
    def apply_diagnostic_quality_enhancement_robust(self, image):
        """Robust version of diagnostic quality enhancement with better error handling"""
        try:
            # Check if the method exists
            if not hasattr(self, 'apply_diagnostic_quality_enhancement'):
                print("Warning: apply_diagnostic_quality_enhancement method not found, using fallback")
                return self._apply_basic_enhancement(image)
            
            return self.apply_diagnostic_quality_enhancement(image)
        except Exception as e:
            print(f"Error in robust diagnostic quality enhancement: {e}")
            return self._apply_basic_enhancement(image)
    
    def _apply_basic_enhancement(self, image):
        """Basic image enhancement fallback"""
        try:
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            return enhancer.enhance(1.1)
        except Exception as e:
            print(f"Basic enhancement failed: {e}")
            return image
    
    def apply_diagnostic_unsharp_masking(self, image):
        """Simple unsharp masking fallback"""
        try:
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Sharpness(image)
            return enhancer.enhance(1.1)
        except:
            return image
    
    def apply_diagnostic_contrast_enhancement_final(self, image):
        """Simple contrast enhancement fallback"""
        try:
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            return enhancer.enhance(1.1)
        except:
            return image
    
    def apply_diagnostic_edge_preservation(self, image):
        """Simple edge preservation fallback"""
        return image  # Just return as-is for simplicity

    def apply_edge_preserving_smoothing(self, pixel_array):
        """Apply edge-preserving smoothing for diagnostic clarity"""
        try:
            from scipy.ndimage import median_filter
            
            # Apply bilateral filtering concept using median filter
            # This preserves edges while reducing noise
            smoothed = median_filter(pixel_array, size=3)
            
            # Preserve strong edges
            edge_mask = np.abs(pixel_array - smoothed) > np.std(pixel_array) * 0.5
            result = np.where(edge_mask, pixel_array, smoothed)
            
            return result
            
        except Exception as e:
            print(f"Error in edge-preserving smoothing: {e}")
            return pixel_array

    def normalize_for_diagnostic_processing(self, pixel_array):
        """Normalize pixel array for optimal diagnostic processing"""
        try:
            # Remove outliers for stable processing
            percentile_1 = np.percentile(pixel_array, 1)
            percentile_99 = np.percentile(pixel_array, 99)
            normalized = np.clip(pixel_array, percentile_1, percentile_99)
            
            # Normalize to 0-1 range
            normalized = (normalized - normalized.min()) / (normalized.max() - normalized.min())
            
            return normalized
            
        except Exception as e:
            print(f"Error in diagnostic normalization: {e}")
            return pixel_array

    def apply_diagnostic_contrast_enhancement(self, pixel_array, contrast_boost, window_level):
        """Apply diagnostic-grade contrast enhancement"""
        try:
            # Adaptive contrast enhancement based on tissue characteristics
            mean_intensity = np.mean(pixel_array)
            std_intensity = np.std(pixel_array)
            
            # Calculate adaptive contrast factor
            adaptive_factor = contrast_boost * (1 + (std_intensity / mean_intensity) * 0.5)
            
            # Apply contrast enhancement
            enhanced = (pixel_array - mean_intensity) * adaptive_factor + mean_intensity
            
            # Ensure values stay in valid range
            enhanced = np.clip(enhanced, pixel_array.min(), pixel_array.max())
            
            return enhanced
            
        except Exception as e:
            print(f"Error in diagnostic contrast enhancement: {e}")
            return pixel_array

    def apply_diagnostic_nonlinear_windowing(self, pixel_array, window_min, window_max):
        """Apply diagnostic non-linear windowing for superior tissue visualization"""
        try:
            # Apply S-curve enhancement for better tissue differentiation
            normalized = (pixel_array - window_min) / (window_max - window_min)
            normalized = np.clip(normalized, 0, 1)
            
            # Apply diagnostic S-curve
            enhanced = self.apply_diagnostic_s_curve(normalized)
            
            # Scale to 0-255 range
            result = enhanced * 255
            
            return result
            
        except Exception as e:
            print(f"Error in diagnostic non-linear windowing: {e}")
            return pixel_array

    def apply_enhanced_linear_windowing(self, pixel_array, window_min, window_max):
        """Apply enhanced linear windowing with gamma correction"""
        try:
            # Linear windowing with gamma correction
            normalized = (pixel_array - window_min) / (window_max - window_min)
            normalized = np.clip(normalized, 0, 1)
            
            # Apply gamma correction for better tissue visualization
            gamma = 0.8  # Slightly darker for better contrast
            enhanced = np.power(normalized, gamma)
            
            # Scale to 0-255 range
            result = enhanced * 255
            
            return result
            
        except Exception as e:
            print(f"Error in enhanced linear windowing: {e}")
            return pixel_array

    def apply_diagnostic_density_enhancement(self, pixel_array):
        """Apply diagnostic-grade density enhancement"""
        try:
            # Multi-scale density analysis
            enhanced = self.apply_multi_scale_density_analysis(pixel_array)
            
            # Adaptive density enhancement
            enhanced = self.apply_adaptive_density_enhancement(enhanced)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in diagnostic density enhancement: {e}")
            return pixel_array

    def apply_final_diagnostic_enhancement(self, pixel_array):
        """Apply final diagnostic enhancement for superior quality"""
        try:
            # Apply local contrast enhancement
            enhanced = self.apply_local_diagnostic_contrast(pixel_array)
            
            # Apply edge enhancement for diagnostic clarity
            enhanced = self.apply_diagnostic_edge_enhancement(enhanced)
            
            # Apply final quality optimization
            enhanced = self.apply_diagnostic_quality_optimization(enhanced)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in final diagnostic enhancement: {e}")
            return pixel_array

    def apply_diagnostic_s_curve(self, normalized_array):
        """Apply diagnostic S-curve for superior tissue differentiation"""
        try:
            # Diagnostic S-curve parameters
            alpha = 0.3  # Controls the steepness
            beta = 0.5   # Controls the center point
            
            # Apply S-curve transformation
            enhanced = 1 / (1 + np.exp(-alpha * (normalized_array - beta)))
            
            # Normalize to 0-1 range
            enhanced = (enhanced - enhanced.min()) / (enhanced.max() - enhanced.min())
            
            return enhanced
            
        except Exception as e:
            print(f"Error in diagnostic S-curve: {e}")
            return normalized_array

    def apply_multi_scale_density_analysis(self, pixel_array):
        """Apply multi-scale density analysis for superior tissue differentiation"""
        try:
            from scipy.ndimage import gaussian_filter
            
            # Multi-scale analysis
            scales = [1, 2, 4]
            multi_scale_result = np.zeros_like(pixel_array)
            
            for scale in scales:
                # Apply Gaussian filter at different scales
                filtered = gaussian_filter(pixel_array, sigma=scale)
                
                # Weight based on scale (finer scales get higher weight)
                weight = 1.0 / scale
                multi_scale_result += weight * filtered
            
            # Normalize result
            multi_scale_result /= len(scales)
            
            return multi_scale_result
            
        except Exception as e:
            print(f"Error in multi-scale density analysis: {e}")
            return pixel_array

    def apply_adaptive_density_enhancement(self, pixel_array):
        """Apply adaptive density enhancement based on local characteristics"""
        try:
            # Calculate local statistics
            from scipy.ndimage import uniform_filter
            
            # Local mean
            local_mean = uniform_filter(pixel_array, size=15)
            
            # Local standard deviation
            local_var = uniform_filter(pixel_array**2, size=15) - local_mean**2
            local_std = np.sqrt(np.maximum(local_var, 0))
            
            # Adaptive enhancement
            enhanced = pixel_array + 0.5 * local_std
            
            # Ensure values stay in valid range
            enhanced = np.clip(enhanced, 0, 255)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in adaptive density enhancement: {e}")
            return pixel_array

    def apply_local_diagnostic_contrast(self, pixel_array):
        """Apply local contrast enhancement for diagnostic details"""
        try:
            from scipy.ndimage import uniform_filter
            
            # Calculate local mean
            local_mean = uniform_filter(pixel_array, size=9)
            
            # Calculate local contrast
            local_contrast = pixel_array - local_mean
            
            # Enhance local contrast
            enhanced_contrast = local_contrast * 1.2
            
            # Add back to local mean
            enhanced = local_mean + enhanced_contrast
            
            # Ensure values stay in valid range
            enhanced = np.clip(enhanced, 0, 255)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in local diagnostic contrast: {e}")
            return pixel_array

    def apply_diagnostic_edge_enhancement(self, pixel_array):
        """Apply diagnostic edge enhancement for clarity"""
        try:
            from scipy.ndimage import gaussian_filter
            
            # Apply Gaussian blur
            blurred = gaussian_filter(pixel_array, sigma=1.0)
            
            # Calculate edge map
            edge_map = pixel_array - blurred
            
            # Enhance edges
            enhanced_edges = edge_map * 0.3
            
            # Add enhanced edges back
            enhanced = pixel_array + enhanced_edges
            
            # Ensure values stay in valid range
            enhanced = np.clip(enhanced, 0, 255)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in diagnostic edge enhancement: {e}")
            return pixel_array

    def apply_diagnostic_quality_optimization(self, pixel_array):
        """Apply final diagnostic quality optimization"""
        try:
            # Apply histogram equalization for optimal contrast
            from skimage import exposure
            
            # Adaptive histogram equalization
            enhanced = exposure.equalize_adapthist(pixel_array.astype(np.float32), clip_limit=0.02)
            
            # Scale to 0-255 range
            enhanced = (enhanced * 255).astype(np.uint8)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in diagnostic quality optimization: {e}")
            return pixel_array

    def apply_diagnostic_unsharp_masking(self, image):
        """Apply diagnostic unsharp masking for clarity"""
        try:
            from PIL import ImageFilter
            
            # Apply unsharp mask filter
            enhanced = image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
            
            return enhanced
            
        except Exception as e:
            print(f"Error in diagnostic unsharp masking: {e}")
            return image

    def apply_diagnostic_contrast_enhancement_final(self, image):
        """Apply final diagnostic contrast enhancement"""
        try:
            from PIL import ImageEnhance
            
            # Apply contrast enhancement
            enhancer = ImageEnhance.Contrast(image)
            enhanced = enhancer.enhance(1.1)  # Slight contrast boost
            
            return enhanced
            
        except Exception as e:
            print(f"Error in diagnostic contrast enhancement final: {e}")
            return image

    def apply_diagnostic_edge_preservation(self, image):
        """Apply diagnostic edge preservation"""
        try:
            from PIL import ImageFilter
            
            # Apply edge enhancement filter
            enhanced = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
            
            # Blend with original for natural appearance
            enhanced = Image.blend(image, enhanced, 0.3)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in diagnostic edge preservation: {e}")
            return image

    def apply_multi_scale_tissue_analysis(self, pixel_array):
        """Apply multi-scale tissue analysis for superior diagnostic capability"""
        try:
            from scipy.ndimage import gaussian_filter
            
            # Multi-scale analysis for tissue differentiation
            scales = [1, 2, 4, 8]
            multi_scale_result = np.zeros_like(pixel_array)
            
            for scale in scales:
                # Apply Gaussian filter at different scales
                filtered = gaussian_filter(pixel_array, sigma=scale)
                
                # Weight based on scale (finer scales get higher weight for detail preservation)
                weight = 1.0 / scale
                multi_scale_result += weight * filtered
            
            # Normalize result
            multi_scale_result /= len(scales)
            
            return multi_scale_result
            
        except Exception as e:
            print(f"Error in multi-scale tissue analysis: {e}")
            return pixel_array

    def apply_adaptive_tissue_contrast(self, pixel_array):
        """Apply adaptive contrast enhancement based on tissue characteristics"""
        try:
            # Calculate tissue-specific contrast parameters
            mean_intensity = np.mean(pixel_array)
            std_intensity = np.std(pixel_array)
            
            # Adaptive contrast factor based on tissue characteristics
            if mean_intensity < 50:  # Dark tissue (bone, air)
                contrast_factor = 1.3
            elif mean_intensity > 200:  # Bright tissue (contrast, metal)
                contrast_factor = 1.1
            else:  # Soft tissue
                contrast_factor = 1.2
            
            # Apply adaptive contrast enhancement
            enhanced = (pixel_array - mean_intensity) * contrast_factor + mean_intensity
            
            # Ensure values stay in valid range
            enhanced = np.clip(enhanced, 0, 255)
            
            return enhanced
            
        except Exception as e:
            print(f"Error in adaptive tissue contrast: {e}")
            return pixel_array


class AttachedStudy(models.Model):
    """Model for attaching previous studies for comparison and follow-up"""
    ATTACHMENT_TYPES = [
        ('comparison', 'Comparison Study'),
        ('followup', 'Follow-up Study'),
        ('baseline', 'Baseline Study'),
        ('reference', 'Reference Study'),
    ]
    
    # Current study
    current_study = models.ForeignKey(DicomStudy, related_name='attached_studies', on_delete=models.CASCADE)
    
    # Previous study (can be another DICOM study or external)
    previous_study = models.ForeignKey(DicomStudy, related_name='referenced_by', on_delete=models.CASCADE, null=True, blank=True)
    
    # External study files (for non-DICOM studies)
    external_dicom_file = models.FileField(upload_to='attached_studies/dicom/', null=True, blank=True)
    external_report_file = models.FileField(upload_to='attached_studies/reports/', null=True, blank=True)
    
    # Metadata
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES, default='comparison')
    study_date = models.DateField(null=True, blank=True)
    study_description = models.CharField(max_length=200, blank=True)
    modality = models.CharField(max_length=10, blank=True)
    institution_name = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True, help_text="Notes about this attachment")
    
    # Timestamps
    attached_at = models.DateTimeField(auto_now_add=True)
    attached_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-attached_at']
        verbose_name = "Attached Study"
        verbose_name_plural = "Attached Studies"
    
    def __str__(self):
        if self.previous_study:
            return f"{self.get_attachment_type_display()}: {self.previous_study.patient_name} - {self.previous_study.study_date}"
        else:
            return f"{self.get_attachment_type_display()}: External Study - {self.study_date}"
    
    @property
    def has_dicom_files(self):
        """Check if this attachment has DICOM files available"""
        return bool(self.previous_study or self.external_dicom_file)
    
    @property
    def has_report(self):
        """Check if this attachment has a report available"""
        if self.previous_study and self.previous_study.reports.exists():
            return True
        return bool(self.external_report_file)


class StudyComparison(models.Model):
    """Model for storing study comparison sessions"""
    primary_study = models.ForeignKey(DicomStudy, related_name='primary_comparisons', on_delete=models.CASCADE)
    comparison_study = models.ForeignKey(DicomStudy, related_name='comparison_sessions', on_delete=models.CASCADE)
    
    # Comparison settings
    comparison_mode = models.CharField(max_length=20, choices=[
        ('side_by_side', 'Side by Side'),
        ('overlay', 'Overlay'),
        ('toggle', 'Toggle'),
        ('linked', 'Linked Viewing'),
    ], default='side_by_side')
    
    # Session metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['primary_study', 'comparison_study', 'created_by']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comparison: {self.primary_study.patient_name} vs {self.comparison_study.patient_name}"


class UserProfile(models.Model):
    """User profile for storing viewer settings and preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='viewer_profile')
    settings = models.JSONField(default=dict, blank=True, help_text="User's viewer settings and preferences")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.username} Profile"