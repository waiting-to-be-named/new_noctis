// DICOM Viewer Image Loading Fix
// Handles image loading errors and provides fallback functionality

(function() {
    'use strict';
    
    console.log('DICOM Viewer Image Fix: Initializing...');
    
    // Store the original loadImage method
    const originalLoadImage = window.advancedViewer?.loadImage;
    
    // Enhanced image loading with better error handling
    if (window.advancedViewer && originalLoadImage) {
        window.advancedViewer.loadImage = async function(imageIndex) {
            try {
                // Call the original method
                const result = await originalLoadImage.call(this, imageIndex);
                return result;
            } catch (error) {
                console.error('Image loading failed:', error);
                
                // Check if it's a 500 error (file missing)
                if (error.message && error.message.includes('500')) {
                    console.log('Server error - attempting fallback...');
                    
                    // Try to display a placeholder or message
                    if (this.canvas && this.ctx) {
                        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                        
                        // Draw error message
                        this.ctx.fillStyle = '#1a1a1a';
                        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                        
                        this.ctx.fillStyle = '#ff6b35';
                        this.ctx.font = '20px Arial';
                        this.ctx.textAlign = 'center';
                        this.ctx.textBaseline = 'middle';
                        this.ctx.fillText('Image file not found', this.canvas.width / 2, this.canvas.height / 2 - 30);
                        
                        this.ctx.fillStyle = '#aaa';
                        this.ctx.font = '16px Arial';
                        this.ctx.fillText('The DICOM file may be missing or corrupted', this.canvas.width / 2, this.canvas.height / 2);
                        this.ctx.fillText(`Image ID: ${this.currentStudy?.images[imageIndex]?.id || 'Unknown'}`, this.canvas.width / 2, this.canvas.height / 2 + 30);
                    }
                    
                    // Update status
                    this.updateStatus('Image file not available');
                    
                    // Show notification
                    if (this.notyf) {
                        this.notyf.open({
                            type: 'error',
                            message: 'Image file not found. Please check if the file exists on the server.'
                        });
                    }
                    
                    // Don't throw the error, just log it
                    return null;
                }
                
                // Re-throw other errors
                throw error;
            }
        };
    }
    
    // Add a method to check file availability
    window.checkImageAvailability = async function(studyId) {
        try {
            const response = await fetch(`/viewer/api/studies/${studyId}/check-files/`);
            if (response.ok) {
                const data = await response.json();
                console.log('File availability check:', data);
                return data;
            }
        } catch (error) {
            console.error('Error checking file availability:', error);
        }
        return null;
    };
    
    // Fix for navigation buttons when images are missing
    const fixNavigation = () => {
        const viewer = window.advancedViewer;
        if (!viewer) return;
        
        const originalNavigateImage = viewer.navigateImage;
        if (originalNavigateImage) {
            viewer.navigateImage = async function(direction) {
                try {
                    await originalNavigateImage.call(this, direction);
                } catch (error) {
                    console.error('Navigation error:', error);
                    // Continue to next/previous image even if current one fails
                    if (direction === 'next' && this.currentImageIndex < this.currentStudy.images.length - 1) {
                        this.currentImageIndex++;
                        await this.loadImage(this.currentImageIndex);
                    } else if (direction === 'prev' && this.currentImageIndex > 0) {
                        this.currentImageIndex--;
                        await this.loadImage(this.currentImageIndex);
                    }
                }
            };
        }
    };
    
    // Apply fixes when viewer is ready
    const applyFixes = () => {
        if (window.advancedViewer) {
            fixNavigation();
            console.log('DICOM Viewer Image Fix: Applied successfully');
        } else {
            console.log('Waiting for viewer to initialize...');
            setTimeout(applyFixes, 100);
        }
    };
    
    // Start applying fixes
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyFixes);
    } else {
        applyFixes();
    }
    
})();