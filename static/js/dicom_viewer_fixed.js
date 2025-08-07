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

        // Magnification support
        this.magnificationEnabled = false;
        this.magnificationLevel = 2.0;
        this.magnificationRadius = 100;
        this.magnificationPos = { x: 0, y: 0 };

        // Measurement system with pixel spacing
        this.measurements = [];
        this.activeMeasurement = null;
        this.pixelSpacing = { x: 1.0, y: 1.0 }; // Default 1mm per pixel
        this.measurementUnits = 'mm'; // Default to millimeters
        this.calibrationFactor = 1.0; // For manual calibration

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
    
                // Initialize series list
        this.currentSeriesList = [];
        
        // Setup keyboard event listeners
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcut(e));
        
        // Setup thumbnail toggle
        const thumbnailToggle = document.getElementById('thumbnail-toggle');
        if (thumbnailToggle) {
            thumbnailToggle.addEventListener('click', () => this.toggleThumbnails());
        }
        
        // Setup navigation buttons
        this.setupNavigationButtons();
        
        // Setup reconstruction buttons
        this.setupAllButtons();
    }

    createCanvas() {
        const canvasContainer = document.getElementById('canvas-container');
        if (canvasContainer) {
            this.canvas = document.createElement('canvas');
            this.canvas.id = 'dicom-canvas-advanced';
            this.canvas.className = 'dicom-canvas-advanced';
            this.canvas.style.position = 'absolute';
            this.canvas.style.top = '0';
            this.canvas.style.left = '0';
            this.canvas.style.width = '100%';
            this.canvas.style.height = '100%';
            this.canvas.style.backgroundColor = '#000';
            
            canvasContainer.appendChild(this.canvas);
            this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
            
            // Initialize canvas size properly
            this.resizeCanvas();
            
            // Add resize listener to handle container size changes
            window.addEventListener('resize', () => this.resizeCanvas());
        }
    }

    setupHighQualityRendering() {
        if (this.canvas && this.ctx) {
            // Enable high-quality rendering
            this.ctx.imageSmoothingEnabled = true;
            this.ctx.imageSmoothingQuality = 'high';
            
            // Set canvas size to match container
            this.resizeCanvas();
        }
    }
    
    resizeCanvas() {
        const container = document.getElementById('canvas-container');
        if (container && this.canvas) {
            const rect = container.getBoundingClientRect();
            
            // Set the actual size of the canvas
            this.canvas.width = rect.width || 800;
            this.canvas.height = rect.height || 600;
            
            // Scale it to device pixel ratio for sharp rendering
            const dpr = window.devicePixelRatio || 1;
            this.canvas.width *= dpr;
            this.canvas.height *= dpr;
            
            // Scale the canvas style size back down
            this.canvas.style.width = rect.width + 'px';
            this.canvas.style.height = rect.height + 'px';
            
            // Scale the drawing context to match device pixel ratio
            this.ctx.scale(dpr, dpr);
            
            // Re-setup high quality rendering after resize
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
                        this.notyf.success(`Applied ${preset.description}`);
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
        if (!this.currentImages || this.currentImages.length < 3) {
            this.notyf.error('Need at least 3 images for MPR reconstruction');
            return;
        }

        this.mprEnabled = !this.mprEnabled;
        
        if (this.mprEnabled) {
            this.notyf.info('Initializing MPR reconstruction...');
            await this.initializeMPR();
        } else {
            this.disableMPR();
            this.notyf.info('MPR disabled');
        }
    }

    async initializeMPR() {
        try {
            // Show MPR controls
            const mprPanel = document.getElementById('mpr-reconstruction-panel');
            if (mprPanel) {
                mprPanel.style.display = 'block';
            }

            // Initialize MPR views
            await this.createMPRViews();
            this.notyf.success('MPR reconstruction initialized');
            
        } catch (error) {
            console.error('Error initializing MPR:', error);
            this.notyf.error('Failed to initialize MPR reconstruction');
            this.mprEnabled = false;
        }
    }

    async createMPRViews() {
        const mprContainer = document.getElementById('mpr-views-container');
        if (!mprContainer) {
            console.error('MPR container not found');
            return;
        }

        // Create MPR view elements if they don't exist
        const views = ['axial', 'sagittal', 'coronal'];
        views.forEach(view => {
            let viewElement = document.getElementById(`mpr-${view}`);
            if (!viewElement) {
                viewElement = document.createElement('div');
                viewElement.id = `mpr-${view}`;
                viewElement.className = 'mpr-view';
                viewElement.innerHTML = `
                    <h4>${view.charAt(0).toUpperCase() + view.slice(1)} View</h4>
                    <canvas id="${view}-canvas" width="256" height="256"></canvas>
                `;
                mprContainer.appendChild(viewElement);
            }

            // Store canvas references
            const canvas = document.getElementById(`${view}-canvas`);
            if (canvas) {
                this.mprViews[view].canvas = canvas;
                this.mprViews[view].ctx = canvas.getContext('2d');
            }
        });

        // Generate MPR slices
        this.generateMPRSlices();
    }

    generateMPRSlices() {
        if (!this.currentImages || this.currentImages.length === 0) return;

        const currentIndex = this.currentImageIndex;
        const totalImages = this.currentImages.length;

        // Axial view (current slice)
        this.renderMPRView('axial', currentIndex);

        // Sagittal view (reconstructed from all slices at current X position)
        this.renderMPRView('sagittal', Math.floor(currentIndex * 0.5));

        // Coronal view (reconstructed from all slices at current Y position)
        this.renderMPRView('coronal', Math.floor(currentIndex * 0.7));
    }

    renderMPRView(viewType, sliceIndex) {
        const view = this.mprViews[viewType];
        if (!view.canvas || !view.ctx) return;

        const canvas = view.canvas;
        const ctx = view.ctx;

        // Clear canvas
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // For demonstration, we'll render a simplified version
        // In a real implementation, this would reconstruct from volume data
        if (this.currentImage && this.currentImage.image) {
            const scale = Math.min(canvas.width / this.currentImage.image.width, 
                                 canvas.height / this.currentImage.image.height);
            
            const width = this.currentImage.image.width * scale;
            const height = this.currentImage.image.height * scale;
            const x = (canvas.width - width) / 2;
            const y = (canvas.height - height) / 2;

            ctx.drawImage(this.currentImage.image, x, y, width, height);

            // Add view-specific transformations
            switch (viewType) {
                case 'sagittal':
                    ctx.save();
                    ctx.translate(canvas.width / 2, canvas.height / 2);
                    ctx.rotate(Math.PI / 2);
                    ctx.translate(-canvas.width / 2, -canvas.height / 2);
                    ctx.restore();
                    break;
                case 'coronal':
                    ctx.save();
                    ctx.translate(canvas.width / 2, canvas.height / 2);
                    ctx.scale(1, -1);
                    ctx.translate(-canvas.width / 2, -canvas.height / 2);
                    ctx.restore();
                    break;
            }

            // Draw crosshairs
            this.drawMPRCrosshairs(ctx, canvas);
        }
    }

    enableVolumeRendering() {
        if (!this.currentImages || this.currentImages.length < 10) {
            this.notyf.error('Need at least 10 images for volume rendering');
            return;
        }

        this.notyf.info('Volume rendering feature coming soon!');
        // TODO: Implement proper volume rendering with WebGL
    }

    enableMIP() {
        if (!this.currentImages || this.currentImages.length < 5) {
            this.notyf.error('Need at least 5 images for MIP reconstruction');
            return;
        }

        this.notyf.info('Maximum Intensity Projection feature coming soon!');
        // TODO: Implement MIP reconstruction
    }

    disableMPR() {
        this.mprEnabled = false;
        const mprPanel = document.getElementById('mpr-reconstruction-panel');
        if (mprPanel) {
            mprPanel.style.display = 'none';
        }
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
                            this.generateMPRSlices();
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
            // Enhanced validation for actual DICOM data
            if (!base64Data || typeof base64Data !== 'string' || base64Data.trim() === '') {
                console.error('Invalid or empty base64 data received from server');
                this.notyf.error('No image data received from server');
                this.showErrorPlaceholder();
                reject(new Error('Invalid base64 data'));
                return;
            }
            
            // Clean the base64 data
            let cleanBase64 = base64Data;
            if (base64Data.startsWith('data:image/')) {
                const commaIndex = base64Data.indexOf(',');
                if (commaIndex !== -1) {
                    cleanBase64 = base64Data.substring(commaIndex + 1);
                }
            }
            
            // Validate base64 format
            if (!/^[A-Za-z0-9+/]*={0,2}$/.test(cleanBase64)) {
                console.error('Invalid base64 format received');
                this.notyf.error('Invalid image format received from server');
                this.showErrorPlaceholder();
                reject(new Error('Invalid base64 format'));
                return;
            }
            
            const img = new Image();
            img.onload = () => {
                try {
                    this.clearCanvas();
                    
                    // Enhanced rendering for medical imaging
                    const dpr = window.devicePixelRatio || 1;
                    const canvasWidth = this.canvas.width / dpr;
                    const canvasHeight = this.canvas.height / dpr;
                    
                    const aspectRatio = img.width / img.height;
                    let displayWidth, displayHeight;
                    
                    // Calculate display size maintaining aspect ratio
                    if (canvasWidth / canvasHeight > aspectRatio) {
                        displayHeight = canvasHeight * this.zoomFactor;
                        displayWidth = displayHeight * aspectRatio;
                    } else {
                        displayWidth = canvasWidth * this.zoomFactor;
                        displayHeight = displayWidth / aspectRatio;
                    }
                    
                    // Center the image with pan offset
                    const x = (canvasWidth - displayWidth) / 2 + this.panX;
                    const y = (canvasHeight - displayHeight) / 2 + this.panY;
                    
                    // Apply medical imaging optimizations
                    this.ctx.save();
                    this.ctx.imageSmoothingEnabled = true;
                    this.ctx.imageSmoothingQuality = 'high';
                    
                    // Apply transformations
                    this.ctx.translate(x + displayWidth / 2, y + displayHeight / 2);
                    this.ctx.rotate(this.rotation * Math.PI / 180);
                    this.ctx.scale(
                        this.flipHorizontal ? -1 : 1,
                        this.flipVertical ? -1 : 1
                    );
                    
                    // Draw with high quality
                    this.ctx.drawImage(img, -displayWidth / 2, -displayHeight / 2, displayWidth, displayHeight);
                    this.ctx.restore();
                    
                    // Apply post-processing
                    this.applyImageEnhancements();
                    
                    // Store image data
                    this.imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
                    this.originalImageData = this.ctx.createImageData(this.imageData);
                    this.originalImageData.data.set(this.imageData.data);
                    
                    // Update UI
                    this.updateViewportInfo();
                    this.updateDebugPanel();
                    
                    // Store current image reference
                    this.currentImage = { image: img, width: img.width, height: img.height };
                    
                    console.log('Image displayed successfully:', displayWidth, 'x', displayHeight);
                    resolve();
                    
                } catch (error) {
                    console.error('Error in displayProcessedImage:', error);
                    this.notyf.error('Error rendering image: ' + error.message);
                    this.showErrorPlaceholder();
                    reject(error);
                }
            };
            
            img.onerror = (error) => {
                console.error('Failed to load image:', error);
                this.notyf.error('Failed to load image - invalid format or corrupted data');
                this.showErrorPlaceholder();
                reject(new Error('Image load failed'));
            };
            
            // Set the image source with proper data URI
            img.src = `data:image/png;base64,${cleanBase64}`;
        });
    }

    // === COMPREHENSIVE IMAGE PROCESSING ===
    applyImageEnhancements() {
        if (!this.imageData) return;

        let imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        let data = imageData.data;

        // Apply windowing (Window/Level adjustment)
        if (this.windowWidth && this.windowLevel) {
            this.applyWindowing(data);
        }

        // Apply inversion if enabled
        if (this.inverted) {
            this.invertImage(data);
        }

        // Apply contrast enhancement
        if (this.contrastBoost !== 1.0) {
            this.adjustContrast(data, this.contrastBoost);
        }

        // Apply density enhancement for tissue differentiation
        if (this.densityEnhancement) {
            this.enhanceDensity(data);
        }

        // Put processed data back to canvas
        this.ctx.putImageData(imageData, 0, 0);
    }

    applyWindowing(data) {
        const windowMin = this.windowLevel - this.windowWidth / 2;
        const windowMax = this.windowLevel + this.windowWidth / 2;
        const windowRange = windowMax - windowMin;

        for (let i = 0; i < data.length; i += 4) {
            // Convert RGB to grayscale for HU approximation
            const gray = (data[i] + data[i + 1] + data[i + 2]) / 3;
            
            // Approximate HU value (this is simplified - real DICOM uses slope/intercept)
            const hu = (gray - 128) * 4; // Rough approximation
            
            // Apply windowing
            let windowedValue;
            if (hu <= windowMin) {
                windowedValue = 0;
            } else if (hu >= windowMax) {
                windowedValue = 255;
            } else {
                windowedValue = ((hu - windowMin) / windowRange) * 255;
            }

            // Apply back to RGB channels
            data[i] = windowedValue;     // Red
            data[i + 1] = windowedValue; // Green
            data[i + 2] = windowedValue; // Blue
            // Alpha channel remains unchanged
        }
    }

    invertImage(data) {
        for (let i = 0; i < data.length; i += 4) {
            data[i] = 255 - data[i];         // Red
            data[i + 1] = 255 - data[i + 1]; // Green
            data[i + 2] = 255 - data[i + 2]; // Blue
            // Alpha channel remains unchanged
        }
    }

    adjustContrast(data, contrast) {
        const factor = (259 * (contrast * 255 + 255)) / (255 * (259 - contrast * 255));
        
        for (let i = 0; i < data.length; i += 4) {
            data[i] = Math.max(0, Math.min(255, factor * (data[i] - 128) + 128));
            data[i + 1] = Math.max(0, Math.min(255, factor * (data[i + 1] - 128) + 128));
            data[i + 2] = Math.max(0, Math.min(255, factor * (data[i + 2] - 128) + 128));
        }
    }

    enhanceDensity(data) {
        // Enhance tissue density differences for better visualization
        for (let i = 0; i < data.length; i += 4) {
            const gray = (data[i] + data[i + 1] + data[i + 2]) / 3;
            
            // Apply sigmoid function for better contrast in mid-range
            const enhanced = 255 / (1 + Math.exp(-0.1 * (gray - 128)));
            
            data[i] = enhanced;
            data[i + 1] = enhanced;
            data[i + 2] = enhanced;
        }
    }

    // === COMPREHENSIVE TOOL IMPLEMENTATIONS ===
    
    // Zoom tools
    zoomIn() {
        this.zoomFactor = Math.min(this.zoomFactor * 1.2, 10);
        this.redrawCanvas();
        this.notyf.info(`Zoom: ${Math.round(this.zoomFactor * 100)}%`);
    }

    zoomOut() {
        this.zoomFactor = Math.max(this.zoomFactor * 0.8, 0.1);
        this.redrawCanvas();
        this.notyf.info(`Zoom: ${Math.round(this.zoomFactor * 100)}%`);
    }

    resetZoom() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.rotation = 0;
        this.redrawCanvas();
        this.notyf.success('View reset');
    }

    fitToWindow() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.redrawCanvas();
        this.notyf.info('Fit to window');
    }

    actualSize() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.redrawCanvas();
        this.notyf.info('Actual size (100%)');
    }

    // Rotation and flip tools
    rotateLeft() {
        this.rotation -= 90;
        if (this.rotation < 0) this.rotation += 360;
        this.redrawCanvas();
        this.notyf.info(`Rotated to ${this.rotation}°`);
    }

    rotateRight() {
        this.rotation += 90;
        if (this.rotation >= 360) this.rotation -= 360;
        this.redrawCanvas();
        this.notyf.info(`Rotated to ${this.rotation}°`);
    }

    flipHorizontally() {
        this.flipHorizontal = !this.flipHorizontal;
        this.redrawCanvas();
        this.notyf.info(`Horizontal flip: ${this.flipHorizontal ? 'ON' : 'OFF'}`);
    }

    flipVertically() {
        this.flipVertical = !this.flipVertical;
        this.redrawCanvas();
        this.notyf.info(`Vertical flip: ${this.flipVertical ? 'ON' : 'OFF'}`);
    }

    // Window/Level tools
    setWindowPreset(presetName) {
        const preset = this.windowPresets[presetName];
        if (preset) {
            this.windowWidth = preset.ww;
            this.windowLevel = preset.wl;
            this.refreshCurrentImage();
            this.notyf.success(`Applied ${preset.description}`);
        }
    }

    adjustWindowWidth(delta) {
        this.windowWidth = Math.max(1, this.windowWidth + delta);
        this.refreshCurrentImage();
        this.updateWindowLevelDisplay();
    }

    adjustWindowLevel(delta) {
        this.windowLevel = Math.max(-1000, Math.min(1000, this.windowLevel + delta));
        this.refreshCurrentImage();
        this.updateWindowLevelDisplay();
    }

    // Image enhancement tools
    toggleInversion() {
        this.inverted = !this.inverted;
        this.applyImageEnhancements();
        this.notyf.info(`Inversion: ${this.inverted ? 'ON' : 'OFF'}`);
    }

    toggleDensityEnhancement() {
        this.densityEnhancement = !this.densityEnhancement;
        this.applyImageEnhancements();
        this.notyf.info(`Density enhancement: ${this.densityEnhancement ? 'ON' : 'OFF'}`);
    }

    adjustContrast(value) {
        this.contrastBoost = Math.max(0.1, Math.min(3.0, value));
        this.applyImageEnhancements();
        this.notyf.info(`Contrast: ${Math.round(this.contrastBoost * 100)}%`);
    }
    
    showErrorPlaceholder() {
        try {
            this.clearCanvas();
            this.ctx.fillStyle = '#1a1a1a';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            
            // Draw error message
            this.ctx.fillStyle = '#ff4444';
            this.ctx.font = '20px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('Image Loading Error', this.canvas.width / 2, this.canvas.height / 2 - 20);
            
            this.ctx.fillStyle = '#888888';
            this.ctx.font = '14px Arial';
            this.ctx.fillText('Check DICOM file path and format', this.canvas.width / 2, this.canvas.height / 2 + 10);
        } catch (e) {
            console.error('Error showing placeholder:', e);
        }
    }
    
    hideErrorPlaceholder() {
        // This method is called when an image successfully loads
        // Any error state cleanup can be done here
    }

    clearCanvas() {
        this.ctx.fillStyle = '#000000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }
    
    updateViewportInfo() {
        // Update zoom level display
        const zoomElement = document.getElementById('zoom-level');
        if (zoomElement) {
            zoomElement.textContent = `${Math.round(this.zoomFactor * 100)}%`;
        }
        
        // Update window/level display
        const windowInfoElement = document.getElementById('window-info');
        if (windowInfoElement) {
            windowInfoElement.textContent = `W: ${this.windowWidth} L: ${this.windowLevel}`;
        }
        
        // Update slice info
        const sliceInfoElement = document.getElementById('slice-info');
        if (sliceInfoElement && this.currentImages) {
            const currentIndex = this.currentImages.findIndex(img => img.id === this.currentImage?.id) + 1;
            sliceInfoElement.textContent = `Slice: ${currentIndex}/${this.currentImages.length}`;
        }
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

        let isDrawing = false;
        let startPoint = null;

        // Mouse down event
        this.canvas.addEventListener('mousedown', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const canvasX = e.clientX - rect.left;
            const canvasY = e.clientY - rect.top;
            const imageCoords = this.canvasToImageCoords(canvasX, canvasY);

            if (this.activeTool.startsWith('measure_')) {
                isDrawing = true;
                startPoint = imageCoords;
                this.isDragging = true;
            } else if (this.activeTool.startsWith('roi_')) {
                isDrawing = true;
                startPoint = imageCoords;
                this.isDragging = true;
            } else if (this.activeTool === 'windowing') {
                this.isDragging = true;
                this.dragStart = { x: e.clientX, y: e.clientY };
                this.lastMousePos = { x: e.clientX, y: e.clientY };
            } else if (this.activeTool === 'pan') {
                this.isDragging = true;
                this.dragStart = { x: canvasX, y: canvasY };
            } else if (this.activeTool === 'zoom') {
                // Handle zoom clicks
                const factor = e.button === 0 ? 1.2 : 0.8; // Left click zoom in, right click zoom out
                this.zoomFactor *= factor;
                this.redrawCanvas();
            }
        });

        // Mouse move event
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const canvasX = e.clientX - rect.left;
            const canvasY = e.clientY - rect.top;

            // Handle magnification
            if (this.magnificationEnabled && !isDrawing) {
                this.magnificationPos = { x: canvasX, y: canvasY };
                this.redrawCanvas();
                this.drawMagnifier(canvasX, canvasY);
            }

            // Handle measurement drawing
            if (isDrawing && this.activeTool.startsWith('measure_') && startPoint) {
                const imageCoords = this.canvasToImageCoords(canvasX, canvasY);
                
                // Show temporary measurement line
                this.redrawCanvas();
                this.ctx.save();
                this.ctx.strokeStyle = '#00ff88';
                this.ctx.lineWidth = 2;
                this.ctx.setLineDash([5, 5]);
                
                const startCanvas = this.imageToCanvasCoords(startPoint.x, startPoint.y);
                this.ctx.beginPath();
                this.ctx.moveTo(startCanvas.x, startCanvas.y);
                this.ctx.lineTo(canvasX, canvasY);
                this.ctx.stroke();
                this.ctx.restore();
            }

            // Handle ROI drawing
            if (isDrawing && this.activeTool.startsWith('roi_') && startPoint) {
                const imageCoords = this.canvasToImageCoords(canvasX, canvasY);
                
                // Show temporary ROI rectangle
                this.redrawCanvas();
                this.ctx.save();
                this.ctx.strokeStyle = '#ff6b35';
                this.ctx.fillStyle = 'rgba(255, 107, 53, 0.2)';
                this.ctx.lineWidth = 2;
                this.ctx.setLineDash([5, 5]);
                
                const startCanvas = this.imageToCanvasCoords(startPoint.x, startPoint.y);
                const width = canvasX - startCanvas.x;
                const height = canvasY - startCanvas.y;
                
                this.ctx.fillRect(startCanvas.x, startCanvas.y, width, height);
                this.ctx.strokeRect(startCanvas.x, startCanvas.y, width, height);
                this.ctx.restore();
            }

            // Handle windowing
            if (this.isDragging && this.activeTool === 'windowing' && this.lastMousePos) {
                const deltaX = e.clientX - this.lastMousePos.x;
                const deltaY = e.clientY - this.lastMousePos.y;

                this.windowWidth += deltaX * 4;
                this.windowLevel += deltaY * 4;

                this.windowWidth = Math.max(1, this.windowWidth);
                this.windowLevel = Math.max(-1000, Math.min(1000, this.windowLevel));

                this.lastMousePos = { x: e.clientX, y: e.clientY };
                this.refreshCurrentImage();
            }

            // Handle panning
            if (this.isDragging && this.activeTool === 'pan' && this.dragStart) {
                this.panX += canvasX - this.dragStart.x;
                this.panY += canvasY - this.dragStart.y;
                this.dragStart = { x: canvasX, y: canvasY };
                this.redrawCanvas();
            }
        });

        // Mouse up event
        this.canvas.addEventListener('mouseup', (e) => {
            if (isDrawing && this.activeTool.startsWith('measure_') && startPoint) {
                const rect = this.canvas.getBoundingClientRect();
                const canvasX = e.clientX - rect.left;
                const canvasY = e.clientY - rect.top;
                const endPoint = this.canvasToImageCoords(canvasX, canvasY);

                const measurementType = this.activeTool.replace('measure_', '');
                this.addMeasurement(startPoint, endPoint, measurementType);
                
                isDrawing = false;
                startPoint = null;
            }

            if (isDrawing && this.activeTool.startsWith('roi_') && startPoint) {
                const rect = this.canvas.getBoundingClientRect();
                const canvasX = e.clientX - rect.left;
                const canvasY = e.clientY - rect.top;
                const endPoint = this.canvasToImageCoords(canvasX, canvasY);

                const roiType = this.activeTool.replace('roi_', '');
                this.addROI(startPoint, endPoint, roiType);
                
                isDrawing = false;
                startPoint = null;
            }

            this.isDragging = false;
            this.dragStart = null;
            this.lastMousePos = null;
        });

        // Mouse wheel for zooming
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const factor = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomFactor *= factor;
            this.zoomFactor = Math.max(0.1, Math.min(10, this.zoomFactor));
            this.redrawCanvas();
        });

        // Right click context menu (disable)
        this.canvas.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });

        // Double click to reset zoom
        this.canvas.addEventListener('dblclick', () => {
            this.zoomFactor = 1.0;
            this.panX = 0;
            this.panY = 0;
            this.redrawCanvas();
        });

        // Set up tool buttons
        this.setupToolButtons();
    }

    setupToolButtons() {
        // Measurement tool buttons
        const measureDistanceBtn = document.getElementById('measure-distance-btn');
        if (measureDistanceBtn) {
            measureDistanceBtn.addEventListener('click', () => {
                this.enableMeasurementTool('distance');
                this.setActiveToolButton(measureDistanceBtn);
            });
        }

        const measureAngleBtn = document.getElementById('measure-angle-btn');
        if (measureAngleBtn) {
            measureAngleBtn.addEventListener('click', () => {
                this.enableMeasurementTool('angle');
                this.setActiveToolButton(measureAngleBtn);
            });
        }

        const measureAreaBtn = document.getElementById('measure-area-btn');
        if (measureAreaBtn) {
            measureAreaBtn.addEventListener('click', () => {
                this.enableMeasurementTool('area');
                this.setActiveToolButton(measureAreaBtn);
            });
        }

        // Magnification tool button
        const magnifyBtn = document.getElementById('magnify-btn');
        if (magnifyBtn) {
            magnifyBtn.addEventListener('click', () => {
                if (this.magnificationEnabled) {
                    this.disableMagnification();
                    magnifyBtn.classList.remove('active');
                } else {
                    this.enableMagnification();
                    this.setActiveToolButton(magnifyBtn);
                }
            });
        }

        // Clear measurements button
        const clearMeasurementsBtn = document.getElementById('clear-measurements-btn');
        if (clearMeasurementsBtn) {
            clearMeasurementsBtn.addEventListener('click', () => {
                this.clearMeasurements();
            });
        }

        // Tool activation buttons
        const panBtn = document.getElementById('pan-btn') || document.getElementById('pan-adv-btn');
        if (panBtn) {
            panBtn.addEventListener('click', () => {
                this.activeTool = 'pan';
                this.canvas.style.cursor = 'move';
                this.setActiveToolButton(panBtn);
            });
        }

        const zoomBtn = document.getElementById('zoom-adv-btn') || document.getElementById('zoom-btn');
        if (zoomBtn) {
            zoomBtn.addEventListener('click', () => {
                this.activeTool = 'zoom';
                this.canvas.style.cursor = 'zoom-in';
                this.setActiveToolButton(zoomBtn);
            });
        }

        const windowingBtn = document.getElementById('windowing-btn') || document.getElementById('windowing-adv-btn');
        if (windowingBtn) {
            windowingBtn.addEventListener('click', () => {
                this.activeTool = 'windowing';
                this.canvas.style.cursor = 'default';
                this.setActiveToolButton(windowingBtn);
            });
        }

        // Zoom control buttons
        const zoomInBtn = document.getElementById('zoom-in-btn');
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => this.zoomIn());
        }

        const zoomOutBtn = document.getElementById('zoom-out-btn');
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => this.zoomOut());
        }

        const resetBtn = document.getElementById('reset-adv-btn') || document.getElementById('reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetZoom());
        }

        const fitBtn = document.getElementById('fit-to-window-btn') || document.getElementById('fit-btn');
        if (fitBtn) {
            fitBtn.addEventListener('click', () => this.fitToWindow());
        }

        const actualSizeBtn = document.getElementById('actual-size-btn');
        if (actualSizeBtn) {
            actualSizeBtn.addEventListener('click', () => this.actualSize());
        }

        // Rotation and flip buttons
        const rotateLeftBtn = document.getElementById('rotate-left-btn') || document.getElementById('rotate-btn');
        if (rotateLeftBtn) {
            rotateLeftBtn.addEventListener('click', () => this.rotateLeft());
        }

        const rotateRightBtn = document.getElementById('rotate-right-btn');
        if (rotateRightBtn) {
            rotateRightBtn.addEventListener('click', () => this.rotateRight());
        }

        const flipBtn = document.getElementById('flip-btn');
        if (flipBtn) {
            flipBtn.addEventListener('click', () => this.flipHorizontally());
        }

        const flipVerticalBtn = document.getElementById('flip-vertical-btn');
        if (flipVerticalBtn) {
            flipVerticalBtn.addEventListener('click', () => this.flipVertically());
        }

        // Enhancement buttons
        const sharpenBtn = document.getElementById('sharpen-btn');
        if (sharpenBtn) {
            sharpenBtn.addEventListener('click', () => {
                this.applySharpenFilter();
            });
        }

        const edgeBtn = document.getElementById('edge-enhancement-btn');
        if (edgeBtn) {
            edgeBtn.addEventListener('click', () => {
                this.applyEdgeEnhancement();
            });
        }

        // Unit toggle button
        const unitsBtn = document.getElementById('toggle-units-btn');
        if (unitsBtn) {
            unitsBtn.addEventListener('click', () => {
                this.toggleMeasurementUnits();
            });
        }

        // ROI analysis button
        const roiBtn = document.getElementById('roi-btn');
        if (roiBtn) {
            roiBtn.addEventListener('click', () => {
                this.enableROITool('rectangle');
                this.setActiveToolButton(roiBtn);
            });
        }

        // Clear ROI button
        const clearROIBtn = document.getElementById('clear-roi-btn');
        if (clearROIBtn) {
            clearROIBtn.addEventListener('click', () => {
                this.clearROIs();
            });
        }

        // Histogram button
        const histogramBtn = document.getElementById('histogram-btn');
        if (histogramBtn) {
            histogramBtn.addEventListener('click', () => {
                this.generateHistogram();
            });
        }

        // DICOM metadata button
        const metadataBtn = document.getElementById('metadata-btn');
        if (metadataBtn) {
            metadataBtn.addEventListener('click', () => {
                this.showDICOMMetadata();
            });
        }

        // Crosshair button
        const crosshairBtn = document.getElementById('crosshair-adv-btn') || document.getElementById('crosshair-btn');
        if (crosshairBtn) {
            crosshairBtn.addEventListener('click', () => {
                this.activeTool = 'crosshair';
                this.setActiveToolButton(crosshairBtn);
                this.redrawCanvas();
            });
        }

        // Invert button
        const invertBtn = document.getElementById('invert-adv-btn') || document.getElementById('invert-btn');
        if (invertBtn) {
            invertBtn.addEventListener('click', () => {
                this.toggleInversion();
                invertBtn.classList.toggle('active', this.inverted);
            });
        }

        // Window/Level preset buttons
        const presetButtons = document.querySelectorAll('.preset-btn, [data-preset]');
        presetButtons.forEach(btn => {
            const preset = btn.getAttribute('data-preset');
            if (preset) {
                btn.addEventListener('click', () => {
                    this.setWindowPreset(preset);
                });
            }
        });

        // MPR and 3D buttons
        const mprBtn = document.getElementById('mpr-btn');
        if (mprBtn) {
            mprBtn.addEventListener('click', () => {
                this.toggleMPR();
            });
        }

        const volumeRenderBtn = document.getElementById('volume-render-btn');
        if (volumeRenderBtn) {
            volumeRenderBtn.addEventListener('click', () => {
                this.enableVolumeRendering();
            });
        }

        const mipBtn = document.getElementById('mip-btn');
        if (mipBtn) {
            mipBtn.addEventListener('click', () => {
                this.enableMIP();
            });
        }

        // Image navigation buttons
        const prevImageBtn = document.getElementById('prev-image-btn');
        if (prevImageBtn) {
            prevImageBtn.addEventListener('click', () => {
                this.previousImage();
            });
        }

        const nextImageBtn = document.getElementById('next-image-btn');
        if (nextImageBtn) {
            nextImageBtn.addEventListener('click', () => {
                this.nextImage();
            });
        }

        // Window/Level sliders
        const windowWidthSlider = document.getElementById('window-width-slider');
        if (windowWidthSlider) {
            windowWidthSlider.addEventListener('input', (e) => {
                this.windowWidth = parseInt(e.target.value);
                this.refreshCurrentImage();
                this.updateWindowLevelDisplay();
            });
        }

        const windowLevelSlider = document.getElementById('window-level-slider');
        if (windowLevelSlider) {
            windowLevelSlider.addEventListener('input', (e) => {
                this.windowLevel = parseInt(e.target.value);
                this.refreshCurrentImage();
                this.updateWindowLevelDisplay();
            });
        }

        // Contrast slider
        const contrastSlider = document.getElementById('contrast-slider');
        if (contrastSlider) {
            contrastSlider.addEventListener('input', (e) => {
                this.adjustContrast(parseFloat(e.target.value));
            });
        }

        // Density enhancement toggle
        const densityBtn = document.getElementById('density-enhancement-btn');
        if (densityBtn) {
            densityBtn.addEventListener('click', () => {
                this.toggleDensityEnhancement();
                densityBtn.classList.toggle('active', this.densityEnhancement);
            });
        }

        console.log('All tool buttons setup complete');
    }

    setActiveToolButton(activeBtn) {
        // Remove active class from all tool buttons
        const toolButtons = document.querySelectorAll('.tool-btn-advanced');
        toolButtons.forEach(btn => btn.classList.remove('active'));
        
        // Add active class to the selected button
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
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
        this.notyf.success('View reset to defaults');
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
        const folderInput = document.getElementById('folderInput');
        const browseFilesBtn = document.getElementById('browseFilesBtn');
        const browseFolderBtn = document.getElementById('browseFolderBtn');
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
            this.handleFileSelection(files);
        });
        
        // Folder input change handler
        if (folderInput) {
            folderInput.addEventListener('change', (e) => {
                const files = Array.from(e.target.files);
                this.handleFileSelection(files);
            });
        }
        
        // Browse files button
        if (browseFilesBtn) {
            browseFilesBtn.addEventListener('click', () => {
                fileInput.click();
            });
        }
        
        // Browse folder button
        if (browseFolderBtn) {
            browseFolderBtn.addEventListener('click', () => {
                if (folderInput) {
                    folderInput.click();
                }
            });
        }
        
        // Upload area click handler (default to files)
        uploadArea.addEventListener('click', (e) => {
            // Only trigger if not clicking on buttons
            if (!e.target.closest('button')) {
                fileInput.click();
            }
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
            this.handleFileSelection(files);
        });
        
        // Start upload button
        startUploadBtn.addEventListener('click', () => {
            this.startUpload();
        });
        
        // Mark as set up to prevent duplicates
        this.uploadHandlersSetup = true;
        console.log('Upload handlers setup complete');
    }
    
    handleFileSelection(files) {
        if (files.length === 0) return;
        
        // Filter for DICOM files and common medical image formats
        const validFiles = files.filter(file => {
            const name = file.name.toLowerCase();
            const validExtensions = ['.dcm', '.dicom', '.dic', '.img', '.ima'];
            const hasDicomExtension = validExtensions.some(ext => name.endsWith(ext));
            
            // Also accept files without extension (common in DICOM folders)
            const hasNoExtension = !name.includes('.');
            
            // Check MIME type for medical images
            const isMedicalImage = file.type.includes('dicom') || file.type.includes('medical');
            
            return hasDicomExtension || hasNoExtension || isMedicalImage;
        });
        
        if (validFiles.length === 0) {
            this.notyf.error('No valid DICOM files found. Please select .dcm, .dicom files or a CT scan folder.');
            return;
        }
        
        this.selectedFiles = validFiles;
        
        const startUploadBtn = document.getElementById('startUpload');
        const uploadStatus = document.getElementById('uploadStatus');
        
        if (startUploadBtn) {
            startUploadBtn.disabled = false;
        }
        
        if (uploadStatus) {
            uploadStatus.textContent = `${validFiles.length} DICOM file(s) selected`;
            if (validFiles.length !== files.length) {
                uploadStatus.textContent += ` (${files.length - validFiles.length} non-DICOM files filtered out)`;
            }
        }
        
        this.notyf.success(`Selected ${validFiles.length} DICOM files for upload`);
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
                    
                    // Load and display the first image
                    await this.loadImage(this.currentImage.id);
                    this.updateImageCounter();
                    
                    // Ensure the image is displayed by calling refreshCurrentImage directly
                    console.log('Forcing initial image display...');
                    await this.refreshCurrentImage();
                    
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
            console.log('Loading image:', imageId);
            
            // Set the current image
            this.currentImage = this.currentImages.find(img => img.id === imageId);
            if (!this.currentImage) {
                console.error('Image not found in current images');
                return;
            }
            
            // Always refresh the image display to ensure it's shown
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
            console.log('Updating patient info with data:', study);
            
            // Update main patient information display (advanced view)
            const patientNameAdv = document.getElementById('patient-name-adv');
            const patientIdAdv = document.getElementById('patient-id-adv');
            const patientDob = document.getElementById('patient-dob');
            const studyDateAdv = document.getElementById('study-date-adv');
            const studyDescriptionAdv = document.getElementById('study-description-adv');
            const modalityAdv = document.getElementById('modality-adv');
            const seriesCount = document.getElementById('series-count');
            const imageCountAdv = document.getElementById('image-count-adv');
            const institutionName = document.getElementById('institution-name');
            
            // Update quick header info
            const quickPatientName = document.getElementById('quick-patient-name');
            const quickPatientId = document.getElementById('quick-patient-id');
            const quickModality = document.getElementById('quick-modality');
            
            // Update study counter
            const studyCounter = document.getElementById('study-counter');

            // Populate advanced view fields
            if (patientNameAdv) patientNameAdv.textContent = study.patient_name || 'Unknown Patient';
            if (patientIdAdv) patientIdAdv.textContent = study.patient_id || 'Unknown ID';
            if (patientDob) patientDob.textContent = study.patient_birth_date || study.patient_dob || '-';
            if (studyDateAdv) studyDateAdv.textContent = study.study_date || '-';
            if (studyDescriptionAdv) studyDescriptionAdv.textContent = study.study_description || 'No description';
            if (modalityAdv) modalityAdv.textContent = study.modality || 'Unknown';
            if (seriesCount) seriesCount.textContent = study.series_count || '1';
            if (imageCountAdv) imageCountAdv.textContent = study.image_count || this.currentImages.length || '0';
            if (institutionName) institutionName.textContent = study.institution_name || 'Unknown Institution';
            
            // Populate quick header
            if (quickPatientName) quickPatientName.textContent = study.patient_name || 'Unknown';
            if (quickPatientId) quickPatientId.textContent = study.patient_id || 'Unknown';
            if (quickModality) quickModality.textContent = study.modality || 'Unknown';
            
            // Update study counter
            if (studyCounter) studyCounter.textContent = 'Study 1 of 1';

            console.log('Patient info successfully updated with all fields');
        } catch (error) {
            console.error('Error updating patient info:', error);
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
    
    // Tool management methods
    setActiveTool(tool) {
        console.log('Setting active tool:', tool);
        this.activeTool = tool;
        this.updateToolUI();
        
        // Update cursor style based on tool
        const cursor = this.getToolCursor(tool);
        this.canvas.style.cursor = cursor;
        
        // Use success method instead of info for compatibility
        this.notyf.success(`Active tool: ${tool}`);
    }
    
    getToolCursor(tool) {
        const cursors = {
            'windowing': 'crosshair',
            'pan': 'move',
            'zoom': 'zoom-in',
            'distance': 'crosshair',
            'angle': 'crosshair',
            'area': 'crosshair',
            'hu': 'crosshair',
            'crosshair': 'crosshair',
            'magnify': 'zoom-in'
        };
        return cursors[tool] || 'default';
    }
    
    updateToolUI() {
        // Remove active class from all tool buttons
        const toolButtons = document.querySelectorAll('.tool-btn-advanced');
        toolButtons.forEach(btn => btn.classList.remove('active'));
        
        // Add active class to current tool button
        const activeButton = document.querySelector(`#${this.activeTool}-adv-btn, #${this.activeTool}-btn, #measure-${this.activeTool}-btn`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
    }
    
    // Image manipulation methods
    rotateImage() {
        this.rotation = (this.rotation + 90) % 360;
        this.refreshCurrentImage();
        this.notyf.success(`Rotated to ${this.rotation}°`);
    }
    
    flipImage() {
        this.flipHorizontal = !this.flipHorizontal;
        this.refreshCurrentImage();
        this.notyf.success('Image flipped horizontally');
    }
    
    toggleInversion() {
        this.inverted = !this.inverted;
        this.refreshCurrentImage();
        this.notyf.success(this.inverted ? 'Image inverted' : 'Image normal');
    }
    
    toggleSharpen() {
        // Toggle sharpen filter
        this.sharpenEnabled = !this.sharpenEnabled;
        this.refreshCurrentImage();
        this.notyf.success(this.sharpenEnabled ? 'Sharpening enabled' : 'Sharpening disabled');
    }
    
    fitToWindow() {
        if (!this.currentImage) return;
        
        const containerRect = this.canvas.getBoundingClientRect();
        const imageAspect = this.currentImage.width / this.currentImage.height;
        const containerAspect = containerRect.width / containerRect.height;
        
        if (imageAspect > containerAspect) {
            this.zoomFactor = containerRect.width / this.currentImage.width;
        } else {
            this.zoomFactor = containerRect.height / this.currentImage.height;
        }
        
        this.panX = 0;
        this.panY = 0;
        this.refreshCurrentImage();
        this.notyf.success('Image fitted to window');
    }
    
    actualSize() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.refreshCurrentImage();
        this.notyf.success('Image at actual size (1:1)');
    }
    
    resetView() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.rotation = 0;
        this.flipHorizontal = false;
        this.flipVertical = false;
        this.inverted = false;
        this.refreshCurrentImage();
        this.notyf.success('View reset to defaults');
    }
    
    // Advanced imaging methods
    enableMPR() {
        console.log('Enabling MPR...');
        this.notyf.success('MPR (Multi-Planar Reconstruction) - Feature in development');
        // TODO: Implement MPR functionality
    }
    
    enableVolumeRendering() {
        console.log('Enabling Volume Rendering...');
        this.notyf.success('Volume Rendering - Feature in development');
        // TODO: Implement volume rendering
    }
    
    enableMIP() {
        console.log('Enabling MIP...');
        this.notyf.success('MIP (Maximum Intensity Projection) - Feature in development');
        // TODO: Implement MIP functionality
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

    // === ENHANCED NAVIGATION METHODS ===
    nextImage() {
        if (!this.currentImages || this.currentImages.length === 0) return;
        
        const newIndex = this.currentImageIndex + 1;
        if (newIndex < this.currentImages.length) {
            this.currentImageIndex = newIndex;
            this.currentImage = this.currentImages[this.currentImageIndex];
            this.loadImage(this.currentImage.id);
            this.updateImageCounter();
            this.updateThumbnailSelection();
        }
    }
    
    previousImage() {
        if (!this.currentImages || this.currentImages.length === 0) return;
        
        const newIndex = this.currentImageIndex - 1;
        if (newIndex >= 0) {
            this.currentImageIndex = newIndex;
            this.currentImage = this.currentImages[this.currentImageIndex];
            this.loadImage(this.currentImage.id);
            this.updateImageCounter();
            this.updateThumbnailSelection();
        }
    }
    
    goToImage(index) {
        if (!this.currentImages || this.currentImages.length === 0) {
            this.notyf.warning('No images loaded');
            return;
        }

        if (index >= 0 && index < this.currentImages.length) {
            this.currentImageIndex = index;
            this.loadCurrentImage();
            this.notyf.info(`Switched to image ${index + 1} of ${this.currentImages.length}`);
        }
    }

    async loadCurrentImage() {
        if (!this.currentImages || this.currentImageIndex >= this.currentImages.length) {
            return;
        }

        const imageData = this.currentImages[this.currentImageIndex];
        if (imageData && imageData.id) {
            this.currentImageId = imageData.id;
            await this.refreshCurrentImage();
            
            // Update MPR if enabled
            if (this.mprEnabled) {
                this.generateMPRSlices();
            }
            
            // Update image counter
            this.updateImageCounter();
        }
    }

    updateImageCounter() {
        const counter = document.getElementById('image-counter');
        if (counter && this.currentImages) {
            counter.textContent = `${this.currentImageIndex + 1} / ${this.currentImages.length}`;
        }

        // Update slice slider
        const sliceSlider = document.getElementById('slice-slider');
        if (sliceSlider) {
            sliceSlider.max = this.currentImages.length - 1;
            sliceSlider.value = this.currentImageIndex;
        }
    }

    // === VIEWPORT INFORMATION UPDATE ===
    
    updateViewportInfo() {
        // Update zoom level
        const zoomLevel = document.getElementById('zoom-level');
        if (zoomLevel) {
            zoomLevel.textContent = `${Math.round(this.zoomFactor * 100)}%`;
        }

        // Update window/level display
        this.updateWindowLevelDisplay();

        // Update image position
        const position = document.getElementById('image-position');
        if (position) {
            position.textContent = `Pan: (${Math.round(this.panX)}, ${Math.round(this.panY)})`;
        }

        // Update rotation
        const rotation = document.getElementById('image-rotation');
        if (rotation) {
            rotation.textContent = `${this.rotation}°`;
        }
    }

    updateWindowLevelDisplay() {
        const wwDisplay = document.getElementById('window-width-value') || document.getElementById('ww-value');
        if (wwDisplay) {
            wwDisplay.textContent = this.windowWidth;
        }

        const wlDisplay = document.getElementById('window-level-value') || document.getElementById('wl-value');
        if (wlDisplay) {
            wlDisplay.textContent = this.windowLevel;
        }

        // Update sliders
        const wwSlider = document.getElementById('window-width-slider');
        if (wwSlider) {
            wwSlider.value = this.windowWidth;
        }

        const wlSlider = document.getElementById('window-level-slider');
        if (wlSlider) {
            wlSlider.value = this.windowLevel;
        }
    }

    updateDebugPanel() {
        // Update debug information
        const debugCanvas = document.getElementById('debug-canvas');
        if (debugCanvas) {
            debugCanvas.textContent = `Canvas: ${this.canvas.width}x${this.canvas.height}`;
        }

        const debugImages = document.getElementById('debug-images');
        if (debugImages && this.currentImages) {
            debugImages.textContent = `Images: ${this.currentImages.length}`;
        }

        const debugTool = document.getElementById('debug-tool');
        if (debugTool) {
            debugTool.textContent = `Active Tool: ${this.activeTool}`;
        }
    }

    // === SERIES NAVIGATION METHODS ===
    async loadSeriesData() {
        try {
            console.log('Loading series data for study:', this.currentStudyId);
            
            const response = await fetch(`/viewer/api/studies/${this.currentStudyId}/series/`);
            if (response.ok) {
                const seriesData = await response.json();
                this.currentSeriesList = seriesData.series || [];
                this.populateSeriesSelector();
                console.log(`Loaded ${this.currentSeriesList.length} series`);
            } else {
                console.error('Failed to load series data:', response.status);
            }
        } catch (error) {
            console.error('Error loading series data:', error);
        }
    }
    
    populateSeriesSelector() {
        const seriesList = document.getElementById('series-list');
        if (!seriesList || !this.currentSeriesList) return;
        
        seriesList.innerHTML = '';
        
        this.currentSeriesList.forEach((series, index) => {
            const seriesItem = document.createElement('div');
            seriesItem.className = 'series-item';
            if (series.id === this.currentSeries?.id) {
                seriesItem.classList.add('active');
            }
            
            seriesItem.innerHTML = `
                <div class="series-info">
                    <div class="series-title">Series ${series.series_number || index + 1}</div>
                    <div class="series-description">${series.series_description || 'No description'}</div>
                    <div class="series-details">
                        <span class="modality">${series.modality || 'Unknown'}</span>
                        <span class="image-count">${series.image_count || 0} images</span>
                    </div>
                </div>
            `;
            
            seriesItem.addEventListener('click', () => {
                this.loadSeries(series);
            });
            
            seriesList.appendChild(seriesItem);
        });
    }
    
    async loadSeries(series) {
        try {
            console.log('Loading series:', series);
            this.currentSeries = series;
            
            // Update active series in selector
            const seriesItems = document.querySelectorAll('.series-item');
            seriesItems.forEach(item => item.classList.remove('active'));
            
            const activeItem = Array.from(seriesItems).find(item => 
                item.textContent.includes(`Series ${series.series_number}`)
            );
            if (activeItem) {
                activeItem.classList.add('active');
            }
            
            // Load series images
            await this.loadSeriesImages(series.id);
            
        } catch (error) {
            console.error('Error loading series:', error);
            this.notyf.error('Failed to load series');
        }
    }
    
    async loadSeriesImages(seriesId) {
        try {
            console.log('Loading images for series:', seriesId);
            
            const response = await fetch(`/viewer/api/series/${seriesId}/images/`);
            if (response.ok) {
                const imageData = await response.json();
                this.currentImages = imageData.images || [];
                this.currentImageIndex = 0;
                
                if (this.currentImages.length > 0) {
                    this.currentImage = this.currentImages[0];
                    this.loadImage(this.currentImage.id);
                    this.updateImageCounter();
                    this.populateThumbnails();
                }
                
                console.log(`Loaded ${this.currentImages.length} images`);
            } else {
                console.error('Failed to load series images:', response.status);
            }
        } catch (error) {
            console.error('Error loading series images:', error);
        }
    }

    populateThumbnails() {
        const thumbnailContainer = document.getElementById('thumbnail-list');
        if (!thumbnailContainer || !this.currentImages) return;
        
        thumbnailContainer.innerHTML = '';
        
        this.currentImages.forEach((image, index) => {
            const thumbnail = document.createElement('div');
            thumbnail.className = 'thumbnail-item';
            if (index === this.currentImageIndex) {
                thumbnail.classList.add('active');
            }
            
            thumbnail.innerHTML = `
                <img src="/viewer/api/images/${image.id}/thumbnail/" 
                     alt="Image ${index + 1}" 
                     loading="lazy"
                     onerror="this.style.display='none'">
                <div class="thumbnail-info">
                    <span class="image-number">${index + 1}</span>
                </div>
            `;
            
            thumbnail.addEventListener('click', () => {
                this.goToImage(index);
            });
            
            thumbnailContainer.appendChild(thumbnail);
        });
    }
    
    updateThumbnailSelection() {
        const thumbnails = document.querySelectorAll('.thumbnail-item');
        thumbnails.forEach((thumb, index) => {
            thumb.classList.toggle('active', index === this.currentImageIndex);
        });
    }
    
    updateImageCounter() {
        const counter = document.getElementById('image-counter');
        if (counter && this.currentImages) {
            counter.textContent = `${this.currentImageIndex + 1} / ${this.currentImages.length}`;
        }
    }

    // === WINDOW/LEVEL PRESETS ===
    applyPreset(presetName) {
        const presets = {
            'soft-tissue': { windowWidth: 400, windowCenter: 50 },
            'lung': { windowWidth: 1500, windowCenter: -600 },
            'bone': { windowWidth: 1000, windowCenter: 400 },
            'brain': { windowWidth: 100, windowCenter: 50 },
            'abdomen': { windowWidth: 350, windowCenter: 50 }
        };
        
        const preset = presets[presetName];
        if (preset) {
            this.windowWidth = preset.windowWidth;
            this.windowCenter = preset.windowCenter;
            this.applyWindowLevel();
            this.updateWindowLevelDisplay();
        }
    }

    // === MAGNIFICATION TOOLS ===
    enableMagnification() {
        this.magnificationEnabled = true;
        this.canvas.style.cursor = 'zoom-in';
        this.activeTool = 'magnify';
        this.notyf.success('Magnification tool activated');
    }

    disableMagnification() {
        this.magnificationEnabled = false;
        this.canvas.style.cursor = 'default';
        this.activeTool = 'windowing';
        this.redrawCanvas();
    }

    drawMagnifier(mouseX, mouseY) {
        if (!this.magnificationEnabled || !this.currentImage) return;

        const magnifierCanvas = document.createElement('canvas');
        const magnifierCtx = magnifierCanvas.getContext('2d');
        const radius = this.magnificationRadius;
        
        magnifierCanvas.width = radius * 2;
        magnifierCanvas.height = radius * 2;

        // Create circular clipping path
        magnifierCtx.beginPath();
        magnifierCtx.arc(radius, radius, radius - 2, 0, 2 * Math.PI);
        magnifierCtx.clip();

        // Draw magnified portion of the main image
        const sourceX = mouseX - radius / this.magnificationLevel;
        const sourceY = mouseY - radius / this.magnificationLevel;
        const sourceWidth = (radius * 2) / this.magnificationLevel;
        const sourceHeight = (radius * 2) / this.magnificationLevel;

        magnifierCtx.drawImage(
            this.canvas,
            sourceX, sourceY, sourceWidth, sourceHeight,
            0, 0, radius * 2, radius * 2
        );

        // Draw magnifier border
        magnifierCtx.globalCompositeOperation = 'source-over';
        magnifierCtx.beginPath();
        magnifierCtx.arc(radius, radius, radius - 1, 0, 2 * Math.PI);
        magnifierCtx.strokeStyle = '#00ff88';
        magnifierCtx.lineWidth = 2;
        magnifierCtx.stroke();

        // Draw crosshairs
        magnifierCtx.beginPath();
        magnifierCtx.moveTo(radius - 10, radius);
        magnifierCtx.lineTo(radius + 10, radius);
        magnifierCtx.moveTo(radius, radius - 10);
        magnifierCtx.lineTo(radius, radius + 10);
        magnifierCtx.strokeStyle = '#ff0000';
        magnifierCtx.lineWidth = 1;
        magnifierCtx.stroke();

        // Draw the magnifier on main canvas
        this.ctx.drawImage(magnifierCanvas, mouseX - radius, mouseY - radius);
    }

    // === MEASUREMENT TOOLS ===
    enableMeasurementTool(type = 'distance') {
        this.activeTool = `measure_${type}`;
        this.canvas.style.cursor = 'crosshair';
        this.notyf.info(`${type.charAt(0).toUpperCase() + type.slice(1)} measurement tool activated`);
    }

    addMeasurement(startPoint, endPoint, type = 'distance') {
        const measurement = {
            id: Date.now(),
            type: type,
            start: startPoint,
            end: endPoint,
            value: 0,
            unit: this.measurementUnits
        };

        // Calculate measurement based on type
        switch (type) {
            case 'distance':
                measurement.value = this.calculateDistance(startPoint, endPoint);
                break;
            case 'area':
                measurement.value = this.calculateArea(startPoint, endPoint);
                measurement.unit = this.measurementUnits === 'mm' ? 'mm²' : 'cm²';
                break;
            case 'angle':
                measurement.value = this.calculateAngle(startPoint, endPoint);
                measurement.unit = '°';
                break;
        }

        this.measurements.push(measurement);
        this.updateMeasurementsPanel();
        this.redrawCanvas();
        
        this.notyf.success(`${type} measurement added: ${measurement.value.toFixed(2)} ${measurement.unit}`);
    }

    calculateDistance(start, end) {
        const pixelDistance = Math.sqrt(
            Math.pow(end.x - start.x, 2) + Math.pow(end.y - start.y, 2)
        );
        
        // Convert to real-world units using pixel spacing
        const realDistance = pixelDistance * this.pixelSpacing.x * this.calibrationFactor;
        
        // Convert to appropriate units
        if (this.measurementUnits === 'cm') {
            return realDistance / 10; // mm to cm
        }
        return realDistance; // mm
    }

    calculateArea(start, end) {
        const width = Math.abs(end.x - start.x) * this.pixelSpacing.x * this.calibrationFactor;
        const height = Math.abs(end.y - start.y) * this.pixelSpacing.y * this.calibrationFactor;
        const area = width * height;
        
        if (this.measurementUnits === 'cm') {
            return area / 100; // mm² to cm²
        }
        return area; // mm²
    }

    calculateAngle(start, end) {
        const deltaX = end.x - start.x;
        const deltaY = end.y - start.y;
        return Math.abs(Math.atan2(deltaY, deltaX) * (180 / Math.PI));
    }

    drawMeasurements() {
        this.measurements.forEach(measurement => {
            this.ctx.save();
            this.ctx.strokeStyle = '#00ff88';
            this.ctx.fillStyle = '#00ff88';
            this.ctx.lineWidth = 2;
            this.ctx.font = '14px Arial';

            const start = this.imageToCanvasCoords(measurement.start.x, measurement.start.y);
            const end = this.imageToCanvasCoords(measurement.end.x, measurement.end.y);

            // Draw measurement line
            this.ctx.beginPath();
            this.ctx.moveTo(start.x, start.y);
            this.ctx.lineTo(end.x, end.y);
            this.ctx.stroke();

            // Draw endpoints
            this.ctx.beginPath();
            this.ctx.arc(start.x, start.y, 3, 0, 2 * Math.PI);
            this.ctx.arc(end.x, end.y, 3, 0, 2 * Math.PI);
            this.ctx.fill();

            // Draw measurement text
            const midX = (start.x + end.x) / 2;
            const midY = (start.y + end.y) / 2;
            const text = `${measurement.value.toFixed(2)} ${measurement.unit}`;
            
            this.ctx.fillStyle = '#000000';
            this.ctx.fillRect(midX - 30, midY - 10, 60, 20);
            this.ctx.fillStyle = '#00ff88';
            this.ctx.fillText(text, midX - 25, midY + 5);

            this.ctx.restore();
        });
    }

    clearMeasurements() {
        this.measurements = [];
        this.updateMeasurementsPanel();
        this.redrawCanvas();
        this.notyf.success('All measurements cleared');
    }

    updateMeasurementsPanel() {
        const panel = document.getElementById('measurements-list');
        if (!panel) return;

        panel.innerHTML = '';
        this.measurements.forEach((measurement, index) => {
            const item = document.createElement('div');
            item.className = 'measurement-item';
            item.innerHTML = `
                <div class="measurement-info">
                    <strong>${measurement.type.charAt(0).toUpperCase() + measurement.type.slice(1)} ${index + 1}</strong>
                    <span>${measurement.value.toFixed(2)} ${measurement.unit}</span>
                </div>
                <button onclick="window.fixedViewer.removeMeasurement(${measurement.id})" class="btn-remove">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            panel.appendChild(item);
        });
    }

    removeMeasurement(id) {
        this.measurements = this.measurements.filter(m => m.id !== id);
        this.updateMeasurementsPanel();
        this.redrawCanvas();
    }

    // === CALIBRATION TOOLS ===
    calibratePixelSpacing(knownDistance, measuredPixels) {
        this.calibrationFactor = knownDistance / measuredPixels;
        this.notyf.success(`Calibration updated: ${this.calibrationFactor.toFixed(4)} mm/pixel`);
    }

    setPixelSpacing(spacingX, spacingY) {
        this.pixelSpacing.x = spacingX;
        this.pixelSpacing.y = spacingY;
        this.notyf.info(`Pixel spacing set: ${spacingX}mm × ${spacingY}mm`);
    }

    toggleMeasurementUnits() {
        this.measurementUnits = this.measurementUnits === 'mm' ? 'cm' : 'mm';
        this.updateMeasurementsPanel();
        this.notyf.info(`Measurement units: ${this.measurementUnits}`);
    }

    // === ENHANCED IMAGE PROCESSING ===
    applySharpenFilter() {
        if (!this.currentImage) return;

        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;

        // Sharpening kernel
        const kernel = [
            0, -1, 0,
            -1, 5, -1,
            0, -1, 0
        ];

        const newData = new Uint8ClampedArray(data);

        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                for (let c = 0; c < 3; c++) {
                    let sum = 0;
                    for (let ky = -1; ky <= 1; ky++) {
                        for (let kx = -1; kx <= 1; kx++) {
                            const pos = ((y + ky) * width + (x + kx)) * 4 + c;
                            sum += data[pos] * kernel[(ky + 1) * 3 + (kx + 1)];
                        }
                    }
                    newData[(y * width + x) * 4 + c] = Math.max(0, Math.min(255, sum));
                }
            }
        }

        imageData.data.set(newData);
        this.ctx.putImageData(imageData, 0, 0);
        this.notyf.success('Sharpening filter applied');
    }

    applyEdgeEnhancement() {
        if (!this.currentImage) return;

        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;

        // Edge detection kernel (Sobel)
        const sobelX = [-1, 0, 1, -2, 0, 2, -1, 0, 1];
        const sobelY = [-1, -2, -1, 0, 0, 0, 1, 2, 1];

        const newData = new Uint8ClampedArray(data);

        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                let sumX = 0, sumY = 0;
                
                for (let ky = -1; ky <= 1; ky++) {
                    for (let kx = -1; kx <= 1; kx++) {
                        const pos = ((y + ky) * width + (x + kx)) * 4;
                        const gray = (data[pos] + data[pos + 1] + data[pos + 2]) / 3;
                        const kernelIndex = (ky + 1) * 3 + (kx + 1);
                        sumX += gray * sobelX[kernelIndex];
                        sumY += gray * sobelY[kernelIndex];
                    }
                }

                const magnitude = Math.sqrt(sumX * sumX + sumY * sumY);
                const enhanced = Math.min(255, magnitude);
                
                const pos = (y * width + x) * 4;
                newData[pos] = enhanced;
                newData[pos + 1] = enhanced;
                newData[pos + 2] = enhanced;
                newData[pos + 3] = data[pos + 3];
            }
        }

        imageData.data.set(newData);
        this.ctx.putImageData(imageData, 0, 0);
        this.notyf.success('Edge enhancement applied');
    }

    // === ANNOTATION TOOLS ===
    addTextAnnotation(x, y, text) {
        const annotation = {
            id: Date.now(),
            type: 'text',
            x: x,
            y: y,
            text: text,
            color: '#ffff00'
        };

        if (!this.annotations) this.annotations = [];
        this.annotations.push(annotation);
        this.redrawCanvas();
        this.notyf.success('Text annotation added');
    }

    drawAnnotations() {
        if (!this.annotations) return;

        this.annotations.forEach(annotation => {
            this.ctx.save();
            this.ctx.fillStyle = annotation.color;
            this.ctx.font = '16px Arial';
            this.ctx.strokeStyle = '#000000';
            this.ctx.lineWidth = 3;

            const canvasCoords = this.imageToCanvasCoords(annotation.x, annotation.y);
            
            // Draw text with outline
            this.ctx.strokeText(annotation.text, canvasCoords.x, canvasCoords.y);
            this.ctx.fillText(annotation.text, canvasCoords.x, canvasCoords.y);
            
            this.ctx.restore();
        });
    }

    // === COORDINATE CONVERSION ===
    imageToCanvasCoords(imageX, imageY) {
        if (!this.currentImage) return { x: imageX, y: imageY };

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
        if (!this.currentImage) return { x: canvasX, y: canvasY };

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

    // === ENHANCED CANVAS REDRAW ===
    redrawCanvas() {
        if (!this.currentImage || !this.canvas) return;

        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw main image
        this.displayProcessedImage();

        // Draw overlays
        this.drawMeasurements();
        this.drawAnnotations();

        // Draw crosshairs if enabled
        if (this.activeTool === 'crosshair') {
            this.drawCrosshairs();
        }
    }

    drawCrosshairs() {
        this.ctx.save();
        this.ctx.strokeStyle = '#ff0000';
        this.ctx.lineWidth = 1;
        this.ctx.setLineDash([5, 5]);

        // Vertical line
        this.ctx.beginPath();
        this.ctx.moveTo(this.canvas.width / 2, 0);
        this.ctx.lineTo(this.canvas.width / 2, this.canvas.height);
        this.ctx.stroke();

        // Horizontal line
        this.ctx.beginPath();
        this.ctx.moveTo(0, this.canvas.height / 2);
        this.ctx.lineTo(this.canvas.width, this.canvas.height / 2);
        this.ctx.stroke();

        this.ctx.restore();
    }

    // === ROI ANALYSIS TOOLS ===
    enableROITool(type = 'rectangle') {
        this.activeTool = `roi_${type}`;
        this.canvas.style.cursor = 'crosshair';
        this.notyf.info(`ROI ${type} tool activated`);
    }

    addROI(startPoint, endPoint, type = 'rectangle') {
        const roi = {
            id: Date.now(),
            type: type,
            start: startPoint,
            end: endPoint,
            statistics: null
        };

        // Calculate ROI statistics
        roi.statistics = this.calculateROIStatistics(roi);
        
        if (!this.rois) this.rois = [];
        this.rois.push(roi);
        this.updateROIPanel();
        this.redrawCanvas();
        
        this.notyf.success(`ROI added - Mean: ${roi.statistics.mean.toFixed(1)} HU`);
    }

    calculateROIStatistics(roi) {
        if (!this.currentImage) return { mean: 0, std: 0, min: 0, max: 0, area: 0 };

        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        
        const startCanvas = this.imageToCanvasCoords(roi.start.x, roi.start.y);
        const endCanvas = this.imageToCanvasCoords(roi.end.x, roi.end.y);
        
        const minX = Math.min(startCanvas.x, endCanvas.x);
        const maxX = Math.max(startCanvas.x, endCanvas.x);
        const minY = Math.min(startCanvas.y, endCanvas.y);
        const maxY = Math.max(startCanvas.y, endCanvas.y);
        
        let pixels = [];
        
        for (let y = Math.floor(minY); y < Math.ceil(maxY); y++) {
            for (let x = Math.floor(minX); x < Math.ceil(maxX); x++) {
                if (x >= 0 && x < imageData.width && y >= 0 && y < imageData.height) {
                    const index = (y * imageData.width + x) * 4;
                    // Convert RGB to grayscale and approximate HU values
                    const gray = (data[index] + data[index + 1] + data[index + 2]) / 3;
                    const hu = (gray - 128) * 4; // Rough HU approximation
                    pixels.push(hu);
                }
            }
        }
        
        if (pixels.length === 0) return { mean: 0, std: 0, min: 0, max: 0, area: 0 };
        
        const mean = pixels.reduce((a, b) => a + b, 0) / pixels.length;
        const variance = pixels.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / pixels.length;
        const std = Math.sqrt(variance);
        const min = Math.min(...pixels);
        const max = Math.max(...pixels);
        const area = Math.abs(roi.end.x - roi.start.x) * Math.abs(roi.end.y - roi.start.y) * 
                    this.pixelSpacing.x * this.pixelSpacing.y; // in mm²
        
        return { mean, std, min, max, area, pixelCount: pixels.length };
    }

    drawROIs() {
        if (!this.rois) return;

        this.rois.forEach((roi, index) => {
            this.ctx.save();
            this.ctx.strokeStyle = '#ff6b35';
            this.ctx.fillStyle = 'rgba(255, 107, 53, 0.2)';
            this.ctx.lineWidth = 2;

            const start = this.imageToCanvasCoords(roi.start.x, roi.start.y);
            const end = this.imageToCanvasCoords(roi.end.x, roi.end.y);

            const width = end.x - start.x;
            const height = end.y - start.y;

            // Draw ROI rectangle
            this.ctx.fillRect(start.x, start.y, width, height);
            this.ctx.strokeRect(start.x, start.y, width, height);

            // Draw ROI label
            this.ctx.fillStyle = '#ff6b35';
            this.ctx.font = 'bold 12px Arial';
            this.ctx.fillText(`ROI ${index + 1}`, start.x + 5, start.y - 5);

            // Draw statistics if available
            if (roi.statistics) {
                const stats = [
                    `Mean: ${roi.statistics.mean.toFixed(1)} HU`,
                    `Std: ${roi.statistics.std.toFixed(1)}`,
                    `Area: ${roi.statistics.area.toFixed(1)} mm²`
                ];
                
                stats.forEach((stat, i) => {
                    this.ctx.fillText(stat, start.x + 5, start.y + 15 + (i * 15));
                });
            }

            this.ctx.restore();
        });
    }

    updateROIPanel() {
        const panel = document.getElementById('roi-list');
        if (!panel || !this.rois) return;

        panel.innerHTML = '';
        this.rois.forEach((roi, index) => {
            const item = document.createElement('div');
            item.className = 'roi-item';
            item.innerHTML = `
                <div class="roi-info">
                    <strong>ROI ${index + 1}</strong>
                    <div class="roi-stats">
                        <span>Mean: ${roi.statistics.mean.toFixed(1)} HU</span>
                        <span>Std: ${roi.statistics.std.toFixed(1)}</span>
                        <span>Area: ${roi.statistics.area.toFixed(1)} mm²</span>
                        <span>Pixels: ${roi.statistics.pixelCount}</span>
                    </div>
                </div>
                <button onclick="window.fixedViewer.removeROI(${roi.id})" class="btn-remove">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            panel.appendChild(item);
        });
    }

    removeROI(id) {
        if (!this.rois) return;
        this.rois = this.rois.filter(r => r.id !== id);
        this.updateROIPanel();
        this.redrawCanvas();
    }

    clearROIs() {
        this.rois = [];
        this.updateROIPanel();
        this.redrawCanvas();
        this.notyf.success('All ROIs cleared');
    }

    // === HISTOGRAM ANALYSIS ===
    generateHistogram() {
        if (!this.currentImage) {
            this.notyf.error('No image loaded for histogram analysis');
            return;
        }

        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        const histogram = new Array(256).fill(0);
        
        // Count pixel intensities
        for (let i = 0; i < data.length; i += 4) {
            const gray = Math.floor((data[i] + data[i + 1] + data[i + 2]) / 3);
            histogram[gray]++;
        }
        
        this.displayHistogram(histogram);
    }

    displayHistogram(histogram) {
        const modal = this.createHistogramModal();
        const canvas = modal.querySelector('#histogram-canvas');
        const ctx = canvas.getContext('2d');
        
        // Set canvas size
        canvas.width = 400;
        canvas.height = 200;
        
        // Clear canvas
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Find max value for scaling
        const maxCount = Math.max(...histogram);
        
        // Draw histogram bars
        ctx.fillStyle = '#00ff88';
        const barWidth = canvas.width / histogram.length;
        
        histogram.forEach((count, intensity) => {
            const barHeight = (count / maxCount) * canvas.height;
            const x = intensity * barWidth;
            const y = canvas.height - barHeight;
            
            ctx.fillRect(x, y, barWidth - 1, barHeight);
        });
        
        // Draw labels
        ctx.fillStyle = '#ffffff';
        ctx.font = '12px Arial';
        ctx.fillText('0', 5, canvas.height - 5);
        ctx.fillText('255', canvas.width - 25, canvas.height - 5);
        ctx.fillText('Intensity', canvas.width / 2 - 25, canvas.height - 5);
        
        // Calculate statistics
        this.calculateHistogramStatistics(histogram, modal);
        
        // Show modal
        modal.style.display = 'block';
    }

    createHistogramModal() {
        let modal = document.getElementById('histogram-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'histogram-modal';
            modal.innerHTML = `
                <div class="modal-content" style="background: #1a1a1a; color: white; padding: 20px; border-radius: 8px; max-width: 500px; margin: 100px auto;">
                    <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3>Image Histogram</h3>
                        <button onclick="this.closest('.modal').style.display='none'" style="background: none; border: none; color: white; font-size: 20px; cursor: pointer;">×</button>
                    </div>
                    <canvas id="histogram-canvas" style="border: 1px solid #666; width: 100%;"></canvas>
                    <div id="histogram-stats" style="margin-top: 15px; font-size: 14px;"></div>
                </div>
            `;
            modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; display: none;';
            document.body.appendChild(modal);
        }
        return modal;
    }

    calculateHistogramStatistics(histogram, modal) {
        const totalPixels = histogram.reduce((a, b) => a + b, 0);
        let mean = 0;
        let weightedSum = 0;
        
        histogram.forEach((count, intensity) => {
            weightedSum += intensity * count;
        });
        mean = weightedSum / totalPixels;
        
        // Calculate standard deviation
        let variance = 0;
        histogram.forEach((count, intensity) => {
            variance += count * Math.pow(intensity - mean, 2);
        });
        variance /= totalPixels;
        const std = Math.sqrt(variance);
        
        // Find min and max non-zero values
        let min = histogram.findIndex(count => count > 0);
        let max = histogram.length - 1 - histogram.slice().reverse().findIndex(count => count > 0);
        
        const statsDiv = modal.querySelector('#histogram-stats');
        statsDiv.innerHTML = `
            <div><strong>Statistics:</strong></div>
            <div>Mean: ${mean.toFixed(2)}</div>
            <div>Std Dev: ${std.toFixed(2)}</div>
            <div>Min: ${min}</div>
            <div>Max: ${max}</div>
            <div>Total Pixels: ${totalPixels.toLocaleString()}</div>
        `;
    }

    // === DICOM METADATA VIEWER ===
    showDICOMMetadata() {
        if (!this.currentImage) {
            this.notyf.error('No image loaded');
            return;
        }

        // Get metadata from current image or fetch from server
        this.fetchDICOMMetadata(this.currentImage.id);
    }

    async fetchDICOMMetadata(imageId) {
        try {
            const response = await fetch(`/viewer/api/images/${imageId}/metadata/`);
            const metadata = await response.json();
            this.displayDICOMMetadata(metadata);
        } catch (error) {
            console.error('Error fetching DICOM metadata:', error);
            // Fallback to basic metadata if available
            const basicMetadata = this.getBasicMetadata();
            this.displayDICOMMetadata(basicMetadata);
        }
    }

    getBasicMetadata() {
        const img = this.currentImages[this.currentImageIndex];
        return {
            'Patient Name': img.patient_name || 'Unknown',
            'Patient ID': img.patient_id || 'Unknown',
            'Study Date': img.study_date || 'Unknown',
            'Study Description': img.study_description || 'Unknown',
            'Series Description': img.series_description || 'Unknown',
            'Modality': img.modality || 'Unknown',
            'Image Dimensions': `${img.columns || 0} × ${img.rows || 0}`,
            'Pixel Spacing': `${img.pixel_spacing_x || 1.0} × ${img.pixel_spacing_y || 1.0} mm`,
            'Slice Thickness': `${img.slice_thickness || 'Unknown'} mm`,
            'Window Width': img.window_width || 'Unknown',
            'Window Center': img.window_center || 'Unknown',
            'Institution': img.institution_name || 'Unknown'
        };
    }

    displayDICOMMetadata(metadata) {
        const modal = this.createMetadataModal();
        const content = modal.querySelector('#metadata-content');
        
        let html = '<table style="width: 100%; border-collapse: collapse;">';
        html += '<tr style="background: #333;"><th style="padding: 8px; border: 1px solid #666;">Tag</th><th style="padding: 8px; border: 1px solid #666;">Value</th></tr>';
        
        Object.entries(metadata).forEach(([tag, value]) => {
            html += `<tr><td style="padding: 8px; border: 1px solid #666; font-weight: bold;">${tag}</td>`;
            html += `<td style="padding: 8px; border: 1px solid #666;">${value}</td></tr>`;
        });
        
        html += '</table>';
        content.innerHTML = html;
        modal.style.display = 'block';
    }

    createMetadataModal() {
        let modal = document.getElementById('metadata-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'metadata-modal';
            modal.innerHTML = `
                <div class="modal-content" style="background: #1a1a1a; color: white; padding: 20px; border-radius: 8px; max-width: 600px; max-height: 80vh; overflow-y: auto; margin: 50px auto;">
                    <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3>DICOM Metadata</h3>
                        <button onclick="this.closest('.modal').style.display='none'" style="background: none; border: none; color: white; font-size: 20px; cursor: pointer;">×</button>
                    </div>
                    <div id="metadata-content"></div>
                </div>
            `;
            modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; display: none;';
            document.body.appendChild(modal);
        }
        return modal;
    }

    // === ENHANCED REDRAW WITH ALL OVERLAYS ===
    redrawCanvas() {
        if (!this.currentImage || !this.canvas) return;

        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw main image
        this.displayProcessedImage();

        // Draw all overlays
        this.drawMeasurements();
        this.drawAnnotations();
        this.drawROIs();

        // Draw crosshairs if enabled
        if (this.activeTool === 'crosshair') {
            this.drawCrosshairs();
        }
    }
}

// Initialize the fixed viewer when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const studyId = urlParams.get('study_id');
    
    window.fixedDicomViewer = new FixedDicomViewer(studyId);
});
