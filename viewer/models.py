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
                
            # Try reading with multiple methods
            try:
                # Method 1: Standard reading
                return pydicom.dcmread(file_path)
            except Exception as e1:
                print(f"Standard DICOM reading failed: {e1}")
                try:
                    # Method 2: Force reading (more permissive)
                    return pydicom.dcmread(file_path, force=True)
                except Exception as e2:
                    print(f"Force DICOM reading failed: {e2}")
                    try:
                        # Method 3: Read as bytes
                        with open(file_path, 'rb') as f:
                            file_bytes = f.read()
                        return pydicom.dcmread(io.BytesIO(file_bytes), force=True)
                    except Exception as e3:
                        print(f"Bytes DICOM reading failed: {e3}")
                        return None
                        
        except Exception as e:
            print(f"Error loading DICOM from {self.file_path}: {e}")
            print(f"Attempted file path: {file_path if 'file_path' in locals() else 'unknown'}")
            return None
    
    def get_pixel_array(self):
        """Get pixel array from DICOM file"""
        try:
            dicom_data = self.load_dicom_data()
            if dicom_data and hasattr(dicom_data, 'pixel_array'):
                return dicom_data.pixel_array
            else:
                print(f"No pixel array found in DICOM data for image {self.id}")
                return None
        except Exception as e:
            print(f"Error getting pixel array for image {self.id}: {e}")
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
                                          resolution_factor=1.0, density_enhancement=False, contrast_boost=1.0, thumbnail_size=None):
        """Get enhanced processed image with superior quality for medical imaging"""
        try:
            # Get pixel data
            pixel_array = self.get_pixel_array()
            if pixel_array is None:
                return None
            
            # Apply enhanced windowing with density differentiation
            processed_array = self.apply_enhanced_windowing(
                pixel_array, window_width, window_level, inverted, 
                density_enhancement, contrast_boost
            )
            
            # Apply resolution enhancement if requested
            if resolution_factor != 1.0:
                processed_array = self.apply_resolution_enhancement(processed_array, resolution_factor)
            
            # Apply density differentiation if requested
            if density_enhancement:
                processed_array = self.apply_density_differentiation(processed_array)
            
            # Convert to PIL Image with superior quality
            if processed_array.dtype != np.uint8:
                processed_array = np.clip(processed_array, 0, 255).astype(np.uint8)
            
            image = Image.fromarray(processed_array, mode='L')
            
            # Apply final quality enhancements
            image = self.apply_final_quality_enhancement(image)
            
            # Resize for thumbnail if requested
            if thumbnail_size:
                image = image.resize(thumbnail_size, Image.Resampling.LANCZOS)
            
            # Convert to base64 with maximum quality
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', optimize=False, compress_level=0)  # No compression for maximum quality
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error processing enhanced image {self.id}: {e}")
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