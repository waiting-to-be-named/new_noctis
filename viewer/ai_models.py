# viewer/ai_models.py
import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
import logging
from django.conf import settings
from .models import DicomImage

logger = logging.getLogger(__name__)


class MedicalImageAnalyzer:
    """
    AI-powered medical image analysis class
    Provides basic image enhancement and analysis capabilities
    """
    
    def __init__(self):
        self.enabled = getattr(settings, 'ENABLE_AI_FEATURES', False)
        
    def enhance_contrast(self, pixel_array: np.ndarray) -> np.ndarray:
        """
        Apply Contrast Limited Adaptive Histogram Equalization (CLAHE)
        for better medical image contrast
        """
        if not self.enabled:
            return pixel_array
            
        try:
            # Convert to uint8 if needed
            if pixel_array.dtype != np.uint8:
                pixel_array = ((pixel_array - pixel_array.min()) / 
                             (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
            
            # Apply CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(pixel_array)
            
            logger.info("Successfully applied CLAHE enhancement")
            return enhanced
            
        except Exception as e:
            logger.error(f"Error in contrast enhancement: {e}")
            return pixel_array
    
    def denoise_image(self, pixel_array: np.ndarray) -> np.ndarray:
        """
        Apply non-local means denoising for medical images
        """
        if not self.enabled:
            return pixel_array
            
        try:
            # Convert to uint8 if needed
            if pixel_array.dtype != np.uint8:
                pixel_array = ((pixel_array - pixel_array.min()) / 
                             (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
            
            # Apply non-local means denoising
            denoised = cv2.fastNlMeansDenoising(pixel_array, None, 10, 7, 21)
            
            logger.info("Successfully applied denoising")
            return denoised
            
        except Exception as e:
            logger.error(f"Error in denoising: {e}")
            return pixel_array
    
    def detect_edges(self, pixel_array: np.ndarray) -> np.ndarray:
        """
        Detect edges using Canny edge detection
        Useful for anatomical structure identification
        """
        if not self.enabled:
            return pixel_array
            
        try:
            # Convert to uint8 if needed
            if pixel_array.dtype != np.uint8:
                pixel_array = ((pixel_array - pixel_array.min()) / 
                             (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
            
            # Apply Gaussian blur first
            blurred = cv2.GaussianBlur(pixel_array, (5, 5), 0)
            
            # Apply Canny edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            logger.info("Successfully detected edges")
            return edges
            
        except Exception as e:
            logger.error(f"Error in edge detection: {e}")
            return pixel_array
    
    def analyze_histogram(self, pixel_array: np.ndarray) -> Dict:
        """
        Analyze pixel intensity histogram for tissue characterization
        """
        if not self.enabled:
            return {}
            
        try:
            # Calculate histogram
            hist, bins = np.histogram(pixel_array.flatten(), bins=256, range=[0, 256])
            
            # Calculate statistics
            mean_intensity = np.mean(pixel_array)
            std_intensity = np.std(pixel_array)
            min_intensity = np.min(pixel_array)
            max_intensity = np.max(pixel_array)
            
            # Find peaks in histogram (potential tissue types)
            from scipy.signal import find_peaks
            peaks, properties = find_peaks(hist, height=np.max(hist) * 0.1)
            
            analysis_result = {
                'mean_intensity': float(mean_intensity),
                'std_intensity': float(std_intensity),
                'min_intensity': float(min_intensity),
                'max_intensity': float(max_intensity),
                'histogram': hist.tolist(),
                'bins': bins.tolist(),
                'tissue_peaks': peaks.tolist(),
                'peak_heights': hist[peaks].tolist()
            }
            
            logger.info("Successfully analyzed histogram")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in histogram analysis: {e}")
            return {}
    
    def suggest_window_level(self, pixel_array: np.ndarray, 
                           modality: str = 'CT') -> Dict[str, float]:
        """
        AI-suggested optimal window/level settings based on image content
        """
        if not self.enabled:
            return {}
            
        try:
            # Calculate basic statistics
            mean_val = np.mean(pixel_array)
            std_val = np.std(pixel_array)
            percentile_5 = np.percentile(pixel_array, 5)
            percentile_95 = np.percentile(pixel_array, 95)
            
            suggestions = {}
            
            if modality.upper() == 'CT':
                # CT-specific suggestions
                suggestions['soft_tissue'] = {
                    'window_width': std_val * 4,
                    'window_level': mean_val
                }
                suggestions['bone'] = {
                    'window_width': percentile_95 - percentile_5,
                    'window_level': (percentile_95 + percentile_5) / 2
                }
                suggestions['lung'] = {
                    'window_width': std_val * 6,
                    'window_level': mean_val - std_val
                }
            else:
                # General suggestions
                suggestions['auto'] = {
                    'window_width': percentile_95 - percentile_5,
                    'window_level': (percentile_95 + percentile_5) / 2
                }
            
            logger.info(f"Generated window/level suggestions for {modality}")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error in window/level suggestion: {e}")
            return {}
    
    def basic_anomaly_detection(self, pixel_array: np.ndarray) -> Dict:
        """
        Basic anomaly detection using statistical methods
        Note: This is a simplified approach for demonstration
        """
        if not self.enabled:
            return {}
            
        try:
            # Calculate z-scores
            mean_val = np.mean(pixel_array)
            std_val = np.std(pixel_array)
            z_scores = np.abs((pixel_array - mean_val) / std_val)
            
            # Find potential anomalies (z-score > 3)
            anomaly_threshold = 3.0
            anomaly_mask = z_scores > anomaly_threshold
            anomaly_count = np.sum(anomaly_mask)
            
            # Calculate anomaly percentage
            total_pixels = pixel_array.size
            anomaly_percentage = (anomaly_count / total_pixels) * 100
            
            # Find connected components of anomalies
            anomaly_uint8 = anomaly_mask.astype(np.uint8) * 255
            num_labels, labels = cv2.connectedComponents(anomaly_uint8)
            
            result = {
                'anomaly_count': int(anomaly_count),
                'anomaly_percentage': float(anomaly_percentage),
                'num_anomaly_regions': int(num_labels - 1),  # Subtract background
                'threshold_used': anomaly_threshold,
                'has_potential_anomalies': anomaly_percentage > 1.0  # More than 1% anomalies
            }
            
            logger.info(f"Anomaly detection completed: {anomaly_percentage:.2f}% anomalies found")
            return result
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return {}


def analyze_dicom_image(image_id: int, analysis_type: str = 'basic') -> Dict:
    """
    Analyze a DICOM image using AI models
    
    Args:
        image_id: ID of the DicomImage to analyze
        analysis_type: Type of analysis ('basic', 'contrast', 'denoise', 'edges', 'histogram', 'anomaly')
    
    Returns:
        Dict containing analysis results
    """
    try:
        image = DicomImage.objects.get(id=image_id)
        pixel_array = image.get_pixel_array()
        
        if pixel_array is None:
            return {'error': 'Could not load pixel data'}
        
        analyzer = MedicalImageAnalyzer()
        
        if analysis_type == 'contrast':
            enhanced = analyzer.enhance_contrast(pixel_array)
            return {'enhanced_image': enhanced.tolist()}
            
        elif analysis_type == 'denoise':
            denoised = analyzer.denoise_image(pixel_array)
            return {'denoised_image': denoised.tolist()}
            
        elif analysis_type == 'edges':
            edges = analyzer.detect_edges(pixel_array)
            return {'edge_image': edges.tolist()}
            
        elif analysis_type == 'histogram':
            return analyzer.analyze_histogram(pixel_array)
            
        elif analysis_type == 'window_suggest':
            return analyzer.suggest_window_level(pixel_array, image.series.modality)
            
        elif analysis_type == 'anomaly':
            return analyzer.basic_anomaly_detection(pixel_array)
            
        else:  # basic analysis
            result = {
                'histogram_analysis': analyzer.analyze_histogram(pixel_array),
                'window_suggestions': analyzer.suggest_window_level(pixel_array, image.series.modality),
                'anomaly_detection': analyzer.basic_anomaly_detection(pixel_array)
            }
            return result
            
    except DicomImage.DoesNotExist:
        return {'error': 'DICOM image not found'}
    except Exception as e:
        logger.error(f"Error in DICOM image analysis: {e}")
        return {'error': str(e)}