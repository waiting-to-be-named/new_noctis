// static/js/dicom_viewer_fixed.js

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
        this.highQualityMode = true;  // Default to high quality
        
        // Tools
        this.activeTool = 'windowing';
        this.measurements = [];
        this.annotations = [];
        this.currentMeasurement = null;
        this.currentEllipse = null;
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
        
        // Window presets optimized for better density differentiation
        this.windowPresets = {
            'lung': { ww: 1500, wl: -600 },
            'bone': { ww: 2000, wl: 300 },
            'soft': { ww: 350, wl: 50 },  // Narrower window for better soft tissue contrast
            'brain': { ww: 80, wl: 40 },   // Optimized for brain tissue
            'liver': { ww: 150, wl: 60 },  // Added liver preset
            'mediastinum': { ww: 350, wl: 40 }, // Added mediastinum preset
            'abdomen': { ww: 400, wl: 50 }     // Added abdomen preset
        };
        
        // Notifications
        this.notificationCheckInterval = null;
        
        // Store initial study ID
        this.initialStudyId = initialStudyId;
        
        this.init();
    }
    
    async init() {
        console.log('Initializing DicomViewer with initialStudyId:', this.initialStudyId);
        
        this.setupCanvas();
        this.setupEventListeners();
        await this.loadBackendStudies();
        this.setupNotifications();
        this.setupMeasurementUnitSelector();
        this.setup3DControls();
        this.setupAIPanel();
        
        // Load initial study if provided
        if (this.initialStudyId) {
            console.log('Loading initial study:', this.initialStudyId);
            try {
                this.showLoadingState();
                await this.loadStudy(this.initialStudyId);
                setTimeout(() => {
                    this.redraw();
                    this.updatePatientInfo();
                }, 100);
            } catch (error) {
                console.error('Error loading initial study:', error);
                this.showError('Failed to load initial study: ' + error.message);
            }
        }
        
        this.initialized = true;
    }
    
    setupCanvas() {
        // Enable high-quality rendering
        this.ctx.imageSmoothingEnabled = true;
        this.ctx.imageSmoothingQuality = 'high';
        
        // Support for high-DPI displays
        this.devicePixelRatio = window.devicePixelRatio || 1;
        
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    resizeCanvas() {
        const container = this.canvas.parentElement;
        if (container) {
            const rect = container.getBoundingClientRect();
            
            // Support high-DPI displays for better clarity
            const dpr = this.devicePixelRatio || 1;
            
            // Set display size (CSS pixels)
            this.canvas.style.width = rect.width + 'px';
            this.canvas.style.height = rect.height + 'px';
            
            // Set actual size in memory (scaled for high-DPI)
            this.canvas.width = rect.width * dpr;
            this.canvas.height = rect.height * dpr;
            
            // Scale the drawing context to match device pixel ratio
            this.ctx.scale(dpr, dpr);
            
            // Re-enable high-quality rendering after resize
            this.ctx.imageSmoothingEnabled = true;
            this.ctx.imageSmoothingQuality = 'high';
        }
    }
    
    setupEventListeners() {
        // Tool buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const tool = btn.getAttribute('data-tool');
                this.handleToolClick(tool, btn);
                
                // Update active state (except for toggles like high-quality)
                if (tool !== 'high-quality' && tool !== 'crosshair' && tool !== 'invert') {
                    document.querySelectorAll('.tool-btn').forEach(b => {
                        if (b.getAttribute('data-tool') !== 'high-quality') {
                            b.classList.remove('active');
                        }
                    });
                    btn.classList.add('active');
                }
            });
        });
        
        // Preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const preset = btn.getAttribute('data-preset');
                this.applyPreset(preset);
            });
        });
        
        // Load DICOM button - fixed implementation
        const loadDicomBtn = document.getElementById('load-dicom-btn');
        if (loadDicomBtn) {
            loadDicomBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Load DICOM button clicked');
                this.showUploadModal();
            });
        }
        
        // Worklist button - fixed implementation
        const worklistBtn = document.getElementById('worklist-btn');
        if (worklistBtn) {
            worklistBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Worklist button clicked');
                window.location.href = '/worklist/';
            });
        }
        
        // Clear measurements button
        const clearMeasurementsBtn = document.getElementById('clear-measurements');
        if (clearMeasurementsBtn) {
            clearMeasurementsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Clear measurements button clicked');
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
    
    showLoadingState() {
        if (this.ctx) {
            this.ctx.fillStyle = '#000';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#fff';
            this.ctx.font = '20px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText('Loading study...', this.canvas.width / 2, this.canvas.height / 2);
        }
    }
    
    setupUploadModal() {
        const modal = document.getElementById('upload-modal');
        if (!modal) return;
        
        const closeBtn = modal.querySelector('.modal-close');
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        const hiddenFileInput = document.getElementById('hidden-file-input');
        
        // Close modal
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }
        
        // Close modal when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
        
        // File input change
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.uploadFiles(e.target.files);
            });
        }
        
        // Hidden file input for directory upload
        if (hiddenFileInput) {
            hiddenFileInput.addEventListener('change', (e) => {
                this.uploadFolder(e.target.files);
            });
        }
        
        // Drag and drop
        if (uploadArea) {
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('drag-over');
            });
            
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('drag-over');
            });
            
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('drag-over');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.uploadFiles(files);
                }
            });
        }
    }
    
    showUploadModal() {
        const modal = document.getElementById('upload-modal');
        if (modal) {
            modal.style.display = 'block';
        } else {
            console.error('Upload modal not found');
        }
    }
    
    async uploadFiles(files) {
        if (!files || files.length === 0) return;
        
        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }
        
        try {
            const response = await fetch('/viewer/api/upload/', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Upload successful:', result);
                
                // Reload studies after upload
                await this.loadBackendStudies();
                
                // If a study was created, load it
                if (result.study_id) {
                    await this.loadStudy(result.study_id);
                }
            } else {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showError('Upload failed: ' + error.message);
        }
    }
    
    async uploadFolder(files) {
        if (!files || files.length === 0) return;
        
        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }
        
        try {
            const response = await fetch('/viewer/api/upload-folder/', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Folder upload successful:', result);
                
                // Reload studies after upload
                await this.loadBackendStudies();
                
                // If a study was created, load it
                if (result.study_id) {
                    await this.loadStudy(result.study_id);
                }
            } else {
                throw new Error(`Folder upload failed: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Folder upload error:', error);
            this.showError('Folder upload failed: ' + error.message);
        }
    }
    
    async loadBackendStudies() {
        try {
            const response = await fetch('/viewer/api/studies/');
            if (response.ok) {
                const data = await response.json();
                console.log('Loaded studies:', data.studies);
            }
        } catch (error) {
            console.error('Error loading studies:', error);
        }
    }
    
    async loadStudy(studyId) {
        try {
            console.log(`Loading study ${studyId}...`);
            
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
            
            console.log('Study loaded successfully');
            
        } catch (error) {
            console.error('Error loading study:', error);
            this.showError('Error loading study: ' + error.message);
            
            // Clear canvas on error
            this.ctx.fillStyle = '#000';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#ff0000';
            this.ctx.font = '16px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText('Failed to load study', this.canvas.width / 2, this.canvas.height / 2 - 20);
            this.ctx.fillText(error.message, this.canvas.width / 2, this.canvas.height / 2 + 20);
            
            this.updatePatientInfo();
        }
    }
    
    async loadCurrentImage() {
        if (!this.currentImages.length) {
            console.log('No images available');
            return;
        }
        
        const imageData = this.currentImages[this.currentImageIndex];
        console.log(`Loading image ${this.currentImageIndex + 1}/${this.currentImages.length}, ID: ${imageData.id}`);
        
        try {
            const params = new URLSearchParams({
                window_width: this.windowWidth,
                window_level: this.windowLevel,
                inverted: this.inverted,
                high_quality: this.highQualityMode ? 'true' : 'false',
                resolution_factor: this.highQualityMode ? '2.0' : '1.0',
                density_enhancement: this.highQualityMode ? 'true' : 'false',
                contrast_boost: this.highQualityMode ? '1.2' : '1.0'
            });
            
            const response = await fetch(`/viewer/api/images/${imageData.id}/data/?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.image_data) {
                const img = new Image();
                img.onload = () => {
                    console.log('Image loaded successfully');
                    this.currentImage = {
                        image: img,
                        metadata: data.metadata,
                        id: imageData.id,
                        rows: data.metadata.rows,
                        columns: data.metadata.columns,
                        pixel_spacing_x: data.metadata.pixel_spacing_x,
                        pixel_spacing_y: data.metadata.pixel_spacing_y,
                        pixel_spacing: `${data.metadata.pixel_spacing_x},${data.metadata.pixel_spacing_y}`,
                        slice_thickness: data.metadata.slice_thickness,
                        width: img.width,
                        height: img.height
                    };
                    
                    // Ensure canvas is properly sized before drawing
                    this.resizeCanvas();
                    this.updateDisplay();
                    this.loadMeasurements();
                    this.loadAnnotations();
                    this.updatePatientInfo();
                };
                img.onerror = (error) => {
                    console.error('Failed to load image data:', error);
                    console.error('Image source:', img.src);
                    this.showError('Failed to load image. Please try refreshing or selecting another image.');
                };
                img.src = data.image_data;
            } else {
                throw new Error(data.error || 'No image data received');
            }
            
        } catch (error) {
            console.error('Error loading image:', error);
            this.showError('Error loading image: ' + error.message);
        }
    }
    
    showError(message) {
        console.error(message);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <div class="error-content">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff4444;
            color: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            z-index: 1000;
            max-width: 400px;
        `;
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 5000);
    }
    
    updatePatientInfo() {
        const patientInfo = document.getElementById('patient-info');
        if (!patientInfo) return;
        
        if (this.currentStudy) {
            const studyDate = this.currentStudy.study_date || 'Unknown';
            const modality = this.currentStudy.modality || 'Unknown';
            patientInfo.textContent = `Patient: ${this.currentStudy.patient_name} | Study Date: ${studyDate} | Modality: ${modality}`;
        } else {
            patientInfo.textContent = 'Patient: - | Study Date: - | Modality: -';
        }
    }
    
    updateSliders() {
        const wwSlider = document.getElementById('ww-slider');
        const wlSlider = document.getElementById('wl-slider');
        const wwValue = document.getElementById('ww-value');
        const wlValue = document.getElementById('wl-value');
        
        if (wwSlider && wlSlider && wwValue && wlValue) {
            wwSlider.value = this.windowWidth;
            wlSlider.value = this.windowLevel;
            wwValue.textContent = this.windowWidth;
            wlValue.textContent = this.windowLevel;
            
            // Add event listeners
            wwSlider.addEventListener('input', (e) => {
                this.windowWidth = parseInt(e.target.value);
                wwValue.textContent = this.windowWidth;
                this.updateDisplay();
            });
            
            wlSlider.addEventListener('input', (e) => {
                this.windowLevel = parseInt(e.target.value);
                wlValue.textContent = this.windowLevel;
                this.updateDisplay();
            });
        }
    }
    
    updateDisplay() {
        if (!this.currentImage) return;
        
        // Save the current context state
        this.ctx.save();
        
        // Clear canvas with black background (accounting for device pixel ratio)
        const dpr = this.devicePixelRatio || 1;
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, this.canvas.width / dpr, this.canvas.height / dpr);
        
        // Calculate display parameters
        const img = this.currentImage.image;
        const scale = this.getScale();
        
        const displayWidth = img.width * scale;
        const displayHeight = img.height * scale;
        const canvasDisplayWidth = this.canvas.style.width ? parseInt(this.canvas.style.width) : this.canvas.width / dpr;
        const canvasDisplayHeight = this.canvas.style.height ? parseInt(this.canvas.style.height) : this.canvas.height / dpr;
        const x = (canvasDisplayWidth - displayWidth) / 2 + this.panX;
        const y = (canvasDisplayHeight - displayHeight) / 2 + this.panY;
        
        // Enable high-quality image rendering
        this.ctx.imageSmoothingEnabled = true;
        this.ctx.imageSmoothingQuality = 'high';
        
        // Draw image with high quality
        this.ctx.drawImage(img, x, y, displayWidth, displayHeight);
        
        // Draw measurements after the image
        this.drawMeasurements();
        
        // Draw annotations
        this.drawAnnotations();
        
        // Draw crosshair if enabled
        if (this.crosshair) {
            this.drawCrosshair();
        }
        
        // Update overlay labels
        this.updateOverlayLabels();
        
        // Restore the context state
        this.ctx.restore();
    }
    
    getScale() {
        if (!this.currentImage) return 1;
        const img = this.currentImage.image;
        const dpr = this.devicePixelRatio || 1;
        const displayWidth = this.canvas.style.width ? parseInt(this.canvas.style.width) : this.canvas.width / dpr;
        const displayHeight = this.canvas.style.height ? parseInt(this.canvas.style.height) : this.canvas.height / dpr;
        const baseScale = Math.min(displayWidth / img.width, displayHeight / img.height);
        const clampedBase = baseScale > 1 ? 1 : baseScale;
        return this.zoomFactor * clampedBase;
    }
    
    drawMeasurements() {
        if (!this.currentImage) return;
        
        this.ctx.save();
        this.ctx.strokeStyle = 'red';
        this.ctx.lineWidth = 2;
        this.ctx.fillStyle = 'red';
        this.ctx.font = '14px Arial';
        
        this.measurements.forEach(measurement => {
            // Draw measurement lines and annotations
            if (measurement.coordinates && measurement.coordinates.length >= 2) {
                const start = this.imageToCanvasCoords(measurement.coordinates[0].x, measurement.coordinates[0].y);
                const end = this.imageToCanvasCoords(measurement.coordinates[1].x, measurement.coordinates[1].y);
                
                this.ctx.beginPath();
                this.ctx.moveTo(start.x, start.y);
                this.ctx.lineTo(end.x, end.y);
                this.ctx.stroke();
                
                // Draw measurement value
                const midX = (start.x + end.x) / 2;
                const midY = (start.y + end.y) / 2;
                this.ctx.fillText(`${measurement.value.toFixed(1)} ${measurement.unit}`, midX, midY - 10);
            }
        });
        
        this.ctx.restore();
    }
    
    drawAnnotations() {
        if (!this.currentImage) return;
        
        this.ctx.save();
        this.ctx.font = '14px Arial';
        this.ctx.textAlign = 'left';
        this.ctx.textBaseline = 'top';
        
        this.annotations.forEach(annotation => {
            const canvasPos = this.imageToCanvasCoords(annotation.x_coordinate, annotation.y_coordinate);
            this.ctx.fillStyle = annotation.color;
            this.ctx.font = `${annotation.font_size}px Arial`;
            this.ctx.fillText(annotation.text, canvasPos.x, canvasPos.y);
        });
        
        this.ctx.restore();
    }
    
    drawCrosshair() {
        if (!this.currentImage) return;
        
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        
        this.ctx.save();
        this.ctx.strokeStyle = 'yellow';
        this.ctx.lineWidth = 1;
        this.ctx.setLineDash([5, 5]);
        
        this.ctx.beginPath();
        this.ctx.moveTo(centerX, 0);
        this.ctx.lineTo(centerX, this.canvas.height);
        this.ctx.moveTo(0, centerY);
        this.ctx.lineTo(this.canvas.width, centerY);
        this.ctx.stroke();
        
        this.ctx.restore();
    }
    
    updateOverlayLabels() {
        const wlInfo = document.getElementById('wl-info');
        const zoomInfo = document.getElementById('zoom-info');
        
        if (wlInfo) {
            wlInfo.innerHTML = `WW: ${this.windowWidth}<br>WL: ${this.windowLevel}<br>Slice: ${this.currentImageIndex + 1}/${this.currentImages.length}`;
        }
        
        if (zoomInfo) {
            zoomInfo.innerHTML = `Zoom: ${Math.round(this.zoomFactor * 100)}%`;
        }
    }
    
    handleToolClick(tool, btn = null) {
        this.activeTool = tool;
        
        switch (tool) {
            case 'windowing':
                this.canvas.style.cursor = 'default';
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
            case 'crosshair':
                this.crosshair = !this.crosshair;
                this.updateDisplay();
                break;
            case 'invert':
                this.inverted = !this.inverted;
                this.loadCurrentImage();
                break;
            case 'high-quality':
                this.highQualityMode = !this.highQualityMode;
                btn.classList.toggle('active', this.highQualityMode);
                this.loadCurrentImage();  // Reload with new quality setting
                break;
            case 'reset':
                this.resetView();
                break;
            case 'volume':
                this.volumeTool = !this.volumeTool;
                break;
        }
    }
    
    applyPreset(preset) {
        if (this.windowPresets[preset]) {
            this.windowWidth = this.windowPresets[preset].ww;
            this.windowLevel = this.windowPresets[preset].wl;
            this.updateSliders();
            this.loadCurrentImage();
        }
    }
    
    resetView() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.windowWidth = 400;
        this.windowLevel = 40;
        this.inverted = false;
        this.updateSliders();
        this.updateDisplay();
    }
    
    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.isDragging = true;
        this.dragStart = { x, y };
        
        if (this.activeTool === 'pan') {
            this.canvas.style.cursor = 'grabbing';
        }
    }
    
    onMouseMove(e) {
        if (!this.isDragging) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.activeTool === 'pan') {
            this.panX += x - this.dragStart.x;
            this.panY += y - this.dragStart.y;
            this.dragStart = { x, y };
            this.updateDisplay();
        }
    }
    
    onMouseUp(e) {
        this.isDragging = false;
        this.dragStart = null;
        
        if (this.activeTool === 'pan') {
            this.canvas.style.cursor = 'grab';
        }
    }
    
    onWheel(e) {
        e.preventDefault();
        
        if (this.activeTool === 'zoom') {
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomFactor *= delta;
            this.zoomFactor = Math.max(0.1, Math.min(5, this.zoomFactor));
            this.updateDisplay();
        }
    }
    
    onDoubleClick(e) {
        if (this.activeTool === 'annotate') {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const imagePos = this.canvasToImageCoords(x, y);
            
            const text = prompt('Enter annotation text:');
            if (text) {
                this.addAnnotation(imagePos.x, imagePos.y, text);
            }
        }
    }
    
    imageToCanvasCoords(imageX, imageY) {
        if (!this.currentImage) return { x: imageX, y: imageY };
        
        const scale = this.getScale();
        const displayWidth = this.currentImage.image.width * scale;
        const displayHeight = this.currentImage.image.height * scale;
        const canvasDisplayWidth = this.canvas.style.width ? parseInt(this.canvas.style.width) : this.canvas.width;
        const canvasDisplayHeight = this.canvas.style.height ? parseInt(this.canvas.style.height) : this.canvas.height;
        const x = (canvasDisplayWidth - displayWidth) / 2 + this.panX;
        const y = (canvasDisplayHeight - displayHeight) / 2 + this.panY;
        
        return {
            x: x + imageX * scale,
            y: y + imageY * scale
        };
    }
    
    canvasToImageCoords(canvasX, canvasY) {
        if (!this.currentImage) return { x: canvasX, y: canvasY };
        
        const scale = this.getScale();
        const displayWidth = this.currentImage.image.width * scale;
        const displayHeight = this.currentImage.image.height * scale;
        const canvasDisplayWidth = this.canvas.style.width ? parseInt(this.canvas.style.width) : this.canvas.width;
        const canvasDisplayHeight = this.canvas.style.height ? parseInt(this.canvas.style.height) : this.canvas.height;
        const x = (canvasDisplayWidth - displayWidth) / 2 + this.panX;
        const y = (canvasDisplayHeight - displayHeight) / 2 + this.panY;
        
        return {
            x: (canvasX - x) / scale,
            y: (canvasY - y) / scale
        };
    }
    
    async addMeasurement(measurementData) {
        try {
            const response = await fetch('/viewer/api/measurements/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(measurementData)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.measurements.push(result.measurement);
                this.updateMeasurementsList();
                this.updateDisplay();
            }
        } catch (error) {
            console.error('Error saving measurement:', error);
        }
    }
    
    async addAnnotation(x, y, text) {
        try {
            const response = await fetch('/viewer/api/annotations/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    image_id: this.currentImage.id,
                    x_coordinate: x,
                    y_coordinate: y,
                    text: text
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.annotations.push(result.annotation);
                this.updateDisplay();
            }
        } catch (error) {
            console.error('Error saving annotation:', error);
        }
    }
    
    async loadMeasurements() {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch(`/viewer/api/images/${this.currentImage.id}/measurements/`);
            if (response.ok) {
                const data = await response.json();
                this.measurements = data.measurements || [];
            }
        } catch (error) {
            console.error('Error loading measurements:', error);
        }
    }
    
    async loadAnnotations() {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch(`/viewer/api/images/${this.currentImage.id}/annotations/`);
            if (response.ok) {
                const data = await response.json();
                this.annotations = data.annotations || [];
            }
        } catch (error) {
            console.error('Error loading annotations:', error);
        }
    }
    
    updateMeasurementsList() {
        const measurementsList = document.getElementById('measurements-list');
        if (!measurementsList) return;
        
        measurementsList.innerHTML = '';
        this.measurements.forEach((measurement, index) => {
            const item = document.createElement('div');
            item.className = 'measurement-item';
            item.innerHTML = `
                <span>${measurement.measurement_type}: ${measurement.value.toFixed(1)} ${measurement.unit}</span>
                <button onclick="viewer.deleteMeasurement(${index})">×</button>
            `;
            measurementsList.appendChild(item);
        });
    }
    
    async clearMeasurements() {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch(`/viewer/api/images/${this.currentImage.id}/clear-measurements/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.measurements = [];
                this.updateMeasurementsList();
                this.updateDisplay();
            }
        } catch (error) {
            console.error('Error clearing measurements:', error);
        }
    }
    
    deleteMeasurement(index) {
        if (index >= 0 && index < this.measurements.length) {
            this.measurements.splice(index, 1);
            this.updateMeasurementsList();
            this.updateDisplay();
        }
    }
    
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    getCSRFToken() {
        const token = this.getCookie('csrftoken');
        if (!token) {
            console.warn('CSRF token not found');
            return '';
        }
        return token;
    }
    
    redraw() {
        this.updateDisplay();
    }
    
    setupNotifications() {
        // Check for notifications every 30 seconds
        this.notificationCheckInterval = setInterval(() => {
            this.checkNotifications();
        }, 30000);
    }
    
    async checkNotifications() {
        try {
            const response = await fetch('/worklist/api/notifications/count/');
            if (response.ok) {
                const data = await response.json();
                const countElement = document.getElementById('notification-count');
                if (countElement) {
                    countElement.textContent = data.count;
                }
            }
        } catch (error) {
            console.error('Error checking notifications:', error);
        }
    }
    
    setupMeasurementUnitSelector() {
        const unitSelector = document.getElementById('measurement-unit');
        if (unitSelector) {
            unitSelector.addEventListener('change', (e) => {
                this.measurementUnit = e.target.value;
            });
        }
    }
    
    setup3DControls() {
        // 3D reconstruction controls
        const threeDButtons = document.querySelectorAll('[data-3d-type]');
        threeDButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const type = btn.getAttribute('data-3d-type');
                this.apply3DReconstruction(type);
            });
        });
    }
    
    setupAIPanel() {
        // AI analysis controls
        const aiButtons = document.querySelectorAll('[data-ai-type]');
        aiButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const type = btn.getAttribute('data-ai-type');
                this.performAIAnalysis(type);
            });
        });
    }
    
    async performAIAnalysis(analysisType = 'general') {
        if (!this.currentImage) {
            this.showError('No image loaded for AI analysis');
            return;
        }
        
        try {
            const response = await fetch(`/viewer/api/images/${this.currentImage.id}/ai-analysis/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    analysis_type: analysisType
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.displayAIResults(result);
            } else {
                throw new Error('AI analysis failed');
            }
        } catch (error) {
            console.error('AI analysis error:', error);
            this.showError('AI analysis failed: ' + error.message);
        }
    }
    
    displayAIResults(results) {
        const aiResultsDiv = document.getElementById('ai-results');
        if (aiResultsDiv) {
            aiResultsDiv.innerHTML = `
                <h4>AI Analysis Results</h4>
                <p><strong>Summary:</strong> ${results.summary}</p>
                <p><strong>Confidence:</strong> ${(results.confidence_score * 100).toFixed(1)}%</p>
                <button onclick="viewer.toggleAIHighlights()">Toggle Highlights</button>
                <button onclick="viewer.copyAIResults()">Copy Results</button>
            `;
            aiResultsDiv.style.display = 'block';
        }
        
        this.aiAnalysisResults = results;
    }
    
    toggleAIHighlights() {
        this.showAIHighlights = !this.showAIHighlights;
        this.updateDisplay();
    }
    
    copyAIResults() {
        if (this.aiAnalysisResults) {
            const text = `AI Analysis Results:\nSummary: ${this.aiAnalysisResults.summary}\nConfidence: ${(this.aiAnalysisResults.confidence_score * 100).toFixed(1)}%`;
            navigator.clipboard.writeText(text);
        }
    }
    
    async apply3DReconstruction(type = 'mpr') {
        if (!this.currentSeries) {
            this.showError('No series selected for 3D reconstruction');
            return;
        }
        
        try {
            const response = await fetch(`/viewer/api/series/${this.currentSeries.id}/3d-reconstruction/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    reconstruction_type: type
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.show3DResult(result, type);
            } else {
                throw new Error('3D reconstruction failed');
            }
        } catch (error) {
            console.error('3D reconstruction error:', error);
            this.showError('3D reconstruction failed: ' + error.message);
        }
    }
    
    show3DResult(data, type) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2>3D Reconstruction: ${type.toUpperCase()}</h2>
                <div id="3d-viewer"></div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const closeBtn = modal.querySelector('.close');
        closeBtn.onclick = () => modal.remove();
        
        // Display 3D reconstruction data
        const viewer = modal.querySelector('#3d-viewer');
        if (data.images && data.images.length > 0) {
            viewer.innerHTML = data.images.map(img => `<img src="${img}" style="max-width: 100%; margin: 10px;">`).join('');
        } else {
            viewer.innerHTML = '<p>No 3D reconstruction data available</p>';
        }
    }
}

// Initialize viewer when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing viewer...');
    
    // Wait a bit for the main dicom_viewer.js to load
    setTimeout(() => {
        // Initialize the viewer with the initial study ID
        if (typeof DicomViewer !== 'undefined') {
            // Check if viewer is already initialized
            if (!window.viewer) {
                window.viewer = new DicomViewer(window.initialStudyId);
                console.log('Viewer initialized with study ID:', window.initialStudyId);
            } else {
                console.log('Viewer already initialized, ensuring study is loaded');
                if (window.initialStudyId && !window.viewer.currentStudy) {
                    window.viewer.loadStudy(window.initialStudyId);
                }
            }
        } else {
            console.error('DicomViewer class not found');
        }
        
        // Load clinical info for initial study if present
        if (window.initialStudyId && window.loadClinicalInfo) {
            window.loadClinicalInfo(window.initialStudyId);
        }
    }, 100);
});