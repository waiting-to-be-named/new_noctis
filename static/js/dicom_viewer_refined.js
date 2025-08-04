/**
 * Refined DICOM Viewer JavaScript - Professional Medical Imaging Platform
 * Copyright 2024 - Noctis DICOM Viewer Pro v3.1
 * 
 * This refined version includes:
 * - Enhanced error handling and validation
 * - Improved performance with image caching
 * - Better memory management
 * - Advanced measurement and annotation tools
 * - Professional UI/UX improvements
 * - Comprehensive API integration
 */

class RefinedDicomViewer {
    constructor() {
        // Initialize notification system
        this.initializeNotifications();
        
        // Core elements with robust error checking
        this.initializeCanvas();
        
        // State management
        this.initializeState();
        
        // Performance monitoring
        this.performanceMetrics = {
            renderTime: 0,
            memoryUsage: 0,
            cacheHits: 0,
            cacheMisses: 0
        };
        
        // Image cache for performance
        this.imageCache = new Map();
        this.maxCacheSize = 50; // Maximum cached images
        
        // Initialize the viewer
        this.init();
    }
    
    initializeNotifications() {
        // Simple notification system if Notyf is not available
        this.notify = (message, type = 'info') => {
            console.log(`[${type.toUpperCase()}] ${message}`);
            
            // Create simple notification if Notyf not available
            if (typeof Notyf === 'undefined') {
                this.showSimpleNotification(message, type);
            } else {
                this.notyf[type](message);
            }
        };
    }
    
    showSimpleNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed; top: 20px; right: 20px; 
            padding: 10px 20px; border-radius: 4px; 
            color: white; z-index: 10000; font-weight: bold;
            background: ${type === 'error' ? '#ff3333' : type === 'success' ? '#00ff88' : '#0088ff'};
        `;
        
        document.body.appendChild(notification);
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 4000);
    }
    
    initializeCanvas() {
        this.canvas = document.getElementById('dicom-canvas');
        if (!this.canvas) {
            console.error('Canvas element with ID "dicom-canvas" not found!');
            this.notify('Canvas element not found! Viewer initialization failed.', 'error');
            return false;
        }
        
        this.ctx = this.canvas.getContext('2d');
        if (!this.ctx) {
            this.notify('Failed to get 2D context from canvas!', 'error');
            return false;
        }
        
        // Enable high-quality image rendering
        this.ctx.imageSmoothingEnabled = false;
        this.ctx.mozImageSmoothingEnabled = false;
        this.ctx.webkitImageSmoothingEnabled = false;
        this.ctx.msImageSmoothingEnabled = false;
        
        return true;
    }
    
    initializeState() {
        // Study and image state
        this.currentStudy = null;
        this.currentImages = [];
        this.currentImageIndex = 0;
        this.currentImage = null;
        this.currentImageMetadata = null;
        
        // Display parameters
        this.windowWidth = 400;
        this.windowLevel = 40;
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.inverted = false;
        this.crosshair = false;
        this.magnify = false;
        
        // Tools and interactions
        this.activeTool = 'windowing';
        this.measurements = [];
        this.annotations = [];
        this.currentMeasurement = null;
        this.isDragging = false;
        this.dragStart = null;
        this.lastMousePos = null;
        
        // Window presets for different body parts
        this.windowPresets = {
            'lung': { ww: 1500, wl: -600 },
            'bone': { ww: 2000, wl: 300 },
            'soft': { ww: 400, wl: 40 },
            'brain': { ww: 100, wl: 50 },
            'abdomen': { ww: 350, wl: 50 },
            'chest': { ww: 1500, wl: -600 },
            'spine': { ww: 2000, wl: 300 }
        };
        
        // Performance settings
        this.enableCaching = true;
        this.enablePerformanceMonitoring = true;
    }
    
    init() {
        if (!this.initializeCanvas()) {
            return;
        }
        
        this.setupCanvas();
        this.setupEventListeners();
        this.loadBackendStudies();
        
        if (this.enablePerformanceMonitoring) {
            this.startPerformanceMonitoring();
        }
        
        this.notify('DICOM Viewer initialized successfully', 'success');
    }
    
    setupCanvas() {
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    resizeCanvas() {
        const viewport = document.querySelector('.viewport') || document.getElementById('viewport');
        if (viewport && this.canvas) {
            this.canvas.width = viewport.clientWidth;
            this.canvas.height = viewport.clientHeight;
            this.redraw();
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
        
        // Control sliders
        this.setupSliderEvents();
        
        // Preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const preset = btn.dataset.preset;
                this.applyPreset(preset);
            });
        });
        
        // Upload and utility buttons
        this.setupUtilityButtons();
        
        // Canvas interactions
        this.setupCanvasEvents();
        
        // Upload modal
        this.setupUploadModal();
        
        // Keyboard shortcuts
        this.setupKeyboardShortcuts();
    }
    
    setupSliderEvents() {
        const sliders = {
            'ww-slider': (value) => {
                this.windowWidth = parseInt(value);
                document.getElementById('ww-value').textContent = this.windowWidth;
                this.updateDisplay();
            },
            'wl-slider': (value) => {
                this.windowLevel = parseInt(value);
                document.getElementById('wl-value').textContent = this.windowLevel;
                this.updateDisplay();
            },
            'slice-slider': (value) => {
                this.currentImageIndex = parseInt(value);
                document.getElementById('slice-value').textContent = this.currentImageIndex + 1;
                this.loadCurrentImage();
            },
            'zoom-slider': (value) => {
                this.zoomFactor = value / 100;
                document.getElementById('zoom-value').textContent = value + '%';
                this.updateDisplay();
            }
        };
        
        Object.entries(sliders).forEach(([id, handler]) => {
            const slider = document.getElementById(id);
            if (slider) {
                slider.addEventListener('input', (e) => handler(e.target.value));
            }
        });
    }
    
    setupUtilityButtons() {
        const buttons = {
            'load-dicom-btn': () => this.showUploadModal(),
            'clear-measurements': () => this.clearMeasurements(),
            'reset-view': () => this.resetView(),
            'fit-to-window': () => this.fitToWindow(),
            'actual-size': () => this.actualSize(),
            'invert-image': () => this.toggleInvert(),
            'crosshair-toggle': () => this.toggleCrosshair()
        };
        
        Object.entries(buttons).forEach(([id, handler]) => {
            const button = document.getElementById(id);
            if (button) {
                button.addEventListener('click', handler);
            }
        });
    }
    
    setupCanvasEvents() {
        if (!this.canvas) return;
        
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        this.canvas.addEventListener('dblclick', (e) => this.onDoubleClick(e));
        
        // Touch events for mobile
        this.canvas.addEventListener('touchstart', (e) => this.onTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.onTouchMove(e));
        this.canvas.addEventListener('touchend', (e) => this.onTouchEnd(e));
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            
            switch(e.key) {
                case 'ArrowLeft':
                    e.preventDefault();
                    this.previousImage();
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.nextImage();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.adjustWindowLevel(10);
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this.adjustWindowLevel(-10);
                    break;
                case 'r':
                    e.preventDefault();
                    this.resetView();
                    break;
                case 'f':
                    e.preventDefault();
                    this.fitToWindow();
                    break;
                case 'i':
                    e.preventDefault();
                    this.toggleInvert();
                    break;
                case 'c':
                    e.preventDefault();
                    this.toggleCrosshair();
                    break;
                case 'Escape':
                    e.preventDefault();
                    this.cancelCurrentOperation();
                    break;
            }
        });
    }
    
    setupUploadModal() {
        const modal = document.getElementById('upload-modal');
        if (!modal) return;
        
        const closeBtn = modal.querySelector('.modal-close');
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }
        
        if (uploadArea && fileInput) {
            uploadArea.addEventListener('click', () => {
                fileInput.click();
            });
            
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.uploadFiles(e.target.files);
                }
            });
            
            // Drag and drop
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
                if (e.dataTransfer.files.length > 0) {
                    this.uploadFiles(e.dataTransfer.files);
                }
            });
        }
    }
    
    showUploadModal() {
        const modal = document.getElementById('upload-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }
    
    async uploadFiles(files) {
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });
        
        const progressDiv = document.getElementById('upload-progress');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        if (progressDiv) progressDiv.style.display = 'block';
        if (progressFill) progressFill.style.width = '0%';
        
        try {
            const response = await fetch('/api/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (progressFill) progressFill.style.width = '100%';
            
            if (response.ok) {
                const result = await response.json();
                if (progressText) progressText.textContent = 'Upload complete!';
                
                setTimeout(() => {
                    const modal = document.getElementById('upload-modal');
                    if (modal) modal.style.display = 'none';
                    if (progressDiv) progressDiv.style.display = 'none';
                    
                    if (result.study_id) {
                        this.loadStudy(result.study_id);
                    }
                }, 1000);
                
                this.notify('Files uploaded successfully', 'success');
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            if (progressText) progressText.textContent = 'Upload failed: ' + error.message;
            this.notify('Upload failed: ' + error.message, 'error');
            console.error('Upload error:', error);
        }
    }
    
    async loadBackendStudies() {
        try {
            const response = await fetch('/api/studies/');
            const studies = await response.json();
            
            const select = document.getElementById('backend-studies');
            if (select) {
                select.innerHTML = '<option value="">Select DICOM from System</option>';
                
                studies.forEach(study => {
                    const option = document.createElement('option');
                    option.value = study.id;
                    option.textContent = `${study.patient_name} - ${study.study_date} (${study.modality})`;
                    select.appendChild(option);
                });
                
                select.addEventListener('change', (e) => {
                    if (e.target.value) {
                        this.loadStudy(parseInt(e.target.value));
                    }
                });
            }
            
        } catch (error) {
            this.notify('Error loading studies: ' + error.message, 'error');
            console.error('Error loading studies:', error);
        }
    }
    
    async loadStudy(studyId) {
        try {
            this.showLoading(true);
            
            const response = await fetch(`/api/studies/${studyId}/images/`);
            const data = await response.json();
            
            this.currentStudy = data.study;
            this.currentImages = data.images;
            this.currentImageIndex = 0;
            
            // Update UI
            this.updatePatientInfo();
            this.updateSliders();
            this.loadCurrentImage();
            
            this.notify(`Study loaded: ${this.currentStudy.patient_name}`, 'success');
            
        } catch (error) {
            this.notify('Error loading study: ' + error.message, 'error');
            console.error('Error loading study:', error);
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadCurrentImage() {
        if (!this.currentImages.length) return;
        
        const imageData = this.currentImages[this.currentImageIndex];
        const cacheKey = `${imageData.id}_${this.windowWidth}_${this.windowLevel}_${this.inverted}`;
        
        // Check cache first
        if (this.enableCaching && this.imageCache.has(cacheKey)) {
            const cachedImage = this.imageCache.get(cacheKey);
            this.currentImage = cachedImage;
            this.updateDisplay();
            this.performanceMetrics.cacheHits++;
            return;
        }
        
        try {
            const params = new URLSearchParams({
                window_width: this.windowWidth,
                window_level: this.windowLevel,
                inverted: this.inverted
            });
            
            const response = await fetch(`/api/images/${imageData.id}/data/?${params}`);
            const data = await response.json();
            
            if (data.image_data) {
                const img = new Image();
                img.onload = () => {
                    this.currentImage = {
                        image: img,
                        metadata: data.metadata,
                        id: imageData.id
                    };
                    
                    // Cache the image
                    if (this.enableCaching) {
                        this.cacheImage(cacheKey, this.currentImage);
                        this.performanceMetrics.cacheMisses++;
                    }
                    
                    this.updateDisplay();
                    this.loadMeasurements();
                    this.loadAnnotations();
                };
                img.src = data.image_data;
            }
            
        } catch (error) {
            this.notify('Error loading image: ' + error.message, 'error');
            console.error('Error loading image:', error);
        }
    }
    
    cacheImage(key, image) {
        if (this.imageCache.size >= this.maxCacheSize) {
            // Remove oldest entry
            const firstKey = this.imageCache.keys().next().value;
            this.imageCache.delete(firstKey);
        }
        this.imageCache.set(key, image);
    }
    
    updatePatientInfo() {
        if (!this.currentStudy) return;
        
        const patientInfo = document.getElementById('patient-info');
        if (patientInfo) {
            patientInfo.textContent = `Patient: ${this.currentStudy.patient_name} | Study Date: ${this.currentStudy.study_date} | Modality: ${this.currentStudy.modality}`;
        }
        
        // Update image info
        const currentImageData = this.currentImages[this.currentImageIndex];
        if (currentImageData) {
            const elements = {
                'info-dimensions': `${currentImageData.columns}x${currentImageData.rows}`,
                'info-pixel-spacing': `${currentImageData.pixel_spacing_x || 'Unknown'}\\${currentImageData.pixel_spacing_y || 'Unknown'}`,
                'info-series': currentImageData.series_description || 'Unknown',
                'info-institution': this.currentStudy.institution_name || 'Unknown'
            };
            
            Object.entries(elements).forEach(([id, text]) => {
                const element = document.getElementById(id);
                if (element) element.textContent = text;
            });
        }
    }
    
    updateSliders() {
        if (!this.currentImages.length) return;
        
        const sliceSlider = document.getElementById('slice-slider');
        if (sliceSlider) {
            sliceSlider.max = this.currentImages.length - 1;
            sliceSlider.value = this.currentImageIndex;
        }
        
        // Update initial window/level from first image
        const firstImage = this.currentImages[0];
        if (firstImage.window_width && firstImage.window_center) {
            this.windowWidth = firstImage.window_width;
            this.windowLevel = firstImage.window_center;
            
            const wwSlider = document.getElementById('ww-slider');
            const wlSlider = document.getElementById('wl-slider');
            const wwValue = document.getElementById('ww-value');
            const wlValue = document.getElementById('wl-value');
            
            if (wwSlider) wwSlider.value = this.windowWidth;
            if (wlSlider) wlSlider.value = this.windowLevel;
            if (wwValue) wwValue.textContent = this.windowWidth;
            if (wlValue) wlValue.textContent = this.windowLevel;
        }
    }
    
    updateDisplay() {
        if (!this.currentImage || !this.canvas) return;
        
        const startTime = performance.now();
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Calculate display parameters
        const img = this.currentImage.image;
        const scale = Math.min(
            (this.canvas.width * this.zoomFactor) / img.width,
            (this.canvas.height * this.zoomFactor) / img.height
        );
        
        const displayWidth = img.width * scale;
        const displayHeight = img.height * scale;
        const x = (this.canvas.width - displayWidth) / 2 + this.panX;
        const y = (this.canvas.height - displayHeight) / 2 + this.panY;
        
        // Draw image
        this.ctx.drawImage(img, x, y, displayWidth, displayHeight);
        
        // Draw overlays
        this.drawMeasurements();
        this.drawAnnotations();
        if (this.crosshair) {
            this.drawCrosshair();
        }
        
        // Update overlay labels
        this.updateOverlayLabels();
        
        this.performanceMetrics.renderTime = performance.now() - startTime;
    }
    
    drawMeasurements() {
        if (!this.currentImage) return;
        
        this.ctx.strokeStyle = 'red';
        this.ctx.lineWidth = 2;
        this.ctx.fillStyle = 'red';
        this.ctx.font = '12px Arial';
        
        this.measurements.forEach(measurement => {
            const coords = measurement.coordinates;
            if (coords.length >= 2) {
                const start = this.imageToCanvasCoords(coords[0].x, coords[0].y);
                const end = this.imageToCanvasCoords(coords[1].x, coords[1].y);
                
                this.ctx.beginPath();
                this.ctx.moveTo(start.x, start.y);
                this.ctx.lineTo(end.x, end.y);
                this.ctx.stroke();
                
                // Draw measurement text
                const midX = (start.x + end.x) / 2;
                const midY = (start.y + end.y) / 2;
                const text = `${measurement.value.toFixed(1)} ${measurement.unit}`;
                
                // Background for text
                const textMetrics = this.ctx.measureText(text);
                this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                this.ctx.fillRect(midX - textMetrics.width/2 - 4, midY - 8, textMetrics.width + 8, 16);
                
                this.ctx.fillStyle = 'red';
                this.ctx.fillText(text, midX - textMetrics.width/2, midY + 4);
            }
        });
        
        // Draw current measurement being created
        if (this.currentMeasurement) {
            const start = this.imageToCanvasCoords(this.currentMeasurement.start.x, this.currentMeasurement.start.y);
            const end = this.imageToCanvasCoords(this.currentMeasurement.end.x, this.currentMeasurement.end.y);
            
            this.ctx.setLineDash([5, 5]);
            this.ctx.strokeStyle = 'yellow';
            this.ctx.beginPath();
            this.ctx.moveTo(start.x, start.y);
            this.ctx.lineTo(end.x, end.y);
            this.ctx.stroke();
            this.ctx.setLineDash([]);
        }
    }
    
    drawAnnotations() {
        if (!this.currentImage) return;
        
        this.ctx.fillStyle = 'yellow';
        this.ctx.font = '12px Arial';
        
        this.annotations.forEach(annotation => {
            const pos = this.imageToCanvasCoords(annotation.x, annotation.y);
            
            // Background for text
            const textMetrics = this.ctx.measureText(annotation.text);
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
            this.ctx.fillRect(pos.x - 2, pos.y - 14, textMetrics.width + 4, 16);
            
            this.ctx.fillStyle = 'yellow';
            this.ctx.fillText(annotation.text, pos.x, pos.y);
        });
    }
    
    drawCrosshair() {
        this.ctx.strokeStyle = 'cyan';
        this.ctx.lineWidth = 1;
        this.ctx.setLineDash([]);
        
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        
        this.ctx.beginPath();
        this.ctx.moveTo(0, centerY);
        this.ctx.lineTo(this.canvas.width, centerY);
        this.ctx.moveTo(centerX, 0);
        this.ctx.lineTo(centerX, this.canvas.height);
        this.ctx.stroke();
    }
    
    updateOverlayLabels() {
        const wlInfo = document.getElementById('wl-info');
        const zoomInfo = document.getElementById('zoom-info');
        
        if (wlInfo) {
            wlInfo.innerHTML = `WW: ${Math.round(this.windowWidth)}<br>WL: ${Math.round(this.windowLevel)}<br>Slice: ${this.currentImageIndex + 1}/${this.currentImages.length}`;
        }
        if (zoomInfo) {
            zoomInfo.textContent = `Zoom: ${Math.round(this.zoomFactor * 100)}%`;
        }
    }
    
    // Event Handlers
    handleToolClick(tool) {
        console.log('Tool activated:', tool);
        
        if (tool === 'reset') {
            this.resetView();
        } else if (tool === 'invert') {
            this.toggleInvert();
        } else if (tool === 'crosshair') {
            this.toggleCrosshair();
        } else if (tool === 'ai') {
            this.notify('AI analysis feature is not implemented yet.', 'warning');
        } else if (tool === '3d') {
            this.notify('3D reconstruction feature is not implemented yet.', 'warning');
        } else {
            this.activeTool = tool;
        }
        
        // Update button states
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        if (!['reset', 'invert', 'crosshair', 'ai', '3d'].includes(tool)) {
            const activeBtn = document.querySelector(`[data-tool="${tool}"]`);
            if (activeBtn) activeBtn.classList.add('active');
        }
    }
    
    applyPreset(preset) {
        const presetValues = this.windowPresets[preset];
        if (presetValues) {
            this.windowWidth = presetValues.ww;
            this.windowLevel = presetValues.wl;
            
            const wwSlider = document.getElementById('ww-slider');
            const wlSlider = document.getElementById('wl-slider');
            const wwValue = document.getElementById('ww-value');
            const wlValue = document.getElementById('wl-value');
            
            if (wwSlider) wwSlider.value = this.windowWidth;
            if (wlSlider) wlSlider.value = this.windowLevel;
            if (wwValue) wwValue.textContent = this.windowWidth;
            if (wlValue) wlValue.textContent = this.windowLevel;
            
            this.loadCurrentImage();
            this.notify(`Applied ${preset} preset`, 'success');
        }
    }
    
    resetView() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        
        const zoomSlider = document.getElementById('zoom-slider');
        const zoomValue = document.getElementById('zoom-value');
        
        if (zoomSlider) zoomSlider.value = 100;
        if (zoomValue) zoomValue.textContent = '100%';
        
        this.updateDisplay();
        this.notify('View reset', 'info');
    }
    
    fitToWindow() {
        if (!this.currentImage) return;
        
        const img = this.currentImage.image;
        const scale = Math.min(
            this.canvas.width / img.width,
            this.canvas.height / img.height
        );
        
        this.zoomFactor = scale;
        this.panX = 0;
        this.panY = 0;
        
        const zoomSlider = document.getElementById('zoom-slider');
        const zoomValue = document.getElementById('zoom-value');
        
        if (zoomSlider) zoomSlider.value = Math.round(scale * 100);
        if (zoomValue) zoomValue.textContent = Math.round(scale * 100) + '%';
        
        this.updateDisplay();
        this.notify('Fitted to window', 'info');
    }
    
    actualSize() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        
        const zoomSlider = document.getElementById('zoom-slider');
        const zoomValue = document.getElementById('zoom-value');
        
        if (zoomSlider) zoomSlider.value = 100;
        if (zoomValue) zoomValue.textContent = '100%';
        
        this.updateDisplay();
        this.notify('Actual size', 'info');
    }
    
    toggleInvert() {
        this.inverted = !this.inverted;
        this.loadCurrentImage();
        this.notify(`Image ${this.inverted ? 'inverted' : 'normal'}`, 'info');
    }
    
    toggleCrosshair() {
        this.crosshair = !this.crosshair;
        this.updateDisplay();
        this.notify(`Crosshair ${this.crosshair ? 'enabled' : 'disabled'}`, 'info');
    }
    
    adjustWindowLevel(delta) {
        this.windowLevel = Math.max(-1000, Math.min(1000, this.windowLevel + delta));
        
        const wlSlider = document.getElementById('wl-slider');
        const wlValue = document.getElementById('wl-value');
        
        if (wlSlider) wlSlider.value = Math.round(this.windowLevel);
        if (wlValue) wlValue.textContent = Math.round(this.windowLevel);
        
        this.loadCurrentImage();
    }
    
    previousImage() {
        if (this.currentImageIndex > 0) {
            this.currentImageIndex--;
            const sliceSlider = document.getElementById('slice-slider');
            const sliceValue = document.getElementById('slice-value');
            
            if (sliceSlider) sliceSlider.value = this.currentImageIndex;
            if (sliceValue) sliceValue.textContent = this.currentImageIndex + 1;
            
            this.loadCurrentImage();
        }
    }
    
    nextImage() {
        if (this.currentImageIndex < this.currentImages.length - 1) {
            this.currentImageIndex++;
            const sliceSlider = document.getElementById('slice-slider');
            const sliceValue = document.getElementById('slice-value');
            
            if (sliceSlider) sliceSlider.value = this.currentImageIndex;
            if (sliceValue) sliceValue.textContent = this.currentImageIndex + 1;
            
            this.loadCurrentImage();
        }
    }
    
    cancelCurrentOperation() {
        this.currentMeasurement = null;
        this.isDragging = false;
        this.dragStart = null;
        this.updateDisplay();
    }
    
    // Mouse Events
    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.isDragging = true;
        this.dragStart = { x, y };
        this.lastMousePos = { x, y };
        
        if (this.activeTool === 'measure') {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.currentMeasurement = {
                start: imageCoords,
                end: imageCoords
            };
        } else if (this.activeTool === 'annotate') {
            const text = prompt('Enter annotation text:');
            if (text) {
                const imageCoords = this.canvasToImageCoords(x, y);
                this.addAnnotation(imageCoords.x, imageCoords.y, text);
            }
        }
    }
    
    onMouseMove(e) {
        if (!this.isDragging || !this.dragStart) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const dx = x - this.dragStart.x;
        const dy = y - this.dragStart.y;
        
        if (this.activeTool === 'pan') {
            this.panX += dx;
            this.panY += dy;
            this.dragStart = { x, y };
            this.updateDisplay();
        } else if (this.activeTool === 'zoom') {
            const zoomDelta = 1 + dy * 0.01;
            this.zoomFactor = Math.max(0.1, Math.min(5.0, this.zoomFactor * zoomDelta));
            
            const zoomPercent = Math.round(this.zoomFactor * 100);
            const zoomSlider = document.getElementById('zoom-slider');
            const zoomValue = document.getElementById('zoom-value');
            
            if (zoomSlider) zoomSlider.value = zoomPercent;
            if (zoomValue) zoomValue.textContent = zoomPercent + '%';
            
            this.dragStart = { x, y };
            this.updateDisplay();
        } else if (this.activeTool === 'windowing') {
            this.windowWidth = Math.max(1, this.windowWidth + dx * 2);
            this.windowLevel = Math.max(-1000, Math.min(1000, this.windowLevel + dy * 2));
            
            const wwSlider = document.getElementById('ww-slider');
            const wlSlider = document.getElementById('wl-slider');
            const wwValue = document.getElementById('ww-value');
            const wlValue = document.getElementById('wl-value');
            
            if (wwSlider) wwSlider.value = Math.round(this.windowWidth);
            if (wlSlider) wlSlider.value = Math.round(this.windowLevel);
            if (wwValue) wwValue.textContent = Math.round(this.windowWidth);
            if (wlValue) wlValue.textContent = Math.round(this.windowLevel);
            
            this.dragStart = { x, y };
            this.loadCurrentImage();
        } else if (this.activeTool === 'measure' && this.currentMeasurement) {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.currentMeasurement.end = imageCoords;
            this.updateDisplay();
        }
        
        this.lastMousePos = { x, y };
    }
    
    onMouseUp(e) {
        if (this.activeTool === 'measure' && this.currentMeasurement) {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const imageCoords = this.canvasToImageCoords(x, y);
            
            this.currentMeasurement.end = imageCoords;
            this.addMeasurement(this.currentMeasurement);
            this.currentMeasurement = null;
        }
        
        this.isDragging = false;
        this.dragStart = null;
    }
    
    onWheel(e) {
        e.preventDefault();
        
        if (e.ctrlKey) {
            // Zoom
            const zoomDelta = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomFactor = Math.max(0.1, Math.min(5.0, this.zoomFactor * zoomDelta));
            
            const zoomPercent = Math.round(this.zoomFactor * 100);
            const zoomSlider = document.getElementById('zoom-slider');
            const zoomValue = document.getElementById('zoom-value');
            
            if (zoomSlider) zoomSlider.value = zoomPercent;
            if (zoomValue) zoomValue.textContent = zoomPercent + '%';
            
            this.updateDisplay();
        } else {
            // Slice navigation
            const direction = e.deltaY > 0 ? 1 : -1;
            const newIndex = this.currentImageIndex + direction;
            
            if (newIndex >= 0 && newIndex < this.currentImages.length) {
                this.currentImageIndex = newIndex;
                const sliceSlider = document.getElementById('slice-slider');
                const sliceValue = document.getElementById('slice-value');
                
                if (sliceSlider) sliceSlider.value = newIndex;
                if (sliceValue) sliceValue.textContent = newIndex + 1;
                
                this.loadCurrentImage();
            }
        }
    }
    
    onDoubleClick(e) {
        if (this.activeTool === 'windowing') {
            this.fitToWindow();
        }
    }
    
    // Touch Events
    onTouchStart(e) {
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            const rect = this.canvas.getBoundingClientRect();
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;
            
            this.isDragging = true;
            this.dragStart = { x, y };
        }
    }
    
    onTouchMove(e) {
        if (!this.isDragging || !this.dragStart || e.touches.length !== 1) return;
        
        const touch = e.touches[0];
        const rect = this.canvas.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;
        
        const dx = x - this.dragStart.x;
        const dy = y - this.dragStart.y;
        
        if (this.activeTool === 'pan') {
            this.panX += dx;
            this.panY += dy;
            this.dragStart = { x, y };
            this.updateDisplay();
        }
    }
    
    onTouchEnd(e) {
        this.isDragging = false;
        this.dragStart = null;
    }
    
    // Coordinate conversion
    imageToCanvasCoords(imageX, imageY) {
        if (!this.currentImage) return { x: 0, y: 0 };
        
        const img = this.currentImage.image;
        const scale = Math.min(
            (this.canvas.width * this.zoomFactor) / img.width,
            (this.canvas.height * this.zoomFactor) / img.height
        );
        
        const displayWidth = img.width * scale;
        const displayHeight = img.height * scale;
        const offsetX = (this.canvas.width - displayWidth) / 2 + this.panX;
        const offsetY = (this.canvas.height - displayHeight) / 2 + this.panY;
        
        return {
            x: offsetX + (imageX * scale),
            y: offsetY + (imageY * scale)
        };
    }
    
    canvasToImageCoords(canvasX, canvasY) {
        if (!this.currentImage) return { x: 0, y: 0 };
        
        const img = this.currentImage.image;
        const scale = Math.min(
            (this.canvas.width * this.zoomFactor) / img.width,
            (this.canvas.height * this.zoomFactor) / img.height
        );
        
        const displayWidth = img.width * scale;
        const displayHeight = img.height * scale;
        const offsetX = (this.canvas.width - displayWidth) / 2 + this.panX;
        const offsetY = (this.canvas.height - displayHeight) / 2 + this.panY;
        
        return {
            x: (canvasX - offsetX) / scale,
            y: (canvasY - offsetY) / scale
        };
    }
    
    // Measurements and Annotations
    async addMeasurement(measurementData) {
        const distance = Math.sqrt(
            Math.pow(measurementData.end.x - measurementData.start.x, 2) +
            Math.pow(measurementData.end.y - measurementData.start.y, 2)
        );
        
        let unit = 'px';
        let value = distance;
        
        // Convert to mm if pixel spacing is available
        const metadata = this.currentImage.metadata;
        if (metadata.pixel_spacing_x && metadata.pixel_spacing_y) {
            const avgSpacing = (metadata.pixel_spacing_x + metadata.pixel_spacing_y) / 2;
            value = distance * avgSpacing;
            unit = 'mm';
        }
        
        const measurement = {
            image_id: this.currentImage.id,
            type: 'line',
            coordinates: [measurementData.start, measurementData.end],
            value: value,
            unit: unit
        };
        
        try {
            const response = await fetch('/api/measurements/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(measurement)
            });
            
            if (response.ok) {
                this.measurements.push(measurement);
                this.updateMeasurementsList();
                this.updateDisplay();
                this.notify('Measurement added', 'success');
            }
        } catch (error) {
            this.notify('Error saving measurement: ' + error.message, 'error');
            console.error('Error saving measurement:', error);
        }
    }
    
    async addAnnotation(x, y, text) {
        const annotation = {
            image_id: this.currentImage.id,
            x: x,
            y: y,
            text: text
        };
        
        try {
            const response = await fetch('/api/annotations/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(annotation)
            });
            
            if (response.ok) {
                this.annotations.push(annotation);
                this.updateDisplay();
                this.notify('Annotation added', 'success');
            }
        } catch (error) {
            this.notify('Error saving annotation: ' + error.message, 'error');
            console.error('Error saving annotation:', error);
        }
    }
    
    async loadMeasurements() {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch(`/api/images/${this.currentImage.id}/measurements/`);
            this.measurements = await response.json();
            this.updateMeasurementsList();
        } catch (error) {
            console.error('Error loading measurements:', error);
        }
    }
    
    async loadAnnotations() {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch(`/api/images/${this.currentImage.id}/annotations/`);
            this.annotations = await response.json();
        } catch (error) {
            console.error('Error loading annotations:', error);
        }
    }
    
    updateMeasurementsList() {
        const list = document.getElementById('measurements-list');
        if (!list) return;
        
        list.innerHTML = '';
        
        this.measurements.forEach((measurement, index) => {
            const item = document.createElement('div');
            item.className = 'measurement-item';
            item.textContent = `Measurement ${index + 1}: ${measurement.value.toFixed(1)} ${measurement.unit}`;
            list.appendChild(item);
        });
    }
    
    async clearMeasurements() {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch(`/api/images/${this.currentImage.id}/clear-measurements/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.measurements = [];
                this.annotations = [];
                this.updateMeasurementsList();
                this.updateDisplay();
                this.notify('Measurements cleared', 'success');
            }
        } catch (error) {
            this.notify('Error clearing measurements: ' + error.message, 'error');
            console.error('Error clearing measurements:', error);
        }
    }
    
    // Performance monitoring
    startPerformanceMonitoring() {
        setInterval(() => {
            this.updatePerformanceDisplay();
        }, 1000);
    }
    
    updatePerformanceDisplay() {
        const performanceDiv = document.getElementById('performance-info');
        if (performanceDiv) {
            performanceDiv.innerHTML = `
                Render: ${this.performanceMetrics.renderTime.toFixed(1)}ms<br>
                Cache: ${this.performanceMetrics.cacheHits}/${this.performanceMetrics.cacheMisses}<br>
                Memory: ${this.imageCache.size} images
            `;
        }
    }
    
    // Utility functions
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    showLoading(show) {
        const loadingDiv = document.getElementById('loading-overlay');
        if (loadingDiv) {
            loadingDiv.style.display = show ? 'flex' : 'none';
        }
    }
    
    redraw() {
        if (this.currentImage) {
            this.updateDisplay();
        }
    }
    
    // Cleanup
    cleanup() {
        this.imageCache.clear();
        this.measurements = [];
        this.annotations = [];
        this.currentImage = null;
        this.currentStudy = null;
        this.currentImages = [];
    }
}

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dicomViewer = new RefinedDicomViewer();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RefinedDicomViewer;
}