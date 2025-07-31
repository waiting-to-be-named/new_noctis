#!/usr/bin/env python3
"""
Advanced DICOM Tissue Differentiation Enhancement
==============================================

This script provides comprehensive DICOM image enhancement specifically
designed to improve tissue differentiation quality similar to high-end
medical imaging workstations.
"""

import os
import sys
import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter
import pydicom
from scipy import ndimage, signal
from skimage import exposure, filters, restoration, morphology, segmentation
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter, median_filter, uniform_filter

class AdvancedDICOMEnhancer:
    """Advanced DICOM enhancement for superior tissue differentiation"""
    
    def __init__(self):
        # Preset configurations for different anatomy types
        self.tissue_presets = {
            'bone_window': {
                'window_center': 400,
                'window_width': 1000,
                'contrast_factor': 1.4,
                'gamma': 0.9,
                'edge_enhancement': 0.6
            },
            'soft_tissue': {
                'window_center': 40,
                'window_width': 400,
                'contrast_factor': 1.6,
                'gamma': 0.8,
                'edge_enhancement': 0.4
            },
            'lung_window': {
                'window_center': -600,
                'window_width': 1500,
                'contrast_factor': 1.3,
                'gamma': 0.85,
                'edge_enhancement': 0.5
            },
            'brain_window': {
                'window_center': 40,
                'window_width': 80,
                'contrast_factor': 1.8,
                'gamma': 0.75,
                'edge_enhancement': 0.3
            },
            'abdomen_window': {
                'window_center': 60,
                'window_width': 400,
                'contrast_factor': 1.5,
                'gamma': 0.8,
                'edge_enhancement': 0.4
            }
        }
    
    def load_dicom_image(self, dicom_path):
        """Load DICOM image with proper preprocessing"""
        try:
            ds = pydicom.dcmread(dicom_path)
            pixel_array = ds.pixel_array.astype(float)
            
            # Apply rescale slope and intercept if available
            if hasattr(ds, 'RescaleSlope') and hasattr(ds, 'RescaleIntercept'):
                pixel_array = pixel_array * ds.RescaleSlope + ds.RescaleIntercept
            
            return pixel_array, ds
        except Exception as e:
            print(f"Error loading DICOM: {e}")
            return None, None
    
    def apply_advanced_windowing(self, image, window_center, window_width, smooth_transition=True):
        """Apply windowing with smooth transitions for better tissue visualization"""
        window_min = window_center - window_width / 2
        window_max = window_center + window_width / 2
        
        if smooth_transition:
            # Smooth windowing with sigmoid-like transitions
            transition_width = window_width * 0.1
            
            # Lower transition
            lower_mask = image < (window_min + transition_width)
            lower_values = 1 / (1 + np.exp(-10 * (image - window_min) / transition_width))
            
            # Upper transition
            upper_mask = image > (window_max - transition_width)
            upper_values = 1 / (1 + np.exp(10 * (image - window_max) / transition_width))
            
            # Linear region
            linear_mask = ~(lower_mask | upper_mask)
            linear_values = (image - window_min) / (window_max - window_min)
            
            windowed = np.zeros_like(image)
            windowed[lower_mask] = lower_values[lower_mask]
            windowed[upper_mask] = upper_values[upper_mask]
            windowed[linear_mask] = linear_values[linear_mask]
        else:
            # Standard windowing
            windowed = np.clip((image - window_min) / (window_max - window_min), 0, 1)
        
        return windowed
    
    def enhance_tissue_contrast_clahe(self, image, clip_limit=0.02, tile_grid_size=(8, 8)):
        """Apply Contrast Limited Adaptive Histogram Equalization"""
        # Convert to uint8 for CLAHE
        image_uint8 = (image * 255).astype(np.uint8)
        
        # Apply CLAHE
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        enhanced = clahe.apply(image_uint8)
        
        return enhanced.astype(float) / 255.0
    
    def apply_multi_scale_enhancement(self, image):
        """Multi-scale enhancement for better tissue differentiation"""
        # Different scales for analysis
        scales = [0.5, 1.0, 2.0, 4.0]
        enhanced_scales = []
        
        for scale in scales:
            # Gaussian blur at different scales
            blurred = gaussian_filter(image, sigma=scale)
            # Enhance details at this scale
            detail = image - blurred
            enhanced_detail = detail * (2.0 - scale * 0.2)  # Adaptive enhancement
            enhanced_scales.append(blurred + enhanced_detail)
        
        # Combine scales with weighted average
        weights = [0.1, 0.4, 0.3, 0.2]
        enhanced = np.sum([w * scale for w, scale in zip(weights, enhanced_scales)], axis=0)
        
        return np.clip(enhanced, 0, 1)
    
    def enhance_edges_selectively(self, image, strength=0.5):
        """Selective edge enhancement that preserves tissue boundaries"""
        # Sobel edge detection
        sobel_h = ndimage.sobel(image, axis=0)
        sobel_v = ndimage.sobel(image, axis=1)
        edges = np.sqrt(sobel_h**2 + sobel_v**2)
        
        # Laplacian for fine detail enhancement
        laplacian = ndimage.laplace(image)
        
        # Adaptive enhancement based on local image properties
        local_std = ndimage.uniform_filter(image**2, size=5) - ndimage.uniform_filter(image, size=5)**2
        adaptation_factor = np.clip(local_std * 5, 0.2, 1.0)
        
        # Combine edge enhancements
        enhanced = image + strength * adaptation_factor * (0.7 * edges + 0.3 * laplacian)
        
        return np.clip(enhanced, 0, 1)
    
    def reduce_noise_preserve_details(self, image):
        """Advanced noise reduction while preserving anatomical details"""
        # Non-local means denoising
        denoised_nlm = restoration.denoise_nl_means(
            image, 
            patch_size=5, 
            patch_distance=6, 
            h=0.08,
            fast_mode=True
        )
        
        # Bilateral filtering for edge preservation
        image_uint8 = (image * 255).astype(np.uint8)
        bilateral = cv2.bilateralFilter(image_uint8, 9, 75, 75)
        denoised_bilateral = bilateral.astype(float) / 255.0
        
        # Combine denoising methods
        combined = 0.6 * denoised_nlm + 0.4 * denoised_bilateral
        
        return np.clip(combined, 0, 1)
    
    def apply_tissue_specific_enhancement(self, image, tissue_type='soft_tissue'):
        """Apply tissue-specific enhancement parameters"""
        preset = self.tissue_presets.get(tissue_type, self.tissue_presets['soft_tissue'])
        
        # Convert to HU-like values for windowing
        hu_image = (image - 0.5) * 4000  # Approximate HU conversion
        
        # Apply windowing
        windowed = self.apply_advanced_windowing(
            hu_image, 
            preset['window_center'], 
            preset['window_width']
        )
        
        # Apply gamma correction
        gamma_corrected = np.power(windowed, preset['gamma'])
        
        # Apply contrast enhancement
        contrast_enhanced = np.clip(
            (gamma_corrected - 0.5) * preset['contrast_factor'] + 0.5, 
            0, 1
        )
        
        return contrast_enhanced
    
    def create_tissue_differentiation_map(self, image):
        """Create enhanced tissue differentiation using advanced algorithms"""
        # Multi-resolution analysis
        pyramid_levels = 4
        pyramid = [image]
        
        # Build Gaussian pyramid
        for level in range(pyramid_levels - 1):
            reduced = ndimage.zoom(pyramid[-1], 0.5, order=1)
            pyramid.append(reduced)
        
        # Build Laplacian pyramid
        laplacian_pyramid = []
        for level in range(pyramid_levels - 1):
            expanded = ndimage.zoom(pyramid[level + 1], 2, order=1)
            # Ensure same size
            if expanded.shape != pyramid[level].shape:
                expanded = ndimage.zoom(expanded, 
                    (pyramid[level].shape[0] / expanded.shape[0],
                     pyramid[level].shape[1] / expanded.shape[1]), 
                    order=1)
            laplacian = pyramid[level] - expanded
            laplacian_pyramid.append(laplacian)
        
        # Enhance each level
        enhanced_pyramid = []
        enhancement_factors = [2.0, 1.5, 1.2, 1.0]
        
        for i, laplacian in enumerate(laplacian_pyramid):
            enhanced = laplacian * enhancement_factors[i]
            enhanced_pyramid.append(enhanced)
        
        # Reconstruct enhanced image
        enhanced = pyramid[-1]
        for level in range(pyramid_levels - 2, -1, -1):
            expanded = ndimage.zoom(enhanced, 2, order=1)
            if expanded.shape != enhanced_pyramid[level].shape:
                expanded = ndimage.zoom(expanded,
                    (enhanced_pyramid[level].shape[0] / expanded.shape[0],
                     enhanced_pyramid[level].shape[1] / expanded.shape[1]),
                    order=1)
            enhanced = expanded + enhanced_pyramid[level]
        
        return np.clip(enhanced, 0, 1)
    
    def enhance_dicom_image(self, dicom_path, tissue_type='soft_tissue', output_path=None):
        """Main enhancement function with comprehensive improvements"""
        print(f"Loading DICOM image: {dicom_path}")
        
        # Load DICOM
        pixel_array, dicom_ds = self.load_dicom_image(dicom_path)
        if pixel_array is None:
            return None
        
        print(f"Original image shape: {pixel_array.shape}")
        print(f"Original value range: {pixel_array.min():.2f} to {pixel_array.max():.2f}")
        
        # Normalize to 0-1 range
        normalized = (pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min())
        
        # Step 1: Noise reduction while preserving details
        print("Step 1: Advanced noise reduction...")
        denoised = self.reduce_noise_preserve_details(normalized)
        
        # Step 2: Apply tissue-specific enhancements
        print(f"Step 2: Applying {tissue_type} specific enhancements...")
        tissue_enhanced = self.apply_tissue_specific_enhancement(denoised, tissue_type)
        
        # Step 3: Multi-scale enhancement
        print("Step 3: Multi-scale enhancement...")
        multi_scale_enhanced = self.apply_multi_scale_enhancement(tissue_enhanced)
        
        # Step 4: CLAHE for local contrast
        print("Step 4: Adaptive histogram equalization...")
        clahe_enhanced = self.enhance_tissue_contrast_clahe(multi_scale_enhanced)
        
        # Step 5: Tissue differentiation mapping
        print("Step 5: Creating tissue differentiation map...")
        diff_enhanced = self.create_tissue_differentiation_map(clahe_enhanced)
        
        # Step 6: Selective edge enhancement
        print("Step 6: Selective edge enhancement...")
        edge_enhanced = self.enhance_edges_selectively(diff_enhanced, 
                                                     self.tissue_presets[tissue_type]['edge_enhancement'])
        
        # Final combination and refinement
        print("Step 7: Final enhancement combination...")
        final_enhanced = (
            0.1 * normalized +         # Preserve some original information
            0.2 * denoised +          # Clean base
            0.3 * multi_scale_enhanced + # Multi-scale details
            0.4 * edge_enhanced       # Final enhanced version
        )
        
        final_enhanced = np.clip(final_enhanced, 0, 1)
        
        # Convert to 8-bit for output
        enhanced_8bit = (final_enhanced * 255).astype(np.uint8)
        
        # Save enhanced image
        if output_path is None:
            output_path = dicom_path.replace('.dcm', f'_enhanced_{tissue_type}.png')
        
        Image.fromarray(enhanced_8bit).save(output_path)
        print(f"Enhanced image saved to: {output_path}")
        
        # Create comparison visualization
        self.create_comparison_plot(normalized, final_enhanced, 
                                  output_path.replace('.png', '_comparison.png'))
        
        return final_enhanced, output_path
    
    def create_comparison_plot(self, original, enhanced, output_path):
        """Create detailed comparison visualization"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # Original image
        axes[0, 0].imshow(original, cmap='gray', aspect='equal')
        axes[0, 0].set_title('Original Image', fontsize=14)
        axes[0, 0].axis('off')
        
        # Enhanced image
        axes[0, 1].imshow(enhanced, cmap='gray', aspect='equal')
        axes[0, 1].set_title('Enhanced Image', fontsize=14)
        axes[0, 1].axis('off')
        
        # Difference map
        difference = np.abs(enhanced - original)
        im_diff = axes[0, 2].imshow(difference, cmap='hot', aspect='equal')
        axes[0, 2].set_title('Enhancement Difference', fontsize=14)
        axes[0, 2].axis('off')
        plt.colorbar(im_diff, ax=axes[0, 2], fraction=0.046, pad=0.04)
        
        # Histograms
        axes[1, 0].hist(original.flatten(), bins=100, alpha=0.7, label='Original', color='blue')
        axes[1, 0].hist(enhanced.flatten(), bins=100, alpha=0.7, label='Enhanced', color='red')
        axes[1, 0].set_title('Intensity Histograms', fontsize=14)
        axes[1, 0].set_xlabel('Intensity')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # Edge detection comparison
        edges_orig = filters.sobel(original)
        edges_enh = filters.sobel(enhanced)
        
        axes[1, 1].imshow(edges_orig, cmap='gray', aspect='equal')
        axes[1, 1].set_title('Original Edges', fontsize=14)
        axes[1, 1].axis('off')
        
        axes[1, 2].imshow(edges_enh, cmap='gray', aspect='equal')
        axes[1, 2].set_title('Enhanced Edges', fontsize=14)
        axes[1, 2].axis('off')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Comparison plot saved to: {output_path}")

def main():
    """Main function to demonstrate DICOM enhancement"""
    enhancer = AdvancedDICOMEnhancer()
    
    print("Advanced DICOM Tissue Differentiation Enhancement")
    print("=" * 50)
    
    # Example usage - you'll need to modify paths for your specific files
    dicom_path = input("Enter DICOM file path (or press Enter for example): ").strip()
    
    if not dicom_path:
        print("Please provide a valid DICOM file path")
        return
    
    if not os.path.exists(dicom_path):
        print(f"File not found: {dicom_path}")
        return
    
    # Choose tissue type
    print("\nAvailable tissue types:")
    for i, tissue_type in enumerate(enhancer.tissue_presets.keys(), 1):
        print(f"{i}. {tissue_type}")
    
    try:
        choice = int(input("Select tissue type (1-5): ")) - 1
        tissue_types = list(enhancer.tissue_presets.keys())
        selected_tissue = tissue_types[choice]
    except (ValueError, IndexError):
        selected_tissue = 'soft_tissue'
        print("Invalid selection, using 'soft_tissue' as default")
    
    # Enhance the image
    result = enhancer.enhance_dicom_image(dicom_path, selected_tissue)
    
    if result is not None:
        enhanced_image, output_path = result
        print(f"\nEnhancement complete!")
        print(f"Enhanced image quality with improved tissue differentiation")
        print(f"Output saved to: {output_path}")
        print("Check the comparison visualization to see the improvements")
    else:
        print("Enhancement failed!")

if __name__ == "__main__":
    main()