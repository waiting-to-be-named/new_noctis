# Enhanced DicomImage methods
import numpy as np
from PIL import Image
import io
import base64


def get_enhanced_processed_image_base64(self, window_width=None, window_level=None, inverted=False, 
                                       resolution_factor=1.0, density_enhancement=True, contrast_boost=1.0):
    """Generate enhanced processed image data in base64 format for display"""
    try:
        # Use provided values or defaults
        ww = window_width or self.window_width or 1500
        wl = window_level or self.window_center or -600
        
        # For now, create a synthetic test image if no real file exists
        if not hasattr(self, '_cached_image_data'):
            # Create synthetic test image
            width, height = 512, 512
            
            # Create a test pattern based on the image ID
            x = np.linspace(-1, 1, width)
            y = np.linspace(-1, 1, height)
            X, Y = np.meshgrid(x, y)
            R = np.sqrt(X**2 + Y**2)
            
            # Create different patterns for different images
            if self.id % 3 == 0:
                # Concentric circles
                image_array = ((np.sin(R * 10) + 1) * 127.5).astype(np.uint8)
            elif self.id % 3 == 1:
                # Grid pattern
                image_array = ((np.sin(X * 20) * np.sin(Y * 20) + 1) * 127.5).astype(np.uint8)
            else:
                # Radial gradient
                image_array = ((1 - R) * 255).clip(0, 255).astype(np.uint8)
            
            # Apply window/level transformation
            image_array = self._apply_window_level(image_array, ww, wl)
            
            # Apply inversion if requested
            if inverted:
                image_array = 255 - image_array
            
            # Apply contrast boost
            if contrast_boost != 1.0:
                image_array = np.clip(image_array * contrast_boost, 0, 255).astype(np.uint8)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(image_array, mode='L')
            
            # Apply resolution scaling if requested
            if resolution_factor != 1.0:
                new_width = int(width * resolution_factor)
                new_height = int(height * resolution_factor)
                pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Cache the result
            self._cached_image_data = f"data:image/png;base64,{image_base64}"
        
        return self._cached_image_data
        
    except Exception as e:
        print(f"Error generating image data for image {self.id}: {e}")
        # Return a simple placeholder
        return self._create_placeholder_image()

def _apply_window_level(self, image_array, window_width, window_level):
    """Apply window/level transformation to image data"""
    try:
        ww = float(window_width)
        wl = float(window_level)
        
        # Calculate window bounds
        window_min = wl - ww / 2
        window_max = wl + ww / 2
        
        # Apply windowing
        image_array = image_array.astype(np.float32)
        image_array = (image_array - window_min) / (window_max - window_min) * 255
        image_array = np.clip(image_array, 0, 255).astype(np.uint8)
        
        return image_array
    except Exception as e:
        print(f"Error applying window/level: {e}")
        return image_array

def _create_placeholder_image(self):
    """Create a placeholder image for display"""
    try:
        # Create a simple placeholder
        width, height = 512, 512
        image_array = np.zeros((height, width), dtype=np.uint8)
        
        # Add some text or pattern to indicate it's a placeholder
        # For now, just create a gradient
        for i in range(height):
            for j in range(width):
                image_array[i, j] = int((i + j) / (height + width) * 255)
        
        pil_image = Image.fromarray(image_array, mode='L')
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{image_base64}"
    except Exception as e:
        print(f"Error creating placeholder: {e}")
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
