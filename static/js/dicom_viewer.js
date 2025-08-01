// static/js/dicom_viewer.js

class DicomViewer {
    constructor(initialStudyId = null) {
        this.canvas = document.getElementById('dicom-canvas');
        if (!this.canvas) {
            console.error('Canvas element not found! Make sure element with id "dicom-canvas" exists.');
            return;
        }
        
        this.ctx = this.canvas.getContext('2d');
        if (!this.ctx) {
            console.error('Failed to get 2D context from canvas!');
            return;
        }
        
        // State variables
        this.currentStudy = null;
        this.currentSeries = null;
        this.currentImages = [];
        this.currentImageIndex = 0;
        this.currentImage = null;
        
        // Display parameters optimized for medical imaging
        this.windowWidth = 400;  // Default window width
        this.windowLevel = 40;   // Default window level
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.inverted = false;
        this.crosshair = false;
        
        // Tools
        this.activeTool = 'zoom';
        this.measurements = [];
        this.annotations = [];
        this.currentMeasurement = null;
        // Ellipse (HU) drawing state
        this.currentEllipse = null;

        // Measurement unit (px, mm or cm)
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
        
        // Enhanced Window presets for optimal tissue differentiation
        this.windowPresets = {
            'lung': { ww: 1500, wl: -600, description: 'Lung/Air - Optimal contrast for air vs soft tissue' },
            'bone': { ww: 2000, wl: 300, description: 'Bone - High contrast for bone vs soft tissue' },
            'soft': { ww: 400, wl: 40, description: 'Soft Tissue - Optimized for organ differentiation' },
            'brain': { ww: 100, wl: 50, description: 'Brain - Fine detail in neural tissue' },
            'abdomen': { ww: 350, wl: 50, description: 'Abdomen - Organ and vessel contrast' },
            'mediastinum': { ww: 400, wl: 20, description: 'Mediastinum - Vessel and tissue contrast' },
            'liver': { ww: 150, wl: 60, description: 'Liver - Hepatic lesion detection' },
            'cardiac': { ww: 600, wl: 200, description: 'Cardiac - Heart muscle and vessels' },
            'spine': { ww: 1000, wl: 400, description: 'Spine - Bone and disc contrast' },
            'angio': { ww: 700, wl: 150, description: 'Angiographic - Vessel enhancement' }
        };
        
        // Notifications
        this.notificationCheckInterval = null;
        
        // Store initial study ID
        this.initialStudyId = initialStudyId;
        
        // Manual enhancement controls - optimized for medical imaging
        this.manualBrightness = null; // When null, use auto calculation
        this.manualContrast = null;   // When null, use auto calculation  
        this.manualGamma = null;      // When null, use auto calculation
        this.densityMultiplier = 1.3; // Enhanced density enhancement for superior tissue visualization
        this.contrastBoostMultiplier = 1.25; // Increased contrast boost for medical images
        this.highQualityMode = true;  // Enable high quality mode by default
        
        // Enhanced medical imaging optimizations
        this.high_quality = 'true';
        this.density_enhancement = 'true';
        this.contrast_optimization = 'medical';
        
        // Medical contrast optimization configuration
        const medical_contrast_config = {
            contrast_optimization: 'medical',
            high_quality: 'true',
            density_enhancement: 'true'
        };
        
        this.init();
    }
    
    async init() {
        // Check if already initialized to prevent duplicate initialization
        if (this.initialized) {
            console.log('DicomViewer already initialized, skipping...');
            return;
        }
        
        console.log('Initializing DicomViewer with initialStudyId:', this.initialStudyId);
        
        // Initialize enhanced viewer features
        this.initializeEnhancedViewer();
        
        try {
            this.setupEventListeners();
            this.resizeCanvas();
            
            // Mark as initialized
            this.initialized = true;
            
            // Load initial study if provided
            if (this.initialStudyId) {
                console.log('Loading initial study:', this.initialStudyId);
                try {
                    await this.loadStudy(this.initialStudyId);
                } catch (error) {
                    console.error('Error loading initial study:', error);
                    this.showError('Failed to load initial study: ' + error.message);
                }
            } else {
                // Show initial state
                this.ctx.fillStyle = '#000';
                this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                
                const displayWidth = this.canvas.style.width ? parseInt(this.canvas.style.width) : this.canvas.width;
                const displayHeight = this.canvas.style.height ? parseInt(this.canvas.style.height) : this.canvas.height;
                
                this.ctx.fillStyle = '#00ff00';
                this.ctx.font = '18px Arial';
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';
                this.ctx.fillText('Enhanced DICOM Viewer Ready', displayWidth / 2, displayHeight / 2);
                this.ctx.font = '14px Arial';
                this.ctx.fillStyle = '#888';
                this.ctx.fillText('Load DICOM files or select from worklist', displayWidth / 2, displayHeight / 2 + 30);
            }
            
            console.log('DicomViewer initialization completed successfully');
            
        } catch (error) {
            console.error('Error during DicomViewer initialization:', error);
            this.showError('Failed to initialize DICOM viewer: ' + error.message);
        }
    }
    
    setupCanvas() {
        // Set canvas size with enhanced resolution handling for medical imaging
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
        
        // Enhanced image smoothing configuration for medical images
        this.ctx.imageSmoothingEnabled = true; // Enable for better quality at different zoom levels
        this.ctx.imageSmoothingQuality = 'high';
        
        // Set additional canvas properties for enhanced rendering
        this.enhancedRendering = true;
        this.pixelDensityScale = window.devicePixelRatio || 1;
        
        // Conservative rendering parameters for diagnostic quality
        this.renderingOptions = {
            preserveSharpness: true,
            enhanceDensityContrast: false, // Disabled for stable brightness
            antialiasing: false, // Disable for pixel-perfect medical imaging
            subpixelRendering: false, // Disabled to prevent artifacts
            highQualityMode: true,
            densityEnhancement: false, // Disabled to prevent over-processing
            contrastOptimization: 'conservative', // Conservative approach
            imageSmoothingEnabled: false // Preserve medical image sharpness
        };
        
        console.log(`Canvas initialized with enhanced rendering, pixel density scale: ${this.pixelDensityScale}`);
    }
    
    resizeCanvas() {
        const viewport = document.querySelector('.viewport-container');
        if (viewport) {
            // Get the actual available viewport dimensions
            const viewportRect = viewport.getBoundingClientRect();
            const displayWidth = viewportRect.width;
            const displayHeight = viewportRect.height;
            
            // Use device pixel ratio for sharp rendering on high-DPI screens
            const devicePixelRatio = window.devicePixelRatio || 1;
            
            // Set canvas internal resolution to match device pixels for crisp rendering
            this.canvas.width = Math.round(displayWidth * devicePixelRatio);
            this.canvas.height = Math.round(displayHeight * devicePixelRatio);
            
            // Set display size to maintain aspect ratio
            this.canvas.style.width = displayWidth + 'px';
            this.canvas.style.height = displayHeight + 'px';
            
            // Scale the context to match the device pixel ratio
            this.ctx.scale(devicePixelRatio, devicePixelRatio);
            
            console.log(`Canvas resized to ${displayWidth}x${displayHeight} (${this.canvas.width}x${this.canvas.height} internal)`);
        }
    }
    
    setupEventListeners() {
        // Header buttons
        document.getElementById('worklist-btn')?.addEventListener('click', () => {
            window.location.href = '/worklist/';
        });
        
        document.getElementById('load-dicom-btn')?.addEventListener('click', () => {
            this.showUploadModal();
        });
        
        document.getElementById('series-btn')?.addEventListener('click', () => {
            this.toggleSeriesSelector();
        });
        
        document.getElementById('logout-btn')?.addEventListener('click', () => {
            window.location.href = '/logout/';
        });
        
        // Tool buttons
        document.getElementById('window-btn')?.addEventListener('click', () => {
            this.handleToolClick('window');
        });
        
        document.getElementById('zoom-btn')?.addEventListener('click', () => {
            this.handleToolClick('zoom');
        });
        
        document.getElementById('pan-btn')?.addEventListener('click', () => {
            this.handleToolClick('pan');
        });
        
        document.getElementById('measure-btn')?.addEventListener('click', () => {
            this.handleToolClick('measure');
        });
        
        document.getElementById('ellipse-btn')?.addEventListener('click', () => {
            this.handleToolClick('ellipse');
        });
        
        document.getElementById('annotate-btn')?.addEventListener('click', () => {
            this.handleToolClick('annotate');
        });
        
        document.getElementById('crosshair-btn')?.addEventListener('click', () => {
            this.toggleCrosshair();
        });
        
        document.getElementById('invert-btn')?.addEventListener('click', () => {
            this.invertImage();
        });
        
        // Toggle switches
        document.getElementById('density-toggle')?.addEventListener('click', () => {
            this.toggleEnhancement('density');
        });
        
        document.getElementById('highres-toggle')?.addEventListener('click', () => {
            this.toggleEnhancement('highres');
        });
        
        document.getElementById('contrast-toggle')?.addEventListener('click', () => {
            this.toggleEnhancement('contrast');
        });
        
        // Sliders
        document.getElementById('window-width-slider')?.addEventListener('input', (e) => {
            this.windowWidth = parseInt(e.target.value);
            this.updateWindowLevelDisplay();
            this.updateDisplay();
        });
        
        document.getElementById('window-level-slider')?.addEventListener('input', (e) => {
            this.windowLevel = parseInt(e.target.value);
            this.updateWindowLevelDisplay();
            this.updateDisplay();
        });
        
        // Preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const preset = btn.dataset.preset;
                this.applyPreset(preset);
            });
        });
        
        // Navigation controls
        document.getElementById('slice-slider')?.addEventListener('input', (e) => {
            this.currentImageIndex = parseInt(e.target.value) - 1;
            this.loadCurrentImage();
        });
        
        document.getElementById('prev-slice-btn')?.addEventListener('click', () => {
            this.previousSlice();
        });
        
        document.getElementById('next-slice-btn')?.addEventListener('click', () => {
            this.nextSlice();
        });
        
        // Clear buttons
        document.getElementById('clear-measurements-btn')?.addEventListener('click', () => {
            this.clearMeasurements();
        });
        
        document.getElementById('clear-annotations-btn')?.addEventListener('click', () => {
            this.clearAnnotations();
        });
        
        // Canvas event listeners
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        this.canvas.addEventListener('dblclick', (e) => this.onDoubleClick(e));
        
        // Upload modal
        document.getElementById('close-upload-modal')?.addEventListener('click', () => {
            this.hideUploadModal();
        });
        
        // Setup upload functionality
        this.setupUploadModal();
        
        console.log('Event listeners setup completed');
    }
    
    handleToolClick(tool) {
        // Remove active class from all tool buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Add active class to clicked button
        const toolBtn = document.getElementById(tool + '-btn');
        if (toolBtn) {
            toolBtn.classList.add('active');
        }
        
        // Update active tool
        this.activeTool = tool;
        
        // Update cursor based on tool
        switch (tool) {
            case 'window':
                this.canvas.style.cursor = 'crosshair';
                break;
            case 'zoom':
                this.canvas.style.cursor = 'zoom-in';
                break;
            case 'pan':
                this.canvas.style.cursor = 'grab';
                break;
            case 'measure':
                this.canvas.style.cursor = 'crosshair';
                break;
            case 'ellipse':
                this.canvas.style.cursor = 'crosshair';
                break;
            case 'annotate':
                this.canvas.style.cursor = 'text';
                break;
            default:
                this.canvas.style.cursor = 'default';
        }
        
        console.log('Active tool changed to:', tool);
    }
    
    toggleCrosshair() {
        this.crosshair = !this.crosshair;
        const crosshairElement = document.getElementById('crosshair');
        const statusElement = document.getElementById('crosshair-status');
        
        if (crosshairElement) {
            crosshairElement.style.display = this.crosshair ? 'block' : 'none';
        }
        
        if (statusElement) {
            statusElement.textContent = this.crosshair ? 'ON' : 'OFF';
        }
        
        this.updateDisplay();
    }
    
    invertImage() {
        this.inverted = !this.inverted;
        this.updateDisplay();
    }
    
    toggleEnhancement(type) {
        const toggle = document.getElementById(type + '-toggle');
        const status = document.getElementById(type + '-status');
        
        if (toggle && status) {
            toggle.classList.toggle('active');
            const isActive = toggle.classList.contains('active');
            status.textContent = isActive ? 'On' : 'Off';
            
            // Apply enhancement based on type
            switch (type) {
                case 'density':
                    this.density_enhancement = isActive ? 'true' : 'false';
                    break;
                case 'highres':
                    this.high_quality = isActive ? 'true' : 'false';
                    break;
                case 'contrast':
                    this.contrast_optimization = isActive ? 'medical' : 'conservative';
                    break;
            }
            
            this.updateDisplay();
        }
    }
    
    updateWindowLevelDisplay() {
        const wwValue = document.getElementById('window-width-value');
        const wlValue = document.getElementById('window-level-value');
        const wwDisplay = document.getElementById('ww-display');
        const wlDisplay = document.getElementById('wl-display');
        
        if (wwValue) wwValue.textContent = this.windowWidth;
        if (wlValue) wlValue.textContent = this.windowLevel;
        if (wwDisplay) wwDisplay.textContent = this.windowWidth;
        if (wlDisplay) wlDisplay.textContent = this.windowLevel;
    }
    
    applyPreset(presetName) {
        const preset = this.windowPresets[presetName];
        if (preset) {
            this.windowWidth = preset.ww;
            this.windowLevel = preset.wl;
            
            // Update sliders
            const wwSlider = document.getElementById('window-width-slider');
            const wlSlider = document.getElementById('window-level-slider');
            
            if (wwSlider) wwSlider.value = this.windowWidth;
            if (wlSlider) wlSlider.value = this.windowLevel;
            
            this.updateWindowLevelDisplay();
            this.updateDisplay();
            
            this.showSuccessNotification(`Applied ${presetName} preset`);
        }
    }
    
    previousSlice() {
        if (this.currentImageIndex > 0) {
            this.currentImageIndex--;
            this.loadCurrentImage();
        }
    }
    
    nextSlice() {
        if (this.currentImageIndex < this.currentImages.length - 1) {
            this.currentImageIndex++;
            this.loadCurrentImage();
        }
    }
    
    clearMeasurements() {
        this.measurements = [];
        this.updateMeasurementDisplay();
        this.updateDisplay();
        this.showSuccessNotification('All measurements cleared');
    }
    
    clearAnnotations() {
        this.annotations = [];
        this.updateAnnotationDisplay();
        this.updateDisplay();
        this.showSuccessNotification('All annotations cleared');
    }
    
    updateMeasurementDisplay() {
        const countElement = document.getElementById('measurement-count');
        if (countElement) {
            countElement.textContent = this.measurements.length > 0 ? 
                `${this.measurements.length} measurement(s)` : 'No measurements';
        }
    }
    
    updateAnnotationDisplay() {
        const countElement = document.getElementById('annotation-count');
        if (countElement) {
            countElement.textContent = this.annotations.length > 0 ? 
                `${this.annotations.length} annotation(s)` : 'No annotations';
        }
    }
    
    toggleSeriesSelector() {
        const selector = document.getElementById('series-selector');
        if (selector) {
            selector.classList.toggle('show');
            if (selector.classList.contains('show')) {
                this.loadSeriesSelector();
            }
        }
    }
    
    setupUploadModal() {
        const dropArea = document.getElementById('upload-drop-area');
        const folderDropArea = document.getElementById('folder-drop-area');
        const fileInput = document.getElementById('file-input');
        const folderInput = document.getElementById('folder-input');
        
        // File upload
        if (dropArea && fileInput) {
            dropArea.addEventListener('click', () => fileInput.click());
            dropArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropArea.style.borderColor = '#00ff00';
            });
            dropArea.addEventListener('dragleave', () => {
                dropArea.style.borderColor = 'rgba(0, 255, 0, 0.3)';
            });
            dropArea.addEventListener('drop', (e) => {
                e.preventDefault();
                dropArea.style.borderColor = 'rgba(0, 255, 0, 0.3)';
                this.uploadFiles(e.dataTransfer.files);
            });
            
            fileInput.addEventListener('change', (e) => {
                this.uploadFiles(e.target.files);
            });
        }
        
        // Folder upload
        if (folderDropArea && folderInput) {
            folderDropArea.addEventListener('click', () => folderInput.click());
            folderDropArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                folderDropArea.style.borderColor = '#00ff00';
            });
            folderDropArea.addEventListener('dragleave', () => {
                folderDropArea.style.borderColor = 'rgba(0, 255, 0, 0.3)';
            });
            folderDropArea.addEventListener('drop', (e) => {
                e.preventDefault();
                folderDropArea.style.borderColor = 'rgba(0, 255, 0, 0.3)';
                this.uploadFolder(e.dataTransfer.files);
            });
            
            folderInput.addEventListener('change', (e) => {
                this.uploadFolder(e.target.files);
            });
        }
    }
    
    showUploadModal() {
        const modal = document.getElementById('upload-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }
    
    hideUploadModal() {
        const modal = document.getElementById('upload-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    async uploadFiles(files) {
        if (!files || files.length === 0) return;
        
        this.showLoadingState('Uploading DICOM files...');
        
        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }
        
        try {
            const response = await fetch('/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.hideUploadModal();
                this.showSuccessNotification('Files uploaded successfully');
                
                // Load the uploaded study
                if (result.study_id) {
                    await this.loadStudy(result.study_id);
                }
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showError('Upload failed: ' + error.message);
        } finally {
            this.hideLoadingState();
        }
    }
    
    async uploadFolder(files) {
        if (!files || files.length === 0) return;
        
        this.showLoadingState('Uploading DICOM folder...');
        
        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }
        
        try {
            const response = await fetch('/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.hideUploadModal();
                this.showSuccessNotification('Folder uploaded successfully');
                
                // Load the uploaded study
                if (result.study_id) {
                    await this.loadStudy(result.study_id);
                }
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showError('Upload failed: ' + error.message);
        } finally {
            this.hideLoadingState();
        }
    }
    
    async loadStudy(studyId) {
        this.showLoadingState('Loading study...');
        
        try {
            const response = await fetch(`/api/study/${studyId}/`);
            if (!response.ok) throw new Error('Failed to load study');
            
            const studyData = await response.json();
            this.currentStudy = studyData;
            
            // Update patient information display
            this.updatePatientInfo(studyData);
            
            // Load first series
            if (studyData.series && studyData.series.length > 0) {
                await this.loadSeries(studyData.series[0]);
            }
            
            this.hideLoadingState();
            this.showSuccessNotification('Study loaded successfully');
            
        } catch (error) {
            console.error('Error loading study:', error);
            this.showError('Failed to load study: ' + error.message);
            this.hideLoadingState();
        }
    }
    
    updatePatientInfo(studyData) {
        const patientName = document.getElementById('patient-name');
        const studyDate = document.getElementById('study-date');
        const modality = document.getElementById('modality');
        
        if (patientName) patientName.textContent = studyData.patient_name || '-';
        if (studyDate) studyDate.textContent = studyData.study_date || '-';
        if (modality) modality.textContent = studyData.modality || '-';
    }
    
    async loadSeries(seriesData) {
        this.currentSeries = seriesData;
        this.currentImages = seriesData.images || [];
        this.currentImageIndex = 0;
        
        // Update slice slider
        const sliceSlider = document.getElementById('slice-slider');
        if (sliceSlider) {
            sliceSlider.max = this.currentImages.length;
            sliceSlider.value = 1;
        }
        
        // Update slice info
        this.updateSliceInfo();
        
        if (this.currentImages.length > 0) {
            await this.loadCurrentImage();
        }
    }
    
    updateSliceInfo() {
        const sliceInfo = document.getElementById('slice-info');
        if (sliceInfo) {
            sliceInfo.textContent = `Slice ${this.currentImageIndex + 1}/${this.currentImages.length}`;
        }
        
        const sliceDisplay = document.getElementById('slice-display');
        if (sliceDisplay) {
            sliceDisplay.textContent = `${this.currentImageIndex + 1}/${this.currentImages.length}`;
        }
    }
    
    async loadCurrentImage() {
        if (!this.currentImages || this.currentImageIndex >= this.currentImages.length) {
            return;
        }
        
        const imageData = this.currentImages[this.currentImageIndex];
        
        try {
            const response = await fetch(`/api/image/${imageData.id}/`);
            if (!response.ok) throw new Error('Failed to load image');
            
            const imageResult = await response.json();
            this.currentImage = imageResult;
            
            this.updateSliceInfo();
            this.updateDisplay();
            
        } catch (error) {
            console.error('Error loading image:', error);
            this.showError('Failed to load image: ' + error.message);
        }
    }
    
    updateDisplay() {
        if (!this.currentImage) return;
        
        // Clear canvas
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Load and display image
        const img = new Image();
        img.onload = () => {
            // Apply window/level
            const processedImg = this.applyWindowLevel(img);
            
            // Calculate display dimensions
            const canvasWidth = this.canvas.width;
            const canvasHeight = this.canvas.height;
            const imgWidth = processedImg.width;
            const imgHeight = processedImg.height;
            
            // Calculate scaling to fit canvas
            const scaleX = canvasWidth / imgWidth;
            const scaleY = canvasHeight / imgHeight;
            const scale = Math.min(scaleX, scaleY) * this.zoomFactor;
            
            const displayWidth = imgWidth * scale;
            const displayHeight = imgHeight * scale;
            
            // Center the image
            const x = (canvasWidth - displayWidth) / 2 + this.panX;
            const y = (canvasHeight - displayHeight) / 2 + this.panY;
            
            // Draw image
            this.ctx.drawImage(processedImg, x, y, displayWidth, displayHeight);
            
            // Draw overlays
            this.drawOverlays();
            
            // Update zoom display
            const zoomDisplay = document.getElementById('zoom-display');
            if (zoomDisplay) {
                zoomDisplay.textContent = `${Math.round(this.zoomFactor * 100)}%`;
            }
        };
        
        img.src = this.currentImage.image_url;
    }
    
    applyWindowLevel(img) {
        // Create a temporary canvas for window/level processing
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        
        tempCanvas.width = img.width;
        tempCanvas.height = img.height;
        
        // Draw original image
        tempCtx.drawImage(img, 0, 0);
        
        // Get image data for processing
        const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
        const data = imageData.data;
        
        // Apply window/level transformation
        const min = this.windowLevel - this.windowWidth / 2;
        const max = this.windowLevel + this.windowWidth / 2;
        
        for (let i = 0; i < data.length; i += 4) {
            let value = data[i]; // Use red channel for grayscale
            
            // Apply window/level
            if (value < min) value = 0;
            else if (value > max) value = 255;
            else value = ((value - min) / (max - min)) * 255;
            
            // Apply inversion if enabled
            if (this.inverted) {
                value = 255 - value;
            }
            
            data[i] = data[i + 1] = data[i + 2] = value;
        }
        
        // Put processed data back
        tempCtx.putImageData(imageData, 0, 0);
        
        return tempCanvas;
    }
    
    drawOverlays() {
        // Draw crosshair
        if (this.crosshair) {
            this.drawCrosshair();
        }
        
        // Draw measurements
        this.drawMeasurements();
        
        // Draw annotations
        this.drawAnnotations();
    }
    
    drawCrosshair() {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        
        this.ctx.strokeStyle = '#00ffff';
        this.ctx.lineWidth = 1;
        this.ctx.setLineDash([5, 5]);
        
        // Horizontal line
        this.ctx.beginPath();
        this.ctx.moveTo(0, centerY);
        this.ctx.lineTo(this.canvas.width, centerY);
        this.ctx.stroke();
        
        // Vertical line
        this.ctx.beginPath();
        this.ctx.moveTo(centerX, 0);
        this.ctx.lineTo(centerX, this.canvas.height);
        this.ctx.stroke();
        
        this.ctx.setLineDash([]);
    }
    
    drawMeasurements() {
        // Draw existing measurements
        this.measurements.forEach(measurement => {
            this.ctx.strokeStyle = '#00ff00';
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.moveTo(measurement.start.x, measurement.start.y);
            this.ctx.lineTo(measurement.end.x, measurement.end.y);
            this.ctx.stroke();
            
            // Draw measurement text
            this.ctx.fillStyle = '#00ff00';
            this.ctx.font = '12px Arial';
            this.ctx.fillText(measurement.value, measurement.end.x + 5, measurement.end.y - 5);
        });
    }
    
    drawAnnotations() {
        // Draw existing annotations
        this.annotations.forEach(annotation => {
            this.ctx.fillStyle = annotation.color;
            this.ctx.font = `${annotation.fontSize}px Arial`;
            this.ctx.fillText(annotation.text, annotation.x, annotation.y);
        });
    }
    
    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        switch (this.activeTool) {
            case 'pan':
                this.isDragging = true;
                this.dragStart = { x: x - this.panX, y: y - this.panY };
                this.canvas.style.cursor = 'grabbing';
                break;
            case 'measure':
                this.startMeasurement(x, y);
                break;
            case 'ellipse':
                this.startEllipse(x, y);
                break;
            case 'annotate':
                this.addAnnotation(x, y);
                break;
        }
    }
    
    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.isDragging && this.activeTool === 'pan') {
            this.panX = x - this.dragStart.x;
            this.panY = y - this.dragStart.y;
            this.updateDisplay();
        }
        
        if (this.activeTool === 'measure' && this.currentMeasurement) {
            this.currentMeasurement.end = { x, y };
            this.updateDisplay();
        }
        
        if (this.activeTool === 'ellipse' && this.currentEllipse) {
            this.currentEllipse.end = { x, y };
            this.updateDisplay();
        }
    }
    
    onMouseUp(e) {
        if (this.isDragging) {
            this.isDragging = false;
            this.canvas.style.cursor = 'grab';
        }
        
        if (this.activeTool === 'measure' && this.currentMeasurement) {
            this.endMeasurement();
        }
        
        if (this.activeTool === 'ellipse' && this.currentEllipse) {
            this.endEllipse();
        }
    }
    
    onWheel(e) {
        if (this.activeTool === 'zoom') {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomFactor *= delta;
            this.zoomFactor = Math.max(0.1, Math.min(5.0, this.zoomFactor));
            this.updateDisplay();
        }
    }
    
    onDoubleClick(e) {
        if (this.activeTool === 'window') {
            // Reset view
            this.zoomFactor = 1.0;
            this.panX = 0;
            this.panY = 0;
            this.updateDisplay();
        }
    }
    
    startMeasurement(x, y) {
        this.currentMeasurement = {
            start: { x, y },
            end: { x, y }
        };
    }
    
    endMeasurement() {
        if (this.currentMeasurement) {
            const distance = Math.sqrt(
                Math.pow(this.currentMeasurement.end.x - this.currentMeasurement.start.x, 2) +
                Math.pow(this.currentMeasurement.end.y - this.currentMeasurement.start.y, 2)
            );
            
            this.currentMeasurement.value = `${distance.toFixed(1)}px`;
            this.measurements.push(this.currentMeasurement);
            this.currentMeasurement = null;
            
            this.updateMeasurementDisplay();
            this.updateDisplay();
        }
    }
    
    startEllipse(x, y) {
        this.currentEllipse = {
            start: { x, y },
            end: { x, y }
        };
    }
    
    endEllipse() {
        if (this.currentEllipse) {
            // Calculate ellipse parameters
            const centerX = (this.currentEllipse.start.x + this.currentEllipse.end.x) / 2;
            const centerY = (this.currentEllipse.start.y + this.currentEllipse.end.y) / 2;
            const radiusX = Math.abs(this.currentEllipse.end.x - this.currentEllipse.start.x) / 2;
            const radiusY = Math.abs(this.currentEllipse.end.y - this.currentEllipse.start.y) / 2;
            
            this.currentEllipse.center = { x: centerX, y: centerY };
            this.currentEllipse.radiusX = radiusX;
            this.currentEllipse.radiusY = radiusY;
            
            this.measurements.push(this.currentEllipse);
            this.currentEllipse = null;
            
            this.updateMeasurementDisplay();
            this.updateDisplay();
        }
    }
    
    addAnnotation(x, y) {
        const text = prompt('Enter annotation text:');
        if (text) {
            this.annotations.push({
                x: x,
                y: y,
                text: text,
                color: '#ffff00',
                fontSize: 14
            });
            
            this.updateAnnotationDisplay();
            this.updateDisplay();
        }
    }
    
    showLoadingState(message = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        const text = document.getElementById('loading-text');
        
        if (overlay) overlay.style.display = 'flex';
        if (text) text.textContent = message;
    }
    
    hideLoadingState() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'none';
    }
    
    updateStatus(message) {
        console.log('Status:', message);
    }
    
    showSuccessNotification(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications-container');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        container.appendChild(notification);
        
        // Show notification
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Remove notification after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                container.removeChild(notification);
            }, 300);
        }, 5000);
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    initializeEnhancedViewer() {
        console.log('Enhanced viewer features initialized');
    }
}

// Global functions for upload modal
function switchUploadTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.upload-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.upload-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById(tabName + '-tab');
    if (selectedContent) {
        selectedContent.classList.add('active');
    }
    
    // Add active class to selected tab
    const selectedTab = document.querySelector(`[onclick="switchUploadTab('${tabName}')"]`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
}

function connectToPACS() {
    const ip = document.getElementById('pacs-ip').value;
    const port = document.getElementById('pacs-port').value;
    const ae = document.getElementById('pacs-ae').value;
    
    if (!ip || !port || !ae) {
        alert('Please fill in all PACS connection fields');
        return;
    }
    
    // Implement PACS connection logic here
    console.log('Connecting to PACS:', { ip, port, ae });
    alert('PACS connection feature not implemented yet');
}

function connectToCloud(provider) {
    console.log('Connecting to cloud provider:', provider);
    alert(`${provider} cloud connection feature not implemented yet`);
}
