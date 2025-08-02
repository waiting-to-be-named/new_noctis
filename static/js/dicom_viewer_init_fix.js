// DICOM Viewer Initialization Fix
// This script ensures proper initialization of the AdvancedDicomViewer class

(function() {
    'use strict';
    
    console.log('DICOM Viewer Init Fix: Starting...');
    
    let initAttempts = 0;
    const maxAttempts = 20;
    
    function waitForDependencies() {
        return new Promise((resolve) => {
            const checkDependencies = () => {
                if (typeof AdvancedDicomViewer !== 'undefined') {
                    console.log('DICOM Viewer Init Fix: AdvancedDicomViewer class found!');
                    resolve();
                } else {
                    initAttempts++;
                    if (initAttempts < maxAttempts) {
                        console.log(`DICOM Viewer Init Fix: Waiting for dependencies... (${initAttempts}/${maxAttempts})`);
                        setTimeout(checkDependencies, 500);
                    } else {
                        console.error('DICOM Viewer Init Fix: AdvancedDicomViewer class not found after maximum attempts');
                        resolve(); // Resolve anyway to try fallback
                    }
                }
            };
            checkDependencies();
        });
    }
    
    async function initializeViewer() {
        await waitForDependencies();
        
        // Get study ID from URL
        const urlParams = new URLSearchParams(window.location.search);
        const studyId = urlParams.get('study_id') || window.studyId || '';
        
        if (!studyId) {
            console.error('DICOM Viewer Init Fix: No study ID found');
            return;
        }
        
        console.log('DICOM Viewer Init Fix: Initializing viewer with study ID:', studyId);
        
        try {
            // Check if viewer already exists
            if (window.advancedViewer) {
                console.log('DICOM Viewer Init Fix: Viewer already exists, reinitializing...');
                // Destroy existing viewer if it has a destroy method
                if (typeof window.advancedViewer.destroy === 'function') {
                    window.advancedViewer.destroy();
                }
            }
            
            // Create new viewer instance
            if (typeof AdvancedDicomViewer !== 'undefined') {
                window.advancedViewer = new AdvancedDicomViewer(studyId);
                console.log('DICOM Viewer Init Fix: Viewer created successfully');
                
                // Wait a bit for viewer to initialize
                setTimeout(() => {
                    // Check if viewer has images
                    if (window.advancedViewer && (!window.advancedViewer.images || window.advancedViewer.images.length === 0)) {
                        console.log('DICOM Viewer Init Fix: No images loaded, attempting to load study...');
                        loadStudyDirectly(studyId);
                    }
                }, 1000);
            } else {
                console.error('DICOM Viewer Init Fix: AdvancedDicomViewer class still not available, using fallback');
                createFallbackViewer(studyId);
            }
        } catch (error) {
            console.error('DICOM Viewer Init Fix: Error initializing viewer:', error);
            createFallbackViewer(studyId);
        }
    }
    
    async function loadStudyDirectly(studyId) {
        try {
            console.log('DICOM Viewer Init Fix: Loading study directly via API...');
            
            // Get CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                             document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || '';
            
            // Fetch study data
            const response = await fetch(`/dicom-viewer/api/studies/${studyId}/`, {
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to load study: ${response.status}`);
            }
            
            const studyData = await response.json();
            console.log('DICOM Viewer Init Fix: Study data loaded:', studyData);
            
            // Load images
            if (studyData.series && studyData.series.length > 0) {
                const firstSeries = studyData.series[0];
                if (firstSeries.images && firstSeries.images.length > 0) {
                    console.log(`DICOM Viewer Init Fix: Loading ${firstSeries.images.length} images from first series`);
                    
                    // If viewer exists, use its loadImages method
                    if (window.advancedViewer && typeof window.advancedViewer.loadImages === 'function') {
                        await window.advancedViewer.loadImages(firstSeries.images);
                    } else {
                        // Direct canvas rendering as fallback
                        displayImageDirectly(firstSeries.images[0]);
                    }
                }
            }
        } catch (error) {
            console.error('DICOM Viewer Init Fix: Error loading study:', error);
        }
    }
    
    function displayImageDirectly(imageUrl) {
        console.log('DICOM Viewer Init Fix: Displaying image directly:', imageUrl);
        
        const canvas = document.getElementById('dicom-canvas-advanced');
        if (!canvas) {
            console.error('DICOM Viewer Init Fix: Canvas not found');
            return;
        }
        
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        img.onload = function() {
            console.log('DICOM Viewer Init Fix: Image loaded, dimensions:', img.width, 'x', img.height);
            
            // Set canvas size to match image
            canvas.width = img.width;
            canvas.height = img.height;
            
            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Draw image
            ctx.drawImage(img, 0, 0);
            
            console.log('DICOM Viewer Init Fix: Image displayed successfully');
            
            // Update debug info
            updateDebugInfo('Image displayed', 1);
        };
        
        img.onerror = function(error) {
            console.error('DICOM Viewer Init Fix: Error loading image:', error);
        };
        
        // Handle relative URLs
        if (!imageUrl.startsWith('http')) {
            imageUrl = window.location.origin + imageUrl;
        }
        
        img.src = imageUrl;
    }
    
    function createFallbackViewer(studyId) {
        console.log('DICOM Viewer Init Fix: Creating fallback viewer...');
        
        // Create a minimal viewer object
        window.advancedViewer = {
            studyId: studyId,
            images: [],
            currentImageIndex: 0,
            canvas: document.getElementById('dicom-canvas-advanced'),
            isInitialized: true,
            
            loadImages: async function(images) {
                this.images = images;
                if (images.length > 0) {
                    displayImageDirectly(images[0]);
                }
            },
            
            showImage: function(index) {
                if (index >= 0 && index < this.images.length) {
                    this.currentImageIndex = index;
                    displayImageDirectly(this.images[index]);
                }
            },
            
            nextImage: function() {
                this.showImage(this.currentImageIndex + 1);
            },
            
            previousImage: function() {
                this.showImage(this.currentImageIndex - 1);
            }
        };
        
        // Load study
        loadStudyDirectly(studyId);
    }
    
    function updateDebugInfo(status, imageCount) {
        const debugStudy = document.getElementById('debug-study');
        const debugImages = document.getElementById('debug-images');
        const debugCanvas = document.getElementById('debug-canvas');
        
        if (debugStudy) debugStudy.textContent = `Study: ${status}`;
        if (debugImages) debugImages.textContent = `Images: ${imageCount}`;
        if (debugCanvas) {
            const canvas = document.getElementById('dicom-canvas-advanced');
            if (canvas) {
                debugCanvas.textContent = `Canvas: ${canvas.width}x${canvas.height}`;
            }
        }
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeViewer);
    } else {
        // DOM already loaded
        setTimeout(initializeViewer, 100);
    }
    
    // Also try on window load
    window.addEventListener('load', function() {
        setTimeout(() => {
            if (!window.advancedViewer || !window.advancedViewer.isInitialized) {
                console.log('DICOM Viewer Init Fix: Retrying initialization on window load...');
                initializeViewer();
            }
        }, 500);
    });
    
    // Export for manual triggering
    window.dicomViewerInitFix = {
        initialize: initializeViewer,
        loadStudy: loadStudyDirectly,
        displayImage: displayImageDirectly
    };
    
})();