// Viewer Study Loader Fix
// Ensures proper study loading when redirecting from worklist

(function() {
    'use strict';
    
    console.log('Viewer Study Loader Fix: Initializing...');
    
    // Override or enhance the loadStudy method
    function enhanceStudyLoading() {
        if (!window.advancedViewer) {
            console.log('Viewer not initialized yet, waiting...');
            setTimeout(enhanceStudyLoading, 100);
            return;
        }
        
        const originalLoadStudy = window.advancedViewer.loadStudy;
        
        window.advancedViewer.loadStudy = async function(studyId) {
            console.log(`Enhanced loadStudy called with ID: ${studyId}`);
            
            try {
                // Show loading state
                this.showLoading(true);
                this.updateStatus('Loading study from worklist...');
                
                // Clear any existing data
                this.currentStudy = null;
                this.currentSeries = null;
                this.currentImages = [];
                this.currentImage = null;
                this.currentImageIndex = 0;
                
                // Clear canvas
                if (this.ctx) {
                    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                    this.ctx.fillStyle = '#000';
                    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                }
                
                // Call original method
                await originalLoadStudy.call(this, studyId);
                
                console.log('Study loaded successfully');
                
                // Ensure UI is updated
                if (this.currentStudy) {
                    this.updatePatientInfo();
                    this.updateImageInfo();
                }
                
                // Log debug info
                const debugInfo = {
                    studyId: studyId,
                    studyLoaded: !!this.currentStudy,
                    seriesCount: this.currentSeries?.length || 0,
                    imageCount: this.currentImages?.length || 0,
                    currentImageIndex: this.currentImageIndex,
                    hasCanvas: !!this.canvas,
                    canvasSize: this.canvas ? `${this.canvas.width}x${this.canvas.height}` : 'N/A'
                };
                console.log('Study loading debug info:', debugInfo);
                
            } catch (error) {
                console.error('Error in enhanced loadStudy:', error);
                this.notyf.error(`Failed to load study: ${error.message}`);
                this.updateStatus('Error loading study');
                throw error;
            }
        };
        
        console.log('Study loading enhancement applied');
    }
    
    // Enhanced image loading with better error handling
    function enhanceImageLoading() {
        if (!window.advancedViewer) {
            setTimeout(enhanceImageLoading, 100);
            return;
        }
        
        const originalLoadImage = window.advancedViewer.loadImage;
        
        window.advancedViewer.loadImage = async function(index) {
            console.log(`Enhanced loadImage called with index: ${index}`);
            
            try {
                // Validate index
                if (!this.currentImages || this.currentImages.length === 0) {
                    throw new Error('No images available to load');
                }
                
                if (index < 0 || index >= this.currentImages.length) {
                    console.warn(`Invalid image index: ${index}, available: ${this.currentImages.length}`);
                    return;
                }
                
                // Call original method
                await originalLoadImage.call(this, index);
                
                // Ensure canvas is visible
                if (this.canvas) {
                    this.canvas.style.display = 'block';
                    this.canvas.style.opacity = '1';
                }
                
                // Hide loading indicator
                const loadingIndicator = document.getElementById('loading-indicator');
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                
            } catch (error) {
                console.error('Error in enhanced loadImage:', error);
                
                // Show error on canvas
                if (this.ctx) {
                    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                    this.ctx.fillStyle = '#1a1a1a';
                    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                    
                    this.ctx.fillStyle = '#ff3333';
                    this.ctx.font = '20px Arial';
                    this.ctx.textAlign = 'center';
                    this.ctx.fillText('Failed to load image', this.canvas.width / 2, this.canvas.height / 2 - 20);
                    
                    this.ctx.fillStyle = '#fff';
                    this.ctx.font = '16px Arial';
                    this.ctx.fillText(error.message, this.canvas.width / 2, this.canvas.height / 2 + 10);
                }
                
                throw error;
            }
        };
        
        console.log('Image loading enhancement applied');
    }
    
    // Function to handle study loading from URL
    function loadStudyFromURL() {
        const urlPath = window.location.pathname;
        const studyMatch = urlPath.match(/\/viewer\/study\/(\d+)\//);
        
        if (studyMatch && window.advancedViewer) {
            const studyId = parseInt(studyMatch[1]);
            console.log('Found study ID in URL:', studyId);
            
            // Check if study is already loaded
            if (window.advancedViewer.currentStudy?.id !== studyId) {
                console.log('Loading study from URL...');
                window.advancedViewer.loadStudy(studyId).catch(error => {
                    console.error('Failed to load study from URL:', error);
                });
            } else {
                console.log('Study already loaded');
            }
        }
    }
    
    // Apply enhancements when ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            enhanceStudyLoading();
            enhanceImageLoading();
            
            // Wait a bit for viewer initialization, then load study from URL
            setTimeout(loadStudyFromURL, 1000);
        });
    } else {
        enhanceStudyLoading();
        enhanceImageLoading();
        setTimeout(loadStudyFromURL, 1000);
    }
    
    // Also apply on window load as backup
    window.addEventListener('load', () => {
        if (!window.studyLoaderEnhanced) {
            enhanceStudyLoading();
            enhanceImageLoading();
            loadStudyFromURL();
            window.studyLoaderEnhanced = true;
        }
    });
    
    console.log('Viewer Study Loader Fix: Ready');
})();