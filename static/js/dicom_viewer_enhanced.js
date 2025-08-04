// Enhanced DICOM Viewer JavaScript - Medical Imaging Platform with MPR Support
// Copyright 2024 - Noctis DICOM Viewer Enhanced

class EnhancedDicomViewer {
    constructor(initialStudyId = null) {
        // Initialize notification system
        this.notyf = new Notyf({
            duration: 4000,
            position: { x: 'right', y: 'top' },
            types: [
                {
                    type: 'success',
                    background: '#00ff88',
                    icon: { className: 'fas fa-check', tagName: 'i', color: '#0a0a0a' }
                },
                {
                    type: 'error',
                    background: '#ff3333',
                    icon: { className: 'fas fa-times', tagName: 'i', color: '#ffffff' }
                },
                {
                    type: 'info',
                    background: '#0088ff',
                    icon: { className: 'fas fa-info-circle', tagName: 'i', color: '#ffffff' }
                }
            ]
        });

        // Core canvas elements
        this.canvas = document.getElementById('dicom-canvas-advanced');
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        
        if (!this.canvas || !this.ctx) {
            this.createCanvas();
        }

        // Enable high-quality rendering
        this.setupHighQualityRendering();

        // State management
        this.currentStudy = null;
        this.currentSeries = null;
        this.currentImages = [];
        this.currentImageIndex = 0;
        this.currentImage = null;
        this.imageData = null;
        this.originalImageData = null;

        // Enhanced viewing parameters for medical imaging
        this.windowWidth = 1500;  // Optimized for lung imaging
        this.windowLevel = -600;  // Lung level for optimal contrast
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.rotation = 0;
        this.flipHorizontal = false;
        this.flipVertical = false;
        this.inverted = false;
        this.densityEnhancement = true;  // Enable by default for better tissue differentiation
        this.contrastBoost = 1.2;  // Slight boost for better visualization

        // Advanced windowing presets for different anatomical regions
        this.windowPresets = {
            'lung': { ww: 1500, wl: -600, description: 'Lung - Optimal for air-tissue contrast' },
            'bone': { ww: 2000, wl: 300, description: 'Bone - High contrast for bone structures' },
            'soft_tissue': { ww: 400, wl: 40, description: 'Soft Tissue - Organ differentiation' },
            'brain': { ww: 100, wl: 50, description: 'Brain - Neural tissue detail' },
            'abdomen': { ww: 350, wl: 50, description: 'Abdomen - Organ contrast' },
            'mediastinum': { ww: 400, wl: 20, description: 'Mediastinum - Vascular structures' },
            'liver': { ww: 150, wl: 60, description: 'Liver - Hepatic lesion detection' },
            'cardiac': { ww: 600, wl: 200, description: 'Cardiac - Heart structures' },
            'spine': { ww: 1000, wl: 400, description: 'Spine - Vertebral structures' },
            'angio': { ww: 700, wl: 150, description: 'Angiographic - Vessel enhancement' },
            'ct_angio': { ww: 600, wl: 100, description: 'CT Angiography - Contrast vessels' },
            'pe_protocol': { ww: 700, wl: 100, description: 'PE Protocol - Pulmonary embolism' }
        };

        // MPR and 3D capabilities
        this.mprEnabled = false;
        this.mprViews = {
            axial: { active: true, canvas: null, ctx: null },
            sagittal: { active: false, canvas: null, ctx: null },
            coronal: { active: false, canvas: null, ctx: null }
        };
        this.volumeData = null;
        this.currentSlicePosition = { x: 0, y: 0, z: 0 };

        // Tool management
        this.activeTool = 'windowing';
        this.isDragging = false;
        this.dragStart = null;
        this.lastMousePos = null;

        // Initialize viewer
        this.init(initialStudyId);
    }

    createCanvas() {
        const canvasContainer = document.getElementById('canvas-container');
        if (canvasContainer) {
            const canvas = document.createElement('canvas');
            canvas.id = 'dicom-canvas-advanced';
            canvas.className = 'dicom-canvas-advanced';
            canvas.style.cssText = 'position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #000;';
            canvasContainer.appendChild(canvas);
            this.canvas = canvas;
            this.ctx = canvas.getContext('2d');
        }
    }

    setupHighQualityRendering() {
        if (!this.ctx) return;
        
        // Enable high-quality image rendering
        this.ctx.imageSmoothingEnabled = false;
        this.ctx.mozImageSmoothingEnabled = false;
        this.ctx.webkitImageSmoothingEnabled = false;
        this.ctx.msImageSmoothingEnabled = false;
        
        // Set up high DPI support
        const devicePixelRatio = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        
        this.canvas.width = rect.width * devicePixelRatio;
        this.canvas.height = rect.height * devicePixelRatio;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        
        this.ctx.scale(devicePixelRatio, devicePixelRatio);
    }

    async init(studyId) {
        try {
            this.setupEventListeners();
            this.setupKeyboardShortcuts();
            this.setupWindowingControls();
            this.setupMPRControls();
            
            if (studyId) {
                await this.loadStudy(studyId);
            }
            
            this.notyf.success('Enhanced DICOM Viewer initialized successfully');
        } catch (error) {
            console.error('Error initializing viewer:', error);
            this.notyf.error('Failed to initialize DICOM viewer');
        }
    }

    setupWindowingControls() {
        // Window width control
        const windowWidthSlider = document.getElementById('window-width-slider');
        const windowWidthInput = document.getElementById('window-width-input');
        
        if (windowWidthSlider) {
            windowWidthSlider.addEventListener('input', (e) => {
                this.windowWidth = parseFloat(e.target.value);
                if (windowWidthInput) windowWidthInput.value = this.windowWidth;
                this.refreshCurrentImage();
            });
        }

        // Window level control
        const windowLevelSlider = document.getElementById('window-level-slider');
        const windowLevelInput = document.getElementById('window-level-input');
        
        if (windowLevelSlider) {
            windowLevelSlider.addEventListener('input', (e) => {
                this.windowLevel = parseFloat(e.target.value);
                if (windowLevelInput) windowLevelInput.value = this.windowLevel;
                this.refreshCurrentImage();
            });
        }

        // Window presets
        this.setupWindowPresets();
    }

    setupWindowPresets() {
        const presetButtons = document.querySelectorAll('.window-preset-btn');
        presetButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const presetName = e.target.getAttribute('data-preset');
                if (this.windowPresets[presetName]) {
                    this.applyWindowPreset(presetName);
                }
            });
        });
    }

    applyWindowPreset(presetName) {
        const preset = this.windowPresets[presetName];
        if (!preset) return;

        this.windowWidth = preset.ww;
        this.windowLevel = preset.wl;

        // Update UI controls
        const windowWidthSlider = document.getElementById('window-width-slider');
        const windowWidthInput = document.getElementById('window-width-input');
        const windowLevelSlider = document.getElementById('window-level-slider');
        const windowLevelInput = document.getElementById('window-level-input');

        if (windowWidthSlider) windowWidthSlider.value = this.windowWidth;
        if (windowWidthInput) windowWidthInput.value = this.windowWidth;
        if (windowLevelSlider) windowLevelSlider.value = this.windowLevel;
        if (windowLevelInput) windowLevelInput.value = this.windowLevel;

        this.refreshCurrentImage();
        this.notyf.info(`Applied ${preset.description}`);
    }

    setupMPRControls() {
        const mprToggle = document.getElementById('mpr-toggle-btn');
        if (mprToggle) {
            mprToggle.addEventListener('click', () => {
                this.toggleMPR();
            });
        }

        // MPR view buttons
        ['axial', 'sagittal', 'coronal'].forEach(view => {
            const btn = document.getElementById(`${view}-view-btn`);
            if (btn) {
                btn.addEventListener('click', () => {
                    this.switchMPRView(view);
                });
            }
        });
    }

    async toggleMPR() {
        this.mprEnabled = !this.mprEnabled;
        
        const mprToggle = document.getElementById('mpr-toggle-btn');
        if (mprToggle) {
            mprToggle.classList.toggle('active', this.mprEnabled);
        }

        if (this.mprEnabled && this.currentSeries) {
            await this.initializeMPR();
            this.notyf.success('MPR mode enabled - Loading volume data...');
        } else {
            this.disableMPR();
            this.notyf.info('MPR mode disabled');
        }
    }

    async initializeMPR() {
        try {
            // Load all images in the series for volume reconstruction
            if (!this.currentSeries || !this.currentImages.length) {
                this.notyf.error('No image series available for MPR');
                return;
            }

            this.notyf.info('Initializing MPR - Loading volume data...');
            
            // For CT/MRI series with multiple slices
            if (this.currentImages.length > 1) {
                await this.loadVolumeData();
                this.setupMPRViews();
                this.renderMPRViews();
            } else {
                this.notyf.warning('MPR requires multiple slices. Single image detected.');
                this.mprEnabled = false;
            }
        } catch (error) {
            console.error('Error initializing MPR:', error);
            this.notyf.error('Failed to initialize MPR mode');
            this.mprEnabled = false;
        }
    }

    async loadVolumeData() {
        // This would load all DICOM slices and construct a 3D volume
        // For now, we'll simulate this functionality
        this.volumeData = {
            width: 512,
            height: 512,
            depth: this.currentImages.length,
            pixelData: new Array(this.currentImages.length),
            spacing: [1, 1, 1], // mm
            orientation: 'axial'
        };

        // Load pixel data for each slice
        for (let i = 0; i < this.currentImages.length; i++) {
            try {
                const imageData = await this.loadImagePixelData(this.currentImages[i]);
                this.volumeData.pixelData[i] = imageData;
            } catch (error) {
                console.warn(`Failed to load slice ${i}:`, error);
            }
        }
    }

    async loadImagePixelData(image) {
        // Load raw pixel data from DICOM image
        // This is a simplified version - real implementation would parse DICOM pixel data
        return new Array(512 * 512).fill(0).map(() => Math.random() * 4096);
    }

    setupMPRViews() {
        const mprContainer = document.getElementById('mpr-views-container');
        if (!mprContainer) return;

        // Create MPR view canvases
        ['axial', 'sagittal', 'coronal'].forEach(view => {
            const canvas = document.createElement('canvas');
            canvas.id = `mpr-${view}-canvas`;
            canvas.className = 'mpr-view-canvas';
            canvas.width = 256;
            canvas.height = 256;
            
            const ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = false;
            
            this.mprViews[view].canvas = canvas;
            this.mprViews[view].ctx = ctx;
            
            // Add to container
            const viewDiv = document.createElement('div');
            viewDiv.className = `mpr-view mpr-${view}`;
            viewDiv.appendChild(canvas);
            
            const label = document.createElement('div');
            label.className = 'mpr-view-label';
            label.textContent = view.toUpperCase();
            viewDiv.appendChild(label);
            
            mprContainer.appendChild(viewDiv);
        });
    }

    renderMPRViews() {
        if (!this.volumeData || !this.mprEnabled) return;

        // Render each MPR view
        Object.keys(this.mprViews).forEach(view => {
            if (this.mprViews[view].active && this.mprViews[view].ctx) {
                this.renderMPRView(view);
            }
        });
    }

    renderMPRView(viewType) {
        const view = this.mprViews[viewType];
        if (!view || !view.ctx || !this.volumeData) return;

        const ctx = view.ctx;
        const canvas = view.canvas;
        
        // Clear canvas
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Extract 2D slice from volume data based on view type
        const sliceData = this.extractSliceData(viewType);
        if (!sliceData) return;

        // Apply windowing to slice data
        const windowedData = this.applyWindowingToSlice(sliceData);
        
        // Create ImageData and render
        const imageData = ctx.createImageData(canvas.width, canvas.height);
        this.fillImageData(imageData, windowedData);
        ctx.putImageData(imageData, 0, 0);

        // Draw crosshairs
        this.drawMPRCrosshairs(ctx, canvas);
    }

    extractSliceData(viewType) {
        if (!this.volumeData) return null;

        const { width, height, depth, pixelData } = this.volumeData;
        const { x, y, z } = this.currentSlicePosition;

        switch (viewType) {
            case 'axial':
                return pixelData[Math.min(z, depth - 1)] || null;
            case 'sagittal':
                // Extract sagittal slice at position x
                const sagittalSlice = new Array(height * depth);
                for (let d = 0; d < depth; d++) {
                    for (let h = 0; h < height; h++) {
                        const voxelIndex = h * width + Math.min(x, width - 1);
                        sagittalSlice[d * height + h] = pixelData[d] ? pixelData[d][voxelIndex] || 0 : 0;
                    }
                }
                return sagittalSlice;
            case 'coronal':
                // Extract coronal slice at position y
                const coronalSlice = new Array(width * depth);
                for (let d = 0; d < depth; d++) {
                    for (let w = 0; w < width; w++) {
                        const voxelIndex = Math.min(y, height - 1) * width + w;
                        coronalSlice[d * width + w] = pixelData[d] ? pixelData[d][voxelIndex] || 0 : 0;
                    }
                }
                return coronalSlice;
            default:
                return null;
        }
    }

    applyWindowingToSlice(sliceData) {
        if (!sliceData) return null;

        return sliceData.map(pixel => {
            const windowMin = this.windowLevel - this.windowWidth / 2;
            const windowMax = this.windowLevel + this.windowWidth / 2;
            
            // Clamp pixel value to window range
            const clampedPixel = Math.max(windowMin, Math.min(windowMax, pixel));
            
            // Scale to 0-255 range
            const scaledPixel = ((clampedPixel - windowMin) / (windowMax - windowMin)) * 255;
            
            return Math.round(scaledPixel);
        });
    }

    fillImageData(imageData, pixelData) {
        if (!pixelData) return;

        const data = imageData.data;
        for (let i = 0; i < pixelData.length && i * 4 < data.length; i++) {
            const gray = pixelData[i] || 0;
            const index = i * 4;
            data[index] = gray;     // R
            data[index + 1] = gray; // G
            data[index + 2] = gray; // B
            data[index + 3] = 255;  // A
        }
    }

    drawMPRCrosshairs(ctx, canvas) {
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 5]);

        // Draw crosshair lines
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;

        ctx.beginPath();
        ctx.moveTo(0, centerY);
        ctx.lineTo(canvas.width, centerY);
        ctx.moveTo(centerX, 0);
        ctx.lineTo(centerX, canvas.height);
        ctx.stroke();

        ctx.setLineDash([]);
    }

    switchMPRView(viewType) {
        // Update active view
        Object.keys(this.mprViews).forEach(view => {
            this.mprViews[view].active = (view === viewType);
        });

        // Update UI
        document.querySelectorAll('.mpr-view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        const activeBtn = document.getElementById(`${viewType}-view-btn`);
        if (activeBtn) activeBtn.classList.add('active');

        // Re-render MPR views
        this.renderMPRViews();
    }

    disableMPR() {
        this.mprEnabled = false;
        const mprContainer = document.getElementById('mpr-views-container');
        if (mprContainer) {
            mprContainer.innerHTML = '';
        }
    }

    async refreshCurrentImage() {
        if (!this.currentImage) return;

        try {
            const response = await fetch(`/viewer/api/process-image/${this.currentImage.id}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    window_width: this.windowWidth,
                    window_level: this.windowLevel,
                    inverted: this.inverted,
                    density_enhancement: this.densityEnhancement,
                    contrast_boost: this.contrastBoost,
                    high_quality: true
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.image_base64) {
                    await this.displayProcessedImage(data.image_base64);
                    
                    // Update MPR views if enabled
                    if (this.mprEnabled) {
                        this.renderMPRViews();
                    }
                }
            }
        } catch (error) {
            console.error('Error refreshing image:', error);
        }
    }

    async displayProcessedImage(base64Data) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                this.clearCanvas();
                
                // Calculate optimal display size maintaining aspect ratio
                const canvasRect = this.canvas.getBoundingClientRect();
                const canvasWidth = canvasRect.width;
                const canvasHeight = canvasRect.height;
                
                const aspectRatio = img.width / img.height;
                let displayWidth = canvasWidth * this.zoomFactor;
                let displayHeight = canvasHeight * this.zoomFactor;
                
                if (displayWidth / displayHeight > aspectRatio) {
                    displayWidth = displayHeight * aspectRatio;
                } else {
                    displayHeight = displayWidth / aspectRatio;
                }
                
                // Center the image with pan offset
                const x = (canvasWidth - displayWidth) / 2 + this.panX;
                const y = (canvasHeight - displayHeight) / 2 + this.panY;
                
                // Apply transformations
                this.ctx.save();
                this.ctx.translate(x + displayWidth / 2, y + displayHeight / 2);
                this.ctx.rotate(this.rotation * Math.PI / 180);
                this.ctx.scale(
                    this.flipHorizontal ? -1 : 1,
                    this.flipVertical ? -1 : 1
                );
                
                // Draw image with high quality
                this.ctx.drawImage(img, -displayWidth / 2, -displayHeight / 2, displayWidth, displayHeight);
                this.ctx.restore();
                
                this.imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
                resolve();
            };
            img.onerror = reject;
            img.src = `data:image/png;base64,${base64Data}`;
        });
    }

    clearCanvas() {
        this.ctx.fillStyle = '#000000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    setupEventListeners() {
        if (!this.canvas) return;

        // Mouse events for interaction
        this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.handleWheel(e));
        
        // Touch events for mobile support
        this.canvas.addEventListener('touchstart', (e) => this.handleTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.handleTouchMove(e));
        this.canvas.addEventListener('touchend', (e) => this.handleTouchEnd(e));
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName.toLowerCase() === 'input') return;
            
            switch (e.key.toLowerCase()) {
                case 'w':
                    this.activeTool = 'windowing';
                    this.updateToolUI();
                    break;
                case 'z':
                    this.activeTool = 'zoom';
                    this.updateToolUI();
                    break;
                case 'p':
                    this.activeTool = 'pan';
                    this.updateToolUI();
                    break;
                case 'm':
                    this.toggleMPR();
                    break;
                case 'r':
                    this.resetView();
                    break;
                case 'i':
                    this.toggleInversion();
                    break;
                case 'arrowup':
                case 'arrowdown':
                    e.preventDefault();
                    this.navigateImages(e.key === 'arrowup' ? -1 : 1);
                    break;
            }
        });
    }

    updateToolUI() {
        document.querySelectorAll('.tool-btn-advanced').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const activeBtn = document.getElementById(`${this.activeTool}-adv-btn`);
        if (activeBtn) activeBtn.classList.add('active');
    }

    handleMouseDown(e) {
        this.isDragging = true;
        this.dragStart = { x: e.clientX, y: e.clientY };
        this.lastMousePos = { x: e.clientX, y: e.clientY };
    }

    handleMouseMove(e) {
        if (!this.isDragging) return;

        const deltaX = e.clientX - this.lastMousePos.x;
        const deltaY = e.clientY - this.lastMousePos.y;

        switch (this.activeTool) {
            case 'windowing':
                this.windowWidth = Math.max(1, this.windowWidth + deltaX * 4);
                this.windowLevel = this.windowLevel + deltaY * 2;
                this.updateWindowingUI();
                this.refreshCurrentImage();
                break;
            case 'pan':
                this.panX += deltaX;
                this.panY += deltaY;
                this.refreshCurrentImage();
                break;
            case 'zoom':
                this.zoomFactor = Math.max(0.1, this.zoomFactor + deltaY * 0.01);
                this.refreshCurrentImage();
                break;
        }

        this.lastMousePos = { x: e.clientX, y: e.clientY };
    }

    handleMouseUp(e) {
        this.isDragging = false;
        this.dragStart = null;
        this.lastMousePos = null;
    }

    handleWheel(e) {
        e.preventDefault();
        
        if (e.ctrlKey) {
            // Zoom with Ctrl+wheel
            const zoomDelta = e.deltaY > 0 ? -0.1 : 0.1;
            this.zoomFactor = Math.max(0.1, Math.min(5.0, this.zoomFactor + zoomDelta));
            this.refreshCurrentImage();
        } else {
            // Navigate images with wheel
            const direction = e.deltaY > 0 ? 1 : -1;
            this.navigateImages(direction);
        }
    }

    updateWindowingUI() {
        const windowWidthInput = document.getElementById('window-width-input');
        const windowLevelInput = document.getElementById('window-level-input');
        const windowWidthSlider = document.getElementById('window-width-slider');
        const windowLevelSlider = document.getElementById('window-level-slider');

        if (windowWidthInput) windowWidthInput.value = Math.round(this.windowWidth);
        if (windowLevelInput) windowLevelInput.value = Math.round(this.windowLevel);
        if (windowWidthSlider) windowWidthSlider.value = this.windowWidth;
        if (windowLevelSlider) windowLevelSlider.value = this.windowLevel;
    }

    async navigateImages(direction) {
        if (!this.currentImages || this.currentImages.length <= 1) return;

        const newIndex = this.currentImageIndex + direction;
        if (newIndex >= 0 && newIndex < this.currentImages.length) {
            this.currentImageIndex = newIndex;
            this.currentImage = this.currentImages[this.currentImageIndex];
            await this.loadImage(this.currentImage.id);
            this.updateImageCounter();
        }
    }

    updateImageCounter() {
        const counter = document.getElementById('image-counter');
        if (counter && this.currentImages) {
            counter.textContent = `${this.currentImageIndex + 1} / ${this.currentImages.length}`;
        }
    }

    resetView() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.rotation = 0;
        this.flipHorizontal = false;
        this.flipVertical = false;
        this.refreshCurrentImage();
        this.notyf.info('View reset to defaults');
    }

    toggleInversion() {
        this.inverted = !this.inverted;
        const invertBtn = document.getElementById('invert-btn');
        if (invertBtn) invertBtn.classList.toggle('active', this.inverted);
        this.refreshCurrentImage();
    }

    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }

    // Touch event handlers for mobile support
    handleTouchStart(e) {
        e.preventDefault();
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            this.handleMouseDown({ clientX: touch.clientX, clientY: touch.clientY });
        }
    }

    handleTouchMove(e) {
        e.preventDefault();
        if (e.touches.length === 1 && this.isDragging) {
            const touch = e.touches[0];
            this.handleMouseMove({ clientX: touch.clientX, clientY: touch.clientY });
        }
    }

    handleTouchEnd(e) {
        e.preventDefault();
        this.handleMouseUp(e);
    }

    // Placeholder methods for loading studies and images
    async loadStudy(studyId) {
        // Implementation for loading study data
        console.log('Loading study:', studyId);
    }

    async loadImage(imageId) {
        // Implementation for loading individual images
        console.log('Loading image:', imageId);
    }
}

// Initialize the enhanced viewer when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const studyId = urlParams.get('study_id');
    
    window.enhancedDicomViewer = new EnhancedDicomViewer(studyId);
});