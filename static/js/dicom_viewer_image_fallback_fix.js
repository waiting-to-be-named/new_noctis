// DICOM Viewer Image Fallback Fix
// Handles missing or corrupted DICOM files gracefully

(function() {
    console.log('DICOM Image Fallback Fix: Loading...');
    
    // Store original loadImage method
    let originalLoadImage = null;
    
    // Generate a synthetic test image
    function generateSyntheticImage(imageInfo) {
        const canvas = document.createElement('canvas');
        canvas.width = 512;
        canvas.height = 512;
        const ctx = canvas.getContext('2d');
        
        // Create a gradient background
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        gradient.addColorStop(0, '#333333');
        gradient.addColorStop(0.5, '#555555');
        gradient.addColorStop(1, '#333333');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Add grid pattern
        ctx.strokeStyle = '#444444';
        ctx.lineWidth = 1;
        for (let i = 0; i < canvas.width; i += 50) {
            ctx.beginPath();
            ctx.moveTo(i, 0);
            ctx.lineTo(i, canvas.height);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(0, i);
            ctx.lineTo(canvas.width, i);
            ctx.stroke();
        }
        
        // Add center crosshair
        ctx.strokeStyle = '#666666';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(canvas.width / 2, 0);
        ctx.lineTo(canvas.width / 2, canvas.height);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, canvas.height / 2);
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();
        
        // Add text overlay
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 24px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Test Image', canvas.width / 2, canvas.height / 2 - 40);
        
        ctx.font = '16px Arial';
        ctx.fillText(`Image ${imageInfo.id || 'N/A'}`, canvas.width / 2, canvas.height / 2);
        ctx.fillText(`Instance: ${imageInfo.instance_number || 'N/A'}`, canvas.width / 2, canvas.height / 2 + 30);
        
        // Add warning text
        ctx.font = '14px Arial';
        ctx.fillStyle = '#FFAA00';
        ctx.fillText('(DICOM file unavailable)', canvas.width / 2, canvas.height / 2 + 60);
        
        return canvas.toDataURL('image/png');
    }
    
    // Enhanced loadImage with fallback
    function enhancedLoadImage(index) {
        const viewer = this;
        const originalMethod = originalLoadImage.bind(viewer);
        
        console.log(`Fallback-enhanced loadImage called for index: ${index}`);
        
        // Call original method with error handling
        return originalMethod(index).catch(async (error) => {
            console.error('Original loadImage failed:', error);
            
            // Check if we have image info
            if (!viewer.currentImages || !viewer.currentImages[index]) {
                console.error('No image info available for fallback');
                throw error;
            }
            
            const imageInfo = viewer.currentImages[index];
            console.log('Attempting fallback for image:', imageInfo);
            
            // Try alternate API endpoint
            try {
                const response = await fetch(`/viewer/api/images/${imageInfo.id}/fallback/`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.image_data) {
                        console.log('Got fallback image from server');
                        
                        // Create and load fallback image
                        const img = new Image();
                        img.src = data.image_data;
                        
                        await new Promise((resolve, reject) => {
                            img.onload = () => {
                                viewer.currentImage = img;
                                viewer.currentImageMetadata = data.metadata || {};
                                viewer.currentImageIndex = index;
                                resolve();
                            };
                            img.onerror = reject;
                        });
                        
                        // Render the fallback image
                        if (viewer.render) {
                            viewer.render();
                        }
                        if (viewer.updateImageInfo) {
                            viewer.updateImageInfo();
                        }
                        if (viewer.updateStatus) {
                            viewer.updateStatus('Image loaded (fallback)');
                        }
                        
                        return;
                    }
                }
            } catch (e) {
                console.error('Fallback API failed:', e);
            }
            
            // Generate synthetic image as last resort
            console.log('Generating synthetic test image');
            const syntheticData = generateSyntheticImage(imageInfo);
            
            const img = new Image();
            img.src = syntheticData;
            
            await new Promise((resolve) => {
                img.onload = () => {
                    viewer.currentImage = img;
                    viewer.currentImageMetadata = {
                        synthetic: true,
                        originalError: error.message
                    };
                    viewer.currentImageIndex = index;
                    resolve();
                };
            });
            
            // Render the synthetic image
            if (viewer.render) {
                viewer.render();
            }
            if (viewer.updateImageInfo) {
                viewer.updateImageInfo();
            }
            if (viewer.updateStatus) {
                viewer.updateStatus('Showing test image (DICOM unavailable)');
            }
            
            // Show notification
            if (viewer.notyf) {
                viewer.notyf.warning('DICOM file unavailable - showing test image');
            }
        });
    }
    
    // Apply fix when viewer is ready
    function applyFallbackFix() {
        if (window.advancedViewer && window.advancedViewer.loadImage) {
            if (!originalLoadImage) {
                originalLoadImage = window.advancedViewer.loadImage;
                window.advancedViewer.loadImage = enhancedLoadImage;
                console.log('Image fallback fix applied successfully');
            }
        }
    }
    
    // Wait for viewer to be ready
    const checkInterval = setInterval(() => {
        if (window.advancedViewer) {
            applyFallbackFix();
            clearInterval(checkInterval);
        }
    }, 100);
    
    // Also apply on various events
    document.addEventListener('DOMContentLoaded', applyFallbackFix);
    window.addEventListener('load', applyFallbackFix);
    
    // Expose for debugging
    window.dicomImageFallbackFix = {
        generateSyntheticImage,
        applyFallbackFix
    };
    
    console.log('DICOM Image Fallback Fix: Ready');
})();