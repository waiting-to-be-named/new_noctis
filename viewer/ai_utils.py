"""
AI utilities for DICOM image analysis
"""
import numpy as np
import cv2
from sklearn.cluster import KMeans
from scipy import ndimage
from skimage import filters, morphology, measure
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DicomImageAnalyzer:
    """AI-powered DICOM image analysis"""
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    def detect_anomalies(self, image_array: np.ndarray, threshold: float = 0.7) -> Dict:
        """
        Detect potential anomalies in medical images using computer vision
        """
        try:
            # Preprocess image
            processed = self._preprocess_image(image_array)
            
            # Apply various detection methods
            edges = self._detect_edges(processed)
            regions = self._segment_regions(processed)
            anomalies = self._identify_anomalies(processed, regions)
            
            # Calculate confidence scores
            confidence = self._calculate_confidence(anomalies, processed)
            
            return {
                'anomalies_detected': len(anomalies) > 0,
                'anomaly_regions': anomalies,
                'confidence': confidence,
                'edge_map': edges,
                'segmented_regions': regions
            }
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return {'error': str(e)}
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for analysis"""
        # Normalize to 0-255 range
        if image.dtype != np.uint8:
            image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(np.uint8)
        
        # Apply CLAHE for contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(enhanced)
        
        return denoised
    
    def _detect_edges(self, image: np.ndarray) -> np.ndarray:
        """Detect edges using multiple algorithms"""
        # Canny edge detection
        edges_canny = cv2.Canny(image, 50, 150)
        
        # Sobel edge detection
        sobel_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        edges_sobel = np.sqrt(sobel_x**2 + sobel_y**2)
        
        # Combine edge maps
        combined_edges = cv2.addWeighted(edges_canny, 0.5, edges_sobel.astype(np.uint8), 0.5, 0)
        
        return combined_edges
    
    def _segment_regions(self, image: np.ndarray) -> List[Dict]:
        """Segment image into regions of interest"""
        # Apply threshold
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > 100:  # Filter small regions
                x, y, w, h = cv2.boundingRect(contour)
                regions.append({
                    'id': i,
                    'bbox': [x, y, w, h],
                    'area': area,
                    'centroid': [x + w//2, y + h//2]
                })
        
        return regions
    
    def _identify_anomalies(self, image: np.ndarray, regions: List[Dict]) -> List[Dict]:
        """Identify potential anomalies in regions"""
        anomalies = []
        
        for region in regions:
            x, y, w, h = region['bbox']
            roi = image[y:y+h, x:x+w]
            
            # Calculate features
            mean_intensity = np.mean(roi)
            std_intensity = np.std(roi)
            texture_score = self._calculate_texture_score(roi)
            
            # Simple anomaly detection based on features
            if std_intensity > 30 and texture_score > 0.5:
                anomalies.append({
                    **region,
                    'mean_intensity': float(mean_intensity),
                    'std_intensity': float(std_intensity),
                    'texture_score': float(texture_score)
                })
        
        return anomalies
    
    def _calculate_texture_score(self, roi: np.ndarray) -> float:
        """Calculate texture complexity score"""
        # Use Gabor filters for texture analysis
        kernels = []
        for theta in np.arange(0, np.pi, np.pi / 4):
            kernel = cv2.getGaborKernel((21, 21), 4.0, theta, 10.0, 0.5, 0, ktype=cv2.CV_32F)
            kernels.append(kernel)
        
        responses = []
        for kernel in kernels:
            filtered = cv2.filter2D(roi, cv2.CV_8UC3, kernel)
            responses.append(filtered.var())
        
        return np.mean(responses) / 255.0
    
    def _calculate_confidence(self, anomalies: List[Dict], image: np.ndarray) -> float:
        """Calculate overall confidence score"""
        if not anomalies:
            return 0.0
        
        # Base confidence on number and characteristics of anomalies
        base_confidence = min(len(anomalies) * 0.2, 0.8)
        
        # Adjust based on image quality
        quality_score = self._assess_image_quality(image)
        
        return min(base_confidence * quality_score, 1.0)
    
    def _assess_image_quality(self, image: np.ndarray) -> float:
        """Assess image quality for confidence adjustment"""
        # Check contrast
        contrast = image.std() / 255.0
        
        # Check sharpness using Laplacian
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        sharpness = laplacian.var() / 1000.0
        
        # Combine metrics
        quality = (contrast + sharpness) / 2.0
        return np.clip(quality, 0.1, 1.0)
    
    def enhance_image(self, image_array: np.ndarray, enhancement_type: str = 'auto') -> np.ndarray:
        """
        Apply various enhancement techniques to improve image quality
        """
        if enhancement_type == 'auto':
            return self._auto_enhance(image_array)
        elif enhancement_type == 'contrast':
            return self._enhance_contrast(image_array)
        elif enhancement_type == 'denoise':
            return self._denoise_image(image_array)
        elif enhancement_type == 'sharpen':
            return self._sharpen_image(image_array)
        else:
            return image_array
    
    def _auto_enhance(self, image: np.ndarray) -> np.ndarray:
        """Automatically enhance image based on its characteristics"""
        # Assess image and apply appropriate enhancements
        enhanced = image.copy()
        
        # Apply CLAHE
        if image.std() < 30:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(enhanced)
        
        # Denoise if needed
        noise_level = self._estimate_noise_level(enhanced)
        if noise_level > 10:
            enhanced = cv2.fastNlMeansDenoising(enhanced, h=noise_level)
        
        # Sharpen if blurry
        if self._is_blurry(enhanced):
            enhanced = self._sharpen_image(enhanced)
        
        return enhanced
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast"""
        # Apply adaptive histogram equalization
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        return clahe.apply(image)
    
    def _denoise_image(self, image: np.ndarray) -> np.ndarray:
        """Remove noise from image"""
        return cv2.fastNlMeansDenoising(image, h=10)
    
    def _sharpen_image(self, image: np.ndarray) -> np.ndarray:
        """Sharpen image"""
        kernel = np.array([[-1, -1, -1],
                          [-1, 9, -1],
                          [-1, -1, -1]])
        return cv2.filter2D(image, -1, kernel)
    
    def _estimate_noise_level(self, image: np.ndarray) -> float:
        """Estimate noise level in image"""
        # Use Laplacian to estimate noise
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        return np.median(np.abs(laplacian))
    
    def _is_blurry(self, image: np.ndarray, threshold: float = 100.0) -> bool:
        """Check if image is blurry"""
        laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
        return laplacian_var < threshold
    
    def measure_roi(self, image_array: np.ndarray, roi_coords: List[Tuple[int, int]], 
                   pixel_spacing: Tuple[float, float] = (1.0, 1.0)) -> Dict:
        """
        Measure region of interest properties
        """
        try:
            # Extract ROI
            roi_mask = self._create_roi_mask(image_array.shape, roi_coords)
            roi_pixels = image_array[roi_mask > 0]
            
            # Calculate measurements
            measurements = {
                'area': float(np.sum(roi_mask) * pixel_spacing[0] * pixel_spacing[1]),
                'mean_intensity': float(np.mean(roi_pixels)),
                'std_intensity': float(np.std(roi_pixels)),
                'min_intensity': float(np.min(roi_pixels)),
                'max_intensity': float(np.max(roi_pixels)),
                'perimeter': float(self._calculate_perimeter(roi_mask) * pixel_spacing[0])
            }
            
            return measurements
        except Exception as e:
            logger.error(f"Error measuring ROI: {e}")
            return {'error': str(e)}
    
    def _create_roi_mask(self, shape: Tuple[int, int], coords: List[Tuple[int, int]]) -> np.ndarray:
        """Create mask from ROI coordinates"""
        mask = np.zeros(shape, dtype=np.uint8)
        coords_array = np.array(coords, dtype=np.int32)
        cv2.fillPoly(mask, [coords_array], 255)
        return mask
    
    def _calculate_perimeter(self, mask: np.ndarray) -> float:
        """Calculate perimeter of masked region"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            return cv2.arcLength(contours[0], True)
        return 0.0


class DicomAIPredictor:
    """Deep learning based predictions for DICOM images"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """Load pre-trained model"""
        try:
            # This is a placeholder - in production, load actual trained model
            self.model = self._create_dummy_model()
            self.model.to(self.device)
            self.model.eval()
        except Exception as e:
            logger.error(f"Error loading model: {e}")
    
    def _create_dummy_model(self) -> nn.Module:
        """Create a dummy model for demonstration"""
        class SimpleClassifier(nn.Module):
            def __init__(self):
                super().__init__()
                self.conv1 = nn.Conv2d(1, 16, 3, padding=1)
                self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
                self.pool = nn.MaxPool2d(2, 2)
                self.fc1 = nn.Linear(32 * 64 * 64, 128)
                self.fc2 = nn.Linear(128, 2)
                
            def forward(self, x):
                x = self.pool(torch.relu(self.conv1(x)))
                x = self.pool(torch.relu(self.conv2(x)))
                x = x.view(-1, 32 * 64 * 64)
                x = torch.relu(self.fc1(x))
                x = self.fc2(x)
                return x
        
        return SimpleClassifier()
    
    def predict(self, image_array: np.ndarray) -> Dict:
        """Make prediction on image"""
        if self.model is None:
            return {'error': 'No model loaded'}
        
        try:
            # Preprocess image
            processed = self._preprocess_for_model(image_array)
            
            # Convert to tensor
            tensor = torch.from_numpy(processed).float().unsqueeze(0).unsqueeze(0)
            tensor = tensor.to(self.device)
            
            # Make prediction
            with torch.no_grad():
                output = self.model(tensor)
                probabilities = torch.softmax(output, dim=1)
                prediction = torch.argmax(probabilities, dim=1)
            
            return {
                'prediction': int(prediction.item()),
                'confidence': float(probabilities.max().item()),
                'probabilities': probabilities.cpu().numpy().tolist()[0]
            }
        except Exception as e:
            logger.error(f"Error in prediction: {e}")
            return {'error': str(e)}
    
    def _preprocess_for_model(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for model input"""
        # Resize to expected input size
        resized = cv2.resize(image, (256, 256))
        
        # Normalize
        normalized = (resized - resized.mean()) / resized.std()
        
        return normalized