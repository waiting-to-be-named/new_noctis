// Fixed DICOM Viewer JavaScript
// This version addresses duplicate buttons and no images displayed issues

class DicomViewer {
    constructor(initialStudyId = null) {
        this.canvas = document.getElementById('dicom-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // State variables
        this.currentStudy = null;
        this.currentSeries = null;
        this.currentImages = [];
        this.currentImageIndex = 0;
        this.currentImage = null;
        
        // Display parameters
        this.windowWidth = 400;
        this.windowLevel = 40;
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.inverted = false;
        this.crosshair = false;
        
        // Tools
        this.activeTool = 'windowing';
        this.measurements = [];
        this.annotations = [];
        this.currentMeasurement = null;
        this.currentEllipse = null;

        // Measurement unit
        this.measurementUnit = 'mm';
        this.isDragging = false;
        this.dragStart = null;
        
        // Volume measurement
        this.volumeTool = false;
        this.volumeContour = [];
        this.currentContour = null;
        
        // Annotation state
        this.selectedAnnotation = null;
        this.isEditingAnnotation = false;
        
        // AI Analysis
        this.aiAnalysisResults = null;
        this.showAIHighlights = false;
        
        // 3D Reconstruction
        this.reconstructionType = 'mpr';
        this.is3DEnabled = false;
        
        // Window presets
        this.windowPresets = {
            'lung': { ww: 1500, wl: -600 },
            'bone': { ww: 2000, wl: 300 },
            'soft': { ww: 400, wl: 40 },
            'brain': { ww: 100, wl: 50 }
        };
        
        // Notifications
        this.notificationCheckInterval = null;
        
        // Store initial study ID
        this.initialStudyId = initialStudyId;
        
        // Flag to prevent duplicate initialization
        this.initialized = false;
        
        this.init();
    }
    
    async init() {
        if (this.initialized) {
            console.log('DicomViewer already initialized, skipping...');
            return;
        }
        
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
        
        this.initialized = true;
    }
    
    setupCanvas() {
        // Set canvas size
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    resizeCanvas() {
        const viewport = document.querySelector('.viewport');
        if (viewport) {
            // Use devicePixelRatio for high-DPI displays
            const devicePixelRatio = window.devicePixelRatio || 1;
            const displayWidth = viewport.clientWidth;
            const displayHeight = viewport.clientHeight;
            
            // Set canvas size
            this.canvas.style.width = displayWidth + 'px';
            this.canvas.style.height = displayHeight + 'px';
            
            // Set actual canvas size
            this.canvas.width = displayWidth * devicePixelRatio;
            this.canvas.height = displayHeight * devicePixelRatio;
            
            // Scale context to match device pixel ratio
            this.ctx.scale(devicePixelRatio, devicePixelRatio);
        }
    }
    
    setupEventListeners() {
        // Tool buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tool = btn.dataset.tool;
                this.handleToolClick(tool);
            });
        });
        
        // Window/Level sliders
        const wwSlider = document.getElementById('ww-slider');
        const wlSlider = document.getElementById('wl-slider');
        const zoomSlider = document.getElementById('zoom-slider');
        const sliceSlider = document.getElementById('slice-slider');
        
        if (wwSlider) {
            wwSlider.addEventListener('input', (e) => {
                this.windowWidth = parseInt(e.target.value);
                document.getElementById('ww-value').textContent = this.windowWidth;
                this.updateDisplay();
            });
        }
        
        if (wlSlider) {
            wlSlider.addEventListener('input', (e) => {
                this.windowLevel = parseInt(e.target.value);
                document.getElementById('wl-value').textContent = this.windowLevel;
                this.updateDisplay();
            });
        }
        
        if (zoomSlider) {
            zoomSlider.addEventListener('input', (e) => {
                this.zoomFactor = parseInt(e.target.value) / 100;
                document.getElementById('zoom-value').textContent = Math.round(this.zoomFactor * 100) + '%';
                this.updateDisplay();
            });
        }
        
        if (sliceSlider) {
            sliceSlider.addEventListener('input', (e) => {
                this.currentImageIndex = parseInt(e.target.value);
                document.getElementById('slice-value').textContent = this.currentImageIndex + 1;
                this.loadCurrentImage();
            });
        }
        
        // Preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const preset = btn.dataset.preset;
                this.applyPreset(preset);
            });
        });
        
        // Load DICOM button - only add event listener if it doesn't already exist
        const loadDicomBtn = document.getElementById('load-dicom-btn');
        if (loadDicomBtn && !loadDicomBtn.hasAttribute('data-listener-added')) {
            loadDicomBtn.setAttribute('data-listener-added', 'true');
            loadDicomBtn.addEventListener('click', () => {
                this.showUploadModal();
            });
        }
        
        // Worklist button - only add event listener if it doesn't already exist
        const worklistBtn = document.getElementById('worklist-btn');
        if (worklistBtn && !worklistBtn.hasAttribute('data-listener-added')) {
            worklistBtn.setAttribute('data-listener-added', 'true');
            worklistBtn.addEventListener('click', () => {
                window.location.href = '/worklist/';
            });
        }
        
        // Clear measurements - only add event listener if it doesn't already exist
        const clearMeasurementsBtn = document.getElementById('clear-measurements');
        if (clearMeasurementsBtn && !clearMeasurementsBtn.hasAttribute('data-listener-added')) {
            clearMeasurementsBtn.setAttribute('data-listener-added', 'true');
            clearMeasurementsBtn.addEventListener('click', () => {
                this.clearMeasurements();
            });
        }
        
        // Canvas mouse events
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        this.canvas.addEventListener('dblclick', (e) => this.onDoubleClick(e));
        
        // Upload modal events
        this.setupUploadModal();
    }
    
    // Add loading state method
    showLoadingState() {
        if (this.ctx) {
            this.ctx.fillStyle = '#000';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#fff';
            this.ctx.font = '20px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText('Loading study from worklist...', this.canvas.width / 2, this.canvas.height / 2);
        }
    }
    
    // Improve the loadStudy method to ensure proper UI updates
    async loadStudy(studyId) {
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
    }
    
    // Improve the updatePatientInfo method to ensure it's always visible
    updatePatientInfo() {
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
    }
    
    // Add a global function to manually trigger study loading (for debugging)
    static loadStudyFromWorklist(studyId) {
        if (window.viewer) {
            window.viewer.loadStudy(studyId);
        } else {
            console.error('Viewer not initialized');
        }
    }
}

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

// Export for global access
window.DicomViewer = DicomViewer;
window.loadStudyFromWorklist = DicomViewer.loadStudyFromWorklist;