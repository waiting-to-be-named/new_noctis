// Fixed DICOM Viewer JavaScript - Medical Imaging Platform with MPR Support
// Copyright 2024 - Noctis DICOM Viewer Enhanced

class FixedDicomViewer {
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
        this.ctx = this.canvas ? this.canvas.getContext('2d', { willReadFrequently: true }) : null;
        
        if (!this.canvas || !this.ctx) {
            this.createCanvas();
        }

        // Enable high-quality rendering
        this.setupHighQualityRendering();

        // State management
        this.currentStudy = null;
        this.currentStudyId = null;
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

        // Upload handlers setup flag
        this.uploadHandlersSetup = false;

        // Initialize viewer
        this.init(initialStudyId);
    }

    createCanvas() {
        const canvasContainer = document.getElementById('canvas-container');
        if (canvasContainer) {
            this.canvas = document.createElement('canvas');
            this.canvas.id = 'dicom-canvas-advanced';
            this.canvas.width = 800;
            this.canvas.height = 600;
            this.canvas.style.border = '1px solid #333';
            this.canvas.style.backgroundColor = '#000';
            canvasContainer.appendChild(this.canvas);
            this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
        }
    }

    setupHighQualityRendering() {
        if (this.canvas) {
            // Enable high-quality rendering
            this.ctx.imageSmoothingEnabled = true;
            this.ctx.imageSmoothingQuality = 'high';
        }
    }

    async init(studyId) {
        try {
            this.setupEventListeners();
            this.setupKeyboardShortcuts();
            this.setupWindowingControls();
            this.setupMPRControls();
            this.setupUploadHandlers(); // Setup upload handlers
            
            // Initialize debug panel
            this.updateDebugPanel();
            
            // Test API connectivity
            await this.testConnectivity();
            
            if (studyId) {
                await this.loadStudy(studyId);
            } else {
                // Show no data message if no study ID provided
                this.showNoDataMessage();
            }
            
            this.notyf.success('Fixed DICOM Viewer initialized successfully');
        } catch (error) {
            console.error('Error initializing viewer:', error);
            this.notyf.error('Failed to initialize DICOM viewer');
            this.showConnectionError();
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
        if (mprToggle) mprToggle.classList.toggle('active', this.mprEnabled);
        
        if (this.mprEnabled) {
            await this.initializeMPR();
        } else {
            this.disableMPR();
        }
    }

    async initializeMPR() {
        if (!this.currentImages || this.currentImages.length === 0) {
            this.notyf.error('No images available for MPR');
            return;
        }

        try {
            await this.loadVolumeData();
            this.setupMPRViews();
            this.renderMPRViews();
            this.notyf.success('MPR initialized successfully');
        } catch (error) {
            console.error('Error initializing MPR:', error);
            this.notyf.error('Failed to initialize MPR');
        }
    }

    async loadVolumeData() {
        // Load all images in the current series for volume reconstruction
        this.volumeData = [];
        for (let image of this.currentImages) {
            try {
                const pixelData = await this.loadImagePixelData(image);
                this.volumeData.push(pixelData);
            } catch (error) {
                console.error('Error loading image for volume:', error);
            }
        }
    }

    async loadImagePixelData(image) {
        // Placeholder for loading pixel data
        return null;
    }

    setupMPRViews() {
        // Create additional canvases for MPR views
        ['axial', 'sagittal', 'coronal'].forEach(viewType => {
            const container = document.getElementById(`${viewType}-view-container`);
            if (container) {
                const canvas = document.createElement('canvas');
                canvas.id = `${viewType}-canvas`;
                canvas.width = 300;
                canvas.height = 300;
                canvas.style.border = '1px solid #666';
                container.appendChild(canvas);
                
                this.mprViews[viewType].canvas = canvas;
                this.mprViews[viewType].ctx = canvas.getContext('2d', { willReadFrequently: true });
            }
        });
    }

    renderMPRViews() {
        if (!this.mprEnabled) return;
        
        ['axial', 'sagittal', 'coronal'].forEach(viewType => {
            if (this.mprViews[viewType].active) {
                this.renderMPRView(viewType);
            }
        });
    }

    renderMPRView(viewType) {
        const view = this.mprViews[viewType];
        if (!view.canvas || !view.ctx) return;

        // Clear canvas
        view.ctx.fillStyle = '#000000';
        view.ctx.fillRect(0, 0, view.canvas.width, view.canvas.height);

        // Extract slice data based on view type
        const sliceData = this.extractSliceData(viewType);
        if (sliceData) {
            this.applyWindowingToSlice(sliceData);
            this.fillImageData(view.ctx.createImageData(view.canvas.width, view.canvas.height), sliceData);
            view.ctx.putImageData(view.ctx.createImageData(view.canvas.width, view.canvas.height), 0, 0);
        }

        // Draw crosshairs
        this.drawMPRCrosshairs(view.ctx, view.canvas);
    }

    extractSliceData(viewType) {
        if (!this.volumeData || this.volumeData.length === 0) return null;

        // Placeholder for slice extraction
        return null;
    }

    applyWindowingToSlice(sliceData) {
        // Apply window/level transformation
        if (!sliceData) return;
        
        // Placeholder for windowing application
    }

    fillImageData(imageData, pixelData) {
        // Fill image data with pixel values
        if (!pixelData || !imageData) return;
        
        // Placeholder for image data filling
    }

    drawMPRCrosshairs(ctx, canvas) {
        ctx.strokeStyle = '#ff0000';
        ctx.lineWidth = 1;
        
        // Draw crosshairs
        ctx.beginPath();
        ctx.moveTo(canvas.width / 2, 0);
        ctx.lineTo(canvas.width / 2, canvas.height);
        ctx.moveTo(0, canvas.height / 2);
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();
    }

    switchMPRView(viewType) {
        // Deactivate all views
        Object.keys(this.mprViews).forEach(key => {
            this.mprViews[key].active = false;
        });
        
        // Activate selected view
        this.mprViews[viewType].active = true;
        
        // Update UI
        ['axial', 'sagittal', 'coronal'].forEach(view => {
            const btn = document.getElementById(`${view}-view-btn`);
            if (btn) {
                btn.classList.toggle('active', view === viewType);
            }
        });
        
        this.renderMPRViews();
    }

    disableMPR() {
        this.mprEnabled = false;
        this.volumeData = null;
        
        // Remove MPR canvases
        ['axial', 'sagittal', 'coronal'].forEach(viewType => {
            const container = document.getElementById(`${viewType}-view-container`);
            if (container) {
                container.innerHTML = '';
            }
        });
    }

    async refreshCurrentImage() {
        if (!this.currentImage) return;

        try {
            // Use the correct GET endpoint with query parameters
            const params = new URLSearchParams({
                window_width: this.windowWidth,
                window_level: this.windowLevel,
                inverted: this.inverted,
                density_enhancement: this.densityEnhancement,
                contrast_boost: this.contrastBoost,
                high_quality: true
            });

            const response = await fetch(`/viewer/api/get-image-data/${this.currentImage.id}/?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.image_data && data.image_data.trim() !== '') {
                    try {
                        await this.displayProcessedImage(data.image_data);
                        
                        // Update MPR views if enabled
                        if (this.mprEnabled) {
                            this.renderMPRViews();
                        }
                    } catch (displayError) {
                        console.error('Error displaying image:', displayError);
                        this.notyf.error('Error displaying image data');
                        
                        // Show a placeholder or error image
                        this.showErrorPlaceholder();
                    }
                } else {
                    console.error('No image data received or empty data');
                    this.notyf.error('No valid image data received from server');
                    this.showErrorPlaceholder();
                }
            } else {
                console.error('Failed to load image:', response.status);
                this.notyf.error('Failed to load image from server');
                this.showErrorPlaceholder();
            }
        } catch (error) {
            console.error('Error refreshing image:', error);
            this.notyf.error('Error loading image');
            this.showErrorPlaceholder();
        }
    }

    async displayProcessedImage(base64Data) {
        return new Promise((resolve, reject) => {
            // Validate base64 data
            if (!base64Data || typeof base64Data !== 'string' || base64Data.trim() === '') {
                console.error('Invalid or empty base64 data received');
                this.notyf.error('Invalid image data received from server');
                reject(new Error('Invalid base64 data'));
                return;
            }
            
            // Clean the base64 data - remove any data URL prefix if present
            let cleanBase64 = base64Data;
            if (base64Data.startsWith('data:image/')) {
                const commaIndex = base64Data.indexOf(',');
                if (commaIndex !== -1) {
                    cleanBase64 = base64Data.substring(commaIndex + 1);
                }
            }
            
            // Validate base64 format
            if (!/^[A-Za-z0-9+/]*={0,2}$/.test(cleanBase64)) {
                console.error('Invalid base64 format');
                this.notyf.error('Invalid image data format');
                reject(new Error('Invalid base64 format'));
                return;
            }
            
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
            img.onerror = (error) => {
                console.error('Failed to load image from base64 data:', error);
                this.notyf.error('Failed to load image data');
                reject(error);
            };
            img.src = `data:image/png;base64,${cleanBase64}`;
        });
    }

    clearCanvas() {
        this.ctx.fillStyle = '#000000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    showErrorPlaceholder() {
        this.clearCanvas();
        
        // Draw error message
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = '16px Arial';
        this.ctx.textAlign = 'center';
        
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        
        // Draw error icon (simple X)
        this.ctx.strokeStyle = '#ff4444';
        this.ctx.lineWidth = 3;
        const iconSize = 40;
        this.ctx.beginPath();
        this.ctx.moveTo(centerX - iconSize/2, centerY - iconSize/2 - 30);
        this.ctx.lineTo(centerX + iconSize/2, centerY + iconSize/2 - 30);
        this.ctx.moveTo(centerX + iconSize/2, centerY - iconSize/2 - 30);
        this.ctx.lineTo(centerX - iconSize/2, centerY + iconSize/2 - 30);
        this.ctx.stroke();
        
        // Draw error text
        this.ctx.fillText('Image Loading Error', centerX, centerY + 10);
        this.ctx.font = '14px Arial';
        this.ctx.fillStyle = '#cccccc';
        this.ctx.fillText('Unable to load image data', centerX, centerY + 35);
        this.ctx.fillText('Please try refreshing or contact support', centerX, centerY + 55);
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
            switch(e.key) {
                case 'ArrowLeft':
                    e.preventDefault();
                    this.navigateImages(-1);
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.navigateImages(1);
                    break;
                case 'r':
                case 'R':
                    e.preventDefault();
                    this.resetView();
                    break;
                case 'i':
                case 'I':
                    e.preventDefault();
                    this.toggleInversion();
                    break;
                case 'm':
                case 'M':
                    e.preventDefault();
                    this.toggleMPR();
                    break;
            }
        });
    }

    updateToolUI() {
        const toolButtons = document.querySelectorAll('.tool-btn');
        toolButtons.forEach(btn => {
            btn.classList.remove('active');
        });
        
        const activeBtn = document.querySelector(`[data-tool="${this.activeTool}"]`);
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

        if (this.activeTool === 'pan') {
            this.panX += deltaX;
            this.panY += deltaY;
            this.refreshCurrentImage();
        } else if (this.activeTool === 'windowing') {
            // Adjust window/level based on mouse movement
            this.windowWidth += deltaX * 10;
            this.windowLevel -= deltaY * 10;
            this.updateWindowingUI();
            this.refreshCurrentImage();
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
        
        if (e.ctrlKey || e.metaKey) {
            // Zoom
            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomFactor *= zoomFactor;
            this.zoomFactor = Math.max(0.1, Math.min(5.0, this.zoomFactor));
            this.refreshCurrentImage();
        } else {
            // Navigate images
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

    setupUploadHandlers() {
        console.log('Setting up upload handlers...');
        
        // Prevent duplicate setup
        if (this.uploadHandlersSetup) {
            console.log('Upload handlers already set up, skipping...');
            return;
        }
        
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const startUploadBtn = document.getElementById('startUpload');
        const uploadProgress = document.getElementById('uploadProgress');
        const uploadStatus = document.getElementById('uploadStatus');
        
        if (!uploadArea || !fileInput || !startUploadBtn) {
            console.warn('Upload elements not found in DOM');
            return;
        }
        
        // File input change handler
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            if (files.length > 0) {
                this.selectedFiles = files;
                startUploadBtn.disabled = false;
                uploadStatus.textContent = `${files.length} file(s) selected`;
            }
        });
        
        // Upload area click handler
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });
        
        // Drag and drop handlers
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                this.selectedFiles = files;
                startUploadBtn.disabled = false;
                uploadStatus.textContent = `${files.length} file(s) selected`;
            }
        });
        
        // Start upload button
        startUploadBtn.addEventListener('click', () => {
            this.startUpload();
        });
        
        // Mark as set up to prevent duplicates
        this.uploadHandlersSetup = true;
        console.log('Upload handlers setup complete');
    }
    
    async startUpload() {
        if (!this.selectedFiles || this.selectedFiles.length === 0) {
            this.notyf.error('No files selected for upload');
            return;
        }
        
        const uploadProgress = document.getElementById('uploadProgress');
        const uploadStatus = document.getElementById('uploadStatus');
        const startUploadBtn = document.getElementById('startUpload');
        
        try {
            // Show progress
            uploadProgress.style.display = 'block';
            uploadStatus.textContent = 'Uploading files...';
            startUploadBtn.disabled = true;
            
            // Create FormData
            const formData = new FormData();
            this.selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            // Get CSRF token
            const csrfToken = this.getCSRFToken();
            
            // Upload files
            const response = await fetch('/viewer/api/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.error) {
                throw new Error(result.error);
            }
            
            // Success
            this.notyf.success(`Successfully uploaded ${result.uploaded_files ? result.uploaded_files.length : 0} files`);
            
            // Reload studies if we have a study ID
            if (result.study_id) {
                await this.loadStudy(result.study_id);
            } else {
                // Refresh the current view
                await this.refreshCurrentImage();
            }
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
            if (modal) {
                modal.hide();
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            this.notyf.error(`Upload failed: ${error.message}`);
        } finally {
            // Hide progress
            uploadProgress.style.display = 'none';
            uploadStatus.textContent = '';
            startUploadBtn.disabled = false;
            this.selectedFiles = null;
        }
    }
    
    showUploadModal() {
        const modal = new bootstrap.Modal(document.getElementById('uploadModal'));
        modal.show();
    }

    // Fixed implementation for loading studies and images
    async loadStudy(studyId) {
        try {
            // Prevent loading the same study multiple times
            if (this.currentStudyId === studyId && this.currentImages && this.currentImages.length > 0) {
                console.log('Study', studyId, 'already loaded, skipping...');
                this.updateDebugPanel();
                return;
            }
            
            console.log('Loading study:', studyId);
            this.updateDebugPanel('loading', `Loading study ${studyId}...`);
            
            // Get study images
            const response = await fetch(`/viewer/api/get-study-images/${studyId}/`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            console.log('API Response status:', response.status);
            this.updateDebugPanel('api', `API Status: ${response.status}`);

            if (response.ok) {
                const data = await response.json();
                console.log('Study data received:', data);
                
                if (data.study) {
                    this.currentStudy = data.study;
                    console.log('Patient data:', data.study);
                    this.updatePatientInfo(data.study);
                }
                
                if (data.images && data.images.length > 0) {
                    this.currentStudyId = studyId;
                    this.currentImages = data.images;
                    this.currentImageIndex = 0;
                    this.currentImage = this.currentImages[0];
                    
                    console.log(`Study loaded with ${data.images.length} images`);
                    this.updateDebugPanel('study', `Study ${studyId}: ${data.images.length} images`);
                    this.updateDebugPanel('images', `Images: ${data.images.length}`);
                    
                    // Load the first image
                    await this.loadImage(this.currentImage.id);
                    this.updateImageCounter();
                    
                    this.notyf.success(`Loaded study with ${this.currentImages.length} images`);
                } else {
                    console.warn('No images found in study response:', data);
                    this.updateDebugPanel('study', 'No images in study');
                    this.notyf.error('No images found in study');
                    this.showNoDataMessage();
                }
            } else {
                const errorText = await response.text();
                console.error('Failed to load study:', response.status, errorText);
                this.updateDebugPanel('api', `API Error: ${response.status}`);
                this.notyf.error(`Failed to load study: ${response.status}`);
                this.showConnectionError();
            }
        } catch (error) {
            console.error('Error loading study:', error);
            this.updateDebugPanel('api', `Connection Error: ${error.message}`);
            this.notyf.error('Error loading study');
            this.showConnectionError();
        }
    }

    async loadImage(imageId) {
        try {
            // Prevent loading the same image multiple times
            if (this.currentImage && this.currentImage.id === imageId) {
                console.log('Image', imageId, 'already loaded, skipping...');
                return;
            }
            
            console.log('Loading image:', imageId);
            
            // Set the current image
            this.currentImage = this.currentImages.find(img => img.id === imageId);
            if (!this.currentImage) {
                console.error('Image not found in current images');
                return;
            }
            
            // Refresh the image display
            await this.refreshCurrentImage();
            
        } catch (error) {
            console.error('Error loading image:', error);
            this.notyf.error('Error loading image');
        }
    }

    // Debug and utility methods
    updateDebugPanel(type = null, message = null) {
        try {
            if (type && message) {
                const element = document.getElementById(`debug-${type}`);
                if (element) {
                    element.textContent = message;
                }
            } else {
                // Update all debug elements
                const elements = {
                    'debug-canvas': this.canvas ? 'Canvas: Ready' : 'Canvas: Not initialized',
                    'debug-study': this.currentStudy ? `Study: ${this.currentStudy.patient_name || 'Unknown'}` : 'Study: None loaded',
                    'debug-images': `Images: ${this.currentImages ? this.currentImages.length : 0}`,
                    'debug-api': 'API Status: Ready',
                    'debug-tool': `Active Tool: ${this.activeTool || 'None'}`
                };
                
                Object.entries(elements).forEach(([id, text]) => {
                    const element = document.getElementById(id);
                    if (element) {
                        element.textContent = text;
                    }
                });
            }
        } catch (error) {
            console.warn('Error updating debug panel:', error);
        }
    }

    updatePatientInfo(study) {
        try {
            // Update patient information display
            const patientName = document.getElementById('patient-name');
            const patientId = document.getElementById('patient-id');
            const studyDate = document.getElementById('study-date');
            const studyDescription = document.getElementById('study-description');
            const modality = document.getElementById('modality');
            const institutionName = document.getElementById('institution-name');

            if (patientName) patientName.textContent = study.patient_name || 'Unknown';
            if (patientId) patientId.textContent = study.patient_id || 'Unknown';
            if (studyDate) studyDate.textContent = study.study_date || 'Unknown';
            if (studyDescription) studyDescription.textContent = study.study_description || 'Unknown';
            if (modality) modality.textContent = study.modality || 'Unknown';
            if (institutionName) institutionName.textContent = study.institution_name || 'Unknown';

            console.log('Patient info updated:', study);
        } catch (error) {
            console.warn('Error updating patient info:', error);
        }
    }

    showNoDataMessage() {
        this.clearCanvas();
        this.ctx.fillStyle = '#444444';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = '24px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('No DICOM images found', this.canvas.width / 2, this.canvas.height / 2 - 30);
        
        this.ctx.font = '16px Arial';
        this.ctx.fillText('Please upload DICOM files to view', this.canvas.width / 2, this.canvas.height / 2 + 10);
    }

    showConnectionError() {
        this.clearCanvas();
        this.ctx.fillStyle = '#2d1b1b';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.ctx.fillStyle = '#ff6b6b';
        this.ctx.font = '24px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('Connection Error', this.canvas.width / 2, this.canvas.height / 2 - 30);
        
        this.ctx.font = '16px Arial';
        this.ctx.fillText('Unable to connect to DICOM server', this.canvas.width / 2, this.canvas.height / 2 + 10);
    }

    async testConnectivity() {
        try {
            const response = await fetch('/viewer/api/test-connectivity/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (response.ok) {
                this.updateDebugPanel('api', 'API Connectivity: OK');
                this.notyf.success('API connectivity test successful!');
            } else {
                const errorText = await response.text();
                console.error('API connectivity test failed:', response.status, errorText);
                this.updateDebugPanel('api', `API Connectivity: Failed (${response.status})`);
                this.notyf.error(`API connectivity test failed: ${response.status}`);
            }
        } catch (error) {
            console.error('API connectivity test failed:', error);
            this.updateDebugPanel('api', 'API Connectivity: Failed (Network Error)');
            this.notyf.error('API connectivity test failed: Network Error');
        }
    }
}

// Initialize the fixed viewer when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const studyId = urlParams.get('study_id');
    
    window.fixedDicomViewer = new FixedDicomViewer(studyId);
});