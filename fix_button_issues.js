// Fix for button functionality issues
document.addEventListener('DOMContentLoaded', function() {
    console.log('Applying button fixes...');
    
    // Fix Load DICOM button
    const loadDicomBtn = document.getElementById('load-dicom-btn');
    if (loadDicomBtn) {
        // Remove existing listeners
        const newLoadBtn = loadDicomBtn.cloneNode(true);
        loadDicomBtn.parentNode.replaceChild(newLoadBtn, loadDicomBtn);
        
        newLoadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Load DICOM button clicked');
            
            // Show upload modal
            const modal = document.getElementById('upload-modal');
            if (modal) {
                modal.style.display = 'block';
            } else {
                console.error('Upload modal not found');
            }
        });
    }
    
    // Fix Worklist button
    const worklistBtn = document.getElementById('worklist-btn');
    if (worklistBtn) {
        // Remove existing listeners
        const newWorklistBtn = worklistBtn.cloneNode(true);
        worklistBtn.parentNode.replaceChild(newWorklistBtn, worklistBtn);
        
        newWorklistBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Worklist button clicked');
            window.location.href = '/worklist/';
        });
    }
    
    // Fix Clear Measurements button
    const clearMeasurementsBtn = document.getElementById('clear-measurements');
    if (clearMeasurementsBtn) {
        // Remove existing listeners
        const newClearBtn = clearMeasurementsBtn.cloneNode(true);
        clearMeasurementsBtn.parentNode.replaceChild(newClearBtn, clearMeasurementsBtn);
        
        newClearBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Clear measurements button clicked');
            if (window.viewer && typeof window.viewer.clearMeasurements === 'function') {
                window.viewer.clearMeasurements();
            }
        });
    }
    
    console.log('Button fixes applied');
});

// Fix for image loading issues
function fixImageLoading() {
    if (window.viewer && window.viewer.loadCurrentImage) {
        const originalLoadCurrentImage = window.viewer.loadCurrentImage;
        
        window.viewer.loadCurrentImage = async function() {
            try {
                console.log('Loading current image with enhanced error handling...');
                await originalLoadCurrentImage.call(this);
                
                // Force a redraw after loading
                setTimeout(() => {
                    if (this.updateDisplay) {
                        this.updateDisplay();
                    }
                    if (this.updatePatientInfo) {
                        this.updatePatientInfo();
                    }
                }, 100);
                
            } catch (error) {
                console.error('Error loading image:', error);
                this.showError('Failed to load image: ' + error.message);
            }
        };
        
        console.log('Image loading fix applied');
    }
}

// Apply fixes when viewer is ready
function applyViewerFixes() {
    if (window.viewer) {
        fixImageLoading();
    } else {
        // Wait for viewer to be available
        setTimeout(applyViewerFixes, 100);
    }
}

// Apply fixes when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(applyViewerFixes, 500);
});