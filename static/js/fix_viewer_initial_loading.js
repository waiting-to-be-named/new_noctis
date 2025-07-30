// Fix for viewer initial loading issue
// This script should be included after the main dicom_viewer.js

// Override the init method to ensure proper initial study loading
if (typeof DicomViewer !== 'undefined') {
    const originalInit = DicomViewer.prototype.init;
    
    DicomViewer.prototype.init = async function() {
        console.log('Initializing DicomViewer with initialStudyId:', this.initialStudyId);
        
        this.setupCanvas();
        this.setupEventListeners();
        await this.loadBackendStudies();
        this.setupNotifications();
        this.setupMeasurementUnitSelector();
        this.setup3DControls();
        this.setupAIPanel();
        
        // Load initial study if provided with improved error handling
        if (this.initialStudyId) {
            console.log('Loading initial study:', this.initialStudyId);
            try {
                // Show loading state
                this.showLoadingState();
                
                await this.loadStudy(this.initialStudyId);
                
                // Force UI updates after loading
                setTimeout(() => {
                    this.redraw();
                    this.updatePatientInfo();
                    this.updateSliders();
                    
                    // Ensure patient info is visible
                    const patientInfo = document.getElementById('patient-info');
                    if (patientInfo && this.currentStudy) {
                        patientInfo.textContent = `Patient: ${this.currentStudy.patient_name} | Study Date: ${this.currentStudy.study_date} | Modality: ${this.currentStudy.modality}`;
                        patientInfo.style.display = 'block';
                    }
                    
                    // Update image controls if available
                    if (this.currentImages && this.currentImages.length > 0) {
                        const sliceSlider = document.getElementById('slice-slider');
                        if (sliceSlider) {
                            sliceSlider.max = this.currentImages.length - 1;
                            sliceSlider.value = 0;
                        }
                        
                        const sliceValue = document.getElementById('slice-value');
                        if (sliceValue) {
                            sliceValue.textContent = '1';
                        }
                    }
                    
                    console.log('Initial study loaded successfully');
                }, 200);
                
            } catch (error) {
                console.error('Failed to load initial study:', error);
                this.showError('Failed to load initial study: ' + error.message);
            }
        }
    };
    
    // Add loading state method
    DicomViewer.prototype.showLoadingState = function() {
        if (this.ctx) {
            this.ctx.fillStyle = '#000';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#fff';
            this.ctx.font = '20px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText('Loading study from worklist...', this.canvas.width / 2, this.canvas.height / 2);
        }
    };
    
    // Improve the loadStudy method to ensure proper UI updates
    const originalLoadStudy = DicomViewer.prototype.loadStudy;
    
    DicomViewer.prototype.loadStudy = async function(studyId) {
        try {
            console.log(`Loading study ${studyId}...`);
            
            // Show loading indicator
            this.showLoadingState();
            
            const response = await fetch(`/viewer/api/studies/${studyId}/images/`);
            
            if (!response.ok) {
                const errorText = await response.text();
                let errorMessage;
                try {
                    const errorData = JSON.parse(errorText);
                    errorMessage = errorData.error || `HTTP ${response.status}: ${response.statusText}`;
                } catch (e) {
                    errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            
            if (!data.images || data.images.length === 0) {
                throw new Error('No images found in this study');
            }
            
            console.log(`Found ${data.images.length} images in study`);
            
            this.currentStudy = data.study;
            this.currentSeries = data.series || null;
            this.currentImages = data.images;
            this.currentImageIndex = 0;
            
            // Clear any existing measurements for new study
            this.measurements = [];
            this.annotations = [];
            this.updateMeasurementsList();
            
            // Update UI immediately
            this.updatePatientInfo();
            this.updateSliders();
            
            // Load the first image
            await this.loadCurrentImage();
            
            // Load clinical info if available
            if (window.loadClinicalInfo && typeof window.loadClinicalInfo === 'function') {
                window.loadClinicalInfo(studyId);
            }
            
            // Force a redraw to ensure the image is displayed
            setTimeout(() => {
                this.redraw();
                this.updatePatientInfo();
            }, 100);
            
            console.log('Study loaded successfully');
            
        } catch (error) {
            console.error('Error loading study:', error);
            this.showError('Error loading study: ' + error.message);
            
            // Clear canvas
            this.ctx.fillStyle = '#000';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#ff0000';
            this.ctx.font = '16px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText('Failed to load study', this.canvas.width / 2, this.canvas.height / 2 - 20);
            this.ctx.fillText(error.message, this.canvas.width / 2, this.canvas.height / 2 + 20);
            
            // Reset patient info on error
            this.updatePatientInfo();
        }
    };
    
    // Improve the updatePatientInfo method to ensure it's always visible
    const originalUpdatePatientInfo = DicomViewer.prototype.updatePatientInfo;
    
    DicomViewer.prototype.updatePatientInfo = function() {
        const patientInfo = document.getElementById('patient-info');
        if (!patientInfo) {
            console.warn('Patient info element not found');
            return;
        }
        
        if (!this.currentStudy) {
            patientInfo.textContent = 'Patient: - | Study Date: - | Modality: -';
            patientInfo.style.display = 'block';
            return;
        }
        
        patientInfo.textContent = `Patient: ${this.currentStudy.patient_name} | Study Date: ${this.currentStudy.study_date} | Modality: ${this.currentStudy.modality}`;
        patientInfo.style.display = 'block';
        
        // Update image info in right panel if elements exist
        const currentImageData = this.currentImages[this.currentImageIndex];
        if (currentImageData) {
            const infoDimensions = document.getElementById('info-dimensions');
            const infoPixelSpacing = document.getElementById('info-pixel-spacing');
            const infoSeries = document.getElementById('info-series');
            const infoInstitution = document.getElementById('info-institution');
            
            if (infoDimensions) {
                infoDimensions.textContent = `${currentImageData.rows} × ${currentImageData.columns}`;
            }
            
            if (infoPixelSpacing && currentImageData.pixel_spacing_x && currentImageData.pixel_spacing_y) {
                infoPixelSpacing.textContent = `${currentImageData.pixel_spacing_x} × ${currentImageData.pixel_spacing_y} mm`;
            }
            
            if (infoSeries && currentImageData.series_description) {
                infoSeries.textContent = currentImageData.series_description;
            }
            
            if (infoInstitution && this.currentStudy.institution_name) {
                infoInstitution.textContent = this.currentStudy.institution_name;
            }
        }
    };
}

// Add a global function to manually trigger study loading (for debugging)
window.loadStudyFromWorklist = function(studyId) {
    if (window.viewer) {
        window.viewer.loadStudy(studyId);
    } else {
        console.error('Viewer not initialized');
    }
};

// Add initialization check
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, checking for initial study ID:', window.initialStudyId);
    
    // Ensure viewer is properly initialized with initial study
    if (window.initialStudyId && window.viewer) {
        console.log('Found initial study ID and viewer, ensuring proper initialization');
        setTimeout(() => {
            if (window.viewer && !window.viewer.currentStudy) {
                console.log('Viewer exists but no study loaded, attempting to load initial study');
                window.viewer.loadStudy(window.initialStudyId);
            }
        }, 1000);
    }
});