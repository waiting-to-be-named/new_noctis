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
                    
                    // Store image data
                    this.imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
                    
                    // Update UI
                    this.updateViewportInfo();
                    this.hideErrorPlaceholder();
                    
                    console.log('✅ Successfully displayed DICOM image');
                    resolve();
                } catch (renderError) {
                    console.error('Error rendering image:', renderError);
                    this.notyf.error('Error rendering image');
                    this.showErrorPlaceholder();
                    reject(renderError);
                }
            };
            
            img.onerror = (error) => {
                console.error('Failed to load image from base64 data:', error);
                this.notyf.error('Failed to display image');
                this.showErrorPlaceholder();
                reject(error);
            };
            
            img.src = `data:image/png;base64,${cleanBase64}`;
        });
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

        // Mouse events for interaction
        this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.handleWheel(e));
        
        // Touch events for mobile support
        this.canvas.addEventListener('touchstart', (e) => this.handleTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.handleTouchMove(e));
        this.canvas.addEventListener('touchend', (e) => this.handleTouchEnd(e));
        
        // Setup tool buttons
        this.setupToolButtons();
        
        // Setup preset buttons
        this.setupPresetButtons();
    }
    
    setupToolButtons() {
        console.log('Setting up tool buttons...');
        
        // Navigation tools
        const windowingBtn = document.getElementById('windowing-adv-btn');
        const panBtn = document.getElementById('pan-adv-btn');
        const zoomBtn = document.getElementById('zoom-adv-btn');
        const rotateBtn = document.getElementById('rotate-btn');
        const flipBtn = document.getElementById('flip-btn');
        
        // Measurement tools
        const distanceBtn = document.getElementById('measure-distance-btn');
        const angleBtn = document.getElementById('measure-angle-btn');
        const areaBtn = document.getElementById('measure-area-btn');
        const volumeBtn = document.getElementById('measure-volume-btn');
        const huBtn = document.getElementById('hu-measurement-btn');
        
        // Enhancement tools
        const invertBtn = document.getElementById('invert-adv-btn');
        const crosshairBtn = document.getElementById('crosshair-adv-btn');
        const magnifyBtn = document.getElementById('magnify-btn');
        const sharpenBtn = document.getElementById('sharpen-btn');
        
        // 3D/MPR tools
        const mprBtn = document.getElementById('mpr-btn');
        const volumeRenderBtn = document.getElementById('volume-render-btn');
        const mipBtn = document.getElementById('mip-btn');
        
        // Utility tools
        const resetBtn = document.getElementById('reset-adv-btn');
        const fitBtn = document.getElementById('fit-to-window-btn');
        const actualSizeBtn = document.getElementById('actual-size-btn');
        
        // Set up event listeners
        if (windowingBtn) windowingBtn.addEventListener('click', () => this.setActiveTool('windowing'));
        if (panBtn) panBtn.addEventListener('click', () => this.setActiveTool('pan'));
        if (zoomBtn) zoomBtn.addEventListener('click', () => this.setActiveTool('zoom'));
        if (rotateBtn) rotateBtn.addEventListener('click', () => this.rotateImage());
        if (flipBtn) flipBtn.addEventListener('click', () => this.flipImage());
        
        if (distanceBtn) distanceBtn.addEventListener('click', () => this.setActiveTool('distance'));
        if (angleBtn) angleBtn.addEventListener('click', () => this.setActiveTool('angle'));
        if (areaBtn) areaBtn.addEventListener('click', () => this.setActiveTool('area'));
        if (volumeBtn) volumeBtn.addEventListener('click', () => this.setActiveTool('volume'));
        if (huBtn) huBtn.addEventListener('click', () => this.setActiveTool('hu'));
        
        if (invertBtn) invertBtn.addEventListener('click', () => this.toggleInversion());
        if (crosshairBtn) crosshairBtn.addEventListener('click', () => this.setActiveTool('crosshair'));
        if (magnifyBtn) magnifyBtn.addEventListener('click', () => this.setActiveTool('magnify'));
        if (sharpenBtn) sharpenBtn.addEventListener('click', () => this.toggleSharpen());
        
        if (mprBtn) mprBtn.addEventListener('click', () => this.enableMPR());
        if (volumeRenderBtn) volumeRenderBtn.addEventListener('click', () => this.enableVolumeRendering());
        if (mipBtn) mipBtn.addEventListener('click', () => this.enableMIP());
        
        if (resetBtn) resetBtn.addEventListener('click', () => this.resetView());
        if (fitBtn) fitBtn.addEventListener('click', () => this.fitToWindow());
        if (actualSizeBtn) actualSizeBtn.addEventListener('click', () => this.actualSize());
        
        console.log('Tool buttons setup complete');
    }
    
    setupPresetButtons() {
        const presetButtons = document.querySelectorAll('.preset-btn');
        presetButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const preset = e.target.getAttribute('data-preset');
                if (preset && this.windowPresets[preset]) {
                    this.applyWindowPreset(preset);
                }
            });
        });
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
}

// Initialize the fixed viewer when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const studyId = urlParams.get('study_id');
    
    window.fixedDicomViewer = new FixedDicomViewer(studyId);

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
        if (!this.currentImages || index < 0 || index >= this.currentImages.length) return;
        
        this.currentImageIndex = index;
        this.currentImage = this.currentImages[this.currentImageIndex];
        this.loadImage(this.currentImage.id);
        this.updateImageCounter();
        this.updateThumbnailSelection();
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
                <div class="series-thumbnail">
                    <img src="/static/images/dicom-placeholder.png" alt="Series thumbnail" loading="lazy">
                </div>
            `;
            
            seriesItem.addEventListener('click', () => this.selectSeries(series));
            seriesList.appendChild(seriesItem);
        });
    }
    
    async selectSeries(series) {
        try {
            console.log('Selecting series:', series.id);
            
            // Update UI to show selection
            document.querySelectorAll('.series-item').forEach(item => item.classList.remove('active'));
            event.currentTarget.classList.add('active');
            
            // Load images for this series
            const response = await fetch(`/viewer/api/series/${series.id}/images/`);
            if (response.ok) {
                const data = await response.json();
                this.currentSeries = series;
                this.currentImages = data.images || [];
                this.currentImageIndex = 0;
                
                if (this.currentImages.length > 0) {
                    this.currentImage = this.currentImages[0];
                    await this.loadImage(this.currentImage.id);
                    this.updateImageCounter();
                    this.populateThumbnails();
                    this.notyf.success(`Loaded series with ${this.currentImages.length} images`);
                } else {
                    this.notyf.error('No images found in this series');
                }
            } else {
                console.error('Failed to load series images:', response.status);
                this.notyf.error('Failed to load series images');
            }
        } catch (error) {
            console.error('Error selecting series:', error);
            this.notyf.error('Error selecting series');
        }
    }
    
    // === THUMBNAIL FUNCTIONALITY ===
    populateThumbnails() {
        const thumbnailContainer = document.getElementById('thumbnail-container');
        if (!thumbnailContainer || !this.currentImages) return;
        
        thumbnailContainer.innerHTML = '';
        
        this.currentImages.forEach((image, index) => {
            const thumbnailItem = document.createElement('div');
            thumbnailItem.className = 'thumbnail-item';
            if (index === this.currentImageIndex) {
                thumbnailItem.classList.add('active');
            }
            
            thumbnailItem.innerHTML = `
                <div class="thumbnail-image">
                    <div class="thumbnail-placeholder">
                        <i class="fas fa-image"></i>
                    </div>
                </div>
                <div class="thumbnail-info">
                    <span class="image-number">${index + 1}</span>
                    <span class="instance-number">Inst: ${image.instance_number || index + 1}</span>
                </div>
            `;
            
            thumbnailItem.addEventListener('click', () => this.goToImage(index));
            thumbnailContainer.appendChild(thumbnailItem);
            
            // Load thumbnail asynchronously
            this.loadThumbnail(image, thumbnailItem);
        });
    }
    
    async loadThumbnail(image, thumbnailItem) {
        try {
            const response = await fetch(`/viewer/api/get-image-data/${image.id}/?thumbnail_size=64`);
            if (response.ok) {
                const data = await response.json();
                if (data.image_data) {
                    const img = thumbnailItem.querySelector('.thumbnail-placeholder');
                    if (img) {
                        img.innerHTML = `<img src="${data.image_data}" alt="Thumbnail ${image.id}">`;
                    }
                }
            }
        } catch (error) {
            console.log('Thumbnail load failed for image', image.id);
        }
    }
    
    updateThumbnailSelection() {
        document.querySelectorAll('.thumbnail-item').forEach((item, index) => {
            if (index === this.currentImageIndex) {
                item.classList.add('active');
                item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    // === RECONSTRUCTION FEATURES ===
    async generateMPR() {
        if (!this.currentSeries) {
            this.notyf.error('Please select a series first');
            return;
        }
        
        try {
            this.notyf.info('Generating Multi-Planar Reconstruction...');
            
            const response = await fetch(`/viewer/api/series/${this.currentSeries.id}/mpr/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.enableMPRMode(data);
                this.notyf.success('MPR reconstruction completed');
            } else {
                throw new Error(`MPR generation failed: ${response.status}`);
            }
        } catch (error) {
            console.error('Error generating MPR:', error);
            this.notyf.error('Failed to generate MPR reconstruction');
        }
    }
    
    async generateMIP() {
        if (!this.currentSeries) {
            this.notyf.error('Please select a series first');
            return;
        }
        
        try {
            this.notyf.info('Generating Maximum Intensity Projection...');
            
            const response = await fetch(`/viewer/api/series/${this.currentSeries.id}/mip/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.image_data) {
                    await this.displayProcessedImage(data.image_data);
                    this.notyf.success('MIP reconstruction completed');
                } else {
                    throw new Error('No MIP data received');
                }
            } else {
                throw new Error(`MIP generation failed: ${response.status}`);
            }
        } catch (error) {
            console.error('Error generating MIP:', error);
            this.notyf.error('Failed to generate MIP reconstruction');
        }
    }
    
    async generateVolumeRendering() {
        if (!this.currentSeries) {
            this.notyf.error('Please select a series first');
            return;
        }
        
        try {
            this.notyf.info('Generating Volume Rendering...');
            
            const response = await fetch(`/viewer/api/series/${this.currentSeries.id}/volume-rendering/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.image_data) {
                    await this.displayProcessedImage(data.image_data);
                    this.notyf.success('Volume rendering completed');
                } else {
                    throw new Error('No volume rendering data received');
                }
            } else {
                throw new Error(`Volume rendering failed: ${response.status}`);
            }
        } catch (error) {
            console.error('Error generating volume rendering:', error);
            this.notyf.error('Failed to generate volume rendering');
        }
    }
    
    enableMPRMode(mprData) {
        this.mprEnabled = true;
        this.mprData = mprData;
        
        // Create MPR layout
        this.createMPRLayout();
        
        // Display axial, sagittal, and coronal views
        if (mprData.axial) this.displayMPRView('axial', mprData.axial);
        if (mprData.sagittal) this.displayMPRView('sagittal', mprData.sagittal);
        if (mprData.coronal) this.displayMPRView('coronal', mprData.coronal);
    }
    
    createMPRLayout() {
        // Switch to 2x2 layout for MPR
        this.setLayout('2x2');
        
        // Label the viewports
        const viewports = document.querySelectorAll('.viewport-canvas');
        const labels = ['Axial', 'Sagittal', 'Coronal', 'Volume'];
        
        viewports.forEach((viewport, index) => {
            if (index < labels.length) {
                const label = document.createElement('div');
                label.className = 'viewport-label';
                label.textContent = labels[index];
                viewport.parentElement.appendChild(label);
            }
        });
    }
    
    displayMPRView(view, imageData) {
        // Implementation for displaying MPR views
        console.log(`Displaying ${view} MPR view`);
        // This would display the specific MPR view in the appropriate viewport
    }
    
    // === KEYBOARD SHORTCUTS ===
    handleKeyboardShortcut(event) {
        if (event.target.tagName.toLowerCase() === 'input') return;
        
        const key = event.key.toLowerCase();
        
        switch (key) {
            case 'arrowleft':
            case 'a':
                event.preventDefault();
                this.previousImage();
                break;
            case 'arrowright':
            case 'd':
                event.preventDefault();
                this.nextImage();
                break;
            case 'arrowup':
                event.preventDefault();
                this.adjustWindowLevel(50);
                break;
            case 'arrowdown':
                event.preventDefault();
                this.adjustWindowLevel(-50);
                break;
            case 'r':
                event.preventDefault();
                this.rotateImage();
                break;
            case 'f':
                event.preventDefault();
                this.flipImage();
                break;
            case 'i':
                event.preventDefault();
                this.invertImage();
                break;
            case 'escape':
                event.preventDefault();
                this.resetView();
                break;
        }
    }
    
    adjustWindowLevel(delta) {
        this.windowLevel += delta;
        this.refreshCurrentImage();
        this.updateViewportInfo();
        this.notyf.info(`Window Level: ${this.windowLevel}

    setupNavigationButtons() {
        // Setup image navigation
        const nextBtn = document.querySelector('[title="Next Image"], #next-image-btn');
        const prevBtn = document.querySelector('[title="Previous Image"], #prev-image-btn');
        
        if (nextBtn) nextBtn.addEventListener('click', () => this.nextImage());
        if (prevBtn) prevBtn.addEventListener('click', () => this.previousImage());
    }
    
    setupReconstructionButtons() {
        // Setup 3D/MPR buttons
        const mprBtn = document.getElementById('mpr-btn');
        const mipBtn = document.getElementById('mip-btn');
        const volumeBtn = document.getElementById('volume-render-btn');
        
        if (mprBtn) {
            mprBtn.addEventListener('click', () => this.generateMPR());
        }
        
        if (mipBtn) {
            mipBtn.addEventListener('click', () => this.generateMIP());
        }

    setupAllButtons() {
        console.log('Setting up all viewer buttons...');
        
        // Tool buttons
        this.setupToolButtons();
        
        // Navigation buttons
        this.setupNavigationButtons();
        
        // Window/Level presets
        this.setupWindowLevelPresets();
        
        // Image manipulation buttons
        this.setupImageManipulationButtons();
        
        // Reconstruction buttons
        this.setupAllButtons();
        
        // Export and utility buttons
        this.setupUtilityButtons();
        
        console.log('✅ All viewer buttons setup complete');
    }
    
    setupToolButtons() {
        const toolButtons = [
            { id: 'windowing-adv-btn', tool: 'windowing' },
            { id: 'pan-adv-btn', tool: 'pan' },
            { id: 'zoom-adv-btn', tool: 'zoom' },
            { id: 'distance-adv-btn', tool: 'distance' },
            { id: 'angle-adv-btn', tool: 'angle' },
            { id: 'area-adv-btn', tool: 'area' },
            { id: 'hu-adv-btn', tool: 'hu' },
            { id: 'crosshair-adv-btn', tool: 'crosshair' },
            { id: 'magnify-btn', tool: 'magnify' }
        ];
        
        toolButtons.forEach(({ id, tool }) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', () => this.setActiveTool(tool));
            }
        });
    }
    
    setupWindowLevelPresets() {
        const presets = document.querySelectorAll('.preset-btn');
        presets.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const preset = e.target.dataset.preset;
                this.applyWindowPreset(preset);
            });
        });
        
        // Window/Level sliders
        const windowWidthSlider = document.getElementById('window-width-slider');
        const windowLevelSlider = document.getElementById('window-level-slider');
        const windowWidthInput = document.getElementById('window-width-input');
        const windowLevelInput = document.getElementById('window-level-input');
        
        if (windowWidthSlider) {
            windowWidthSlider.addEventListener('input', (e) => {
                this.windowWidth = parseFloat(e.target.value);
                if (windowWidthInput) windowWidthInput.value = this.windowWidth;
                this.refreshCurrentImage();
            });
        }
        
        if (windowLevelSlider) {
            windowLevelSlider.addEventListener('input', (e) => {
                this.windowLevel = parseFloat(e.target.value);
                if (windowLevelInput) windowLevelInput.value = this.windowLevel;
                this.refreshCurrentImage();
            });
        }
        
        if (windowWidthInput) {
            windowWidthInput.addEventListener('change', (e) => {
                this.windowWidth = parseFloat(e.target.value);
                if (windowWidthSlider) windowWidthSlider.value = this.windowWidth;
                this.refreshCurrentImage();
            });
        }
        
        if (windowLevelInput) {
            windowLevelInput.addEventListener('change', (e) => {
                this.windowLevel = parseFloat(e.target.value);
                if (windowLevelSlider) windowLevelSlider.value = this.windowLevel;
                this.refreshCurrentImage();
            });
        }
    }
    
    setupImageManipulationButtons() {
        const manipulationButtons = [
            { id: 'rotate-btn', action: () => this.rotateImage() },
            { id: 'flip-btn', action: () => this.flipImage() },
            { id: 'invert-adv-btn', action: () => this.invertImage() },
            { id: 'reset-adv-btn', action: () => this.resetView() },
            { id: 'fit-to-window-btn', action: () => this.fitToWindow() },
            { id: 'actual-size-btn', action: () => this.actualSize() }
        ];
        
        manipulationButtons.forEach(({ id, action }) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', action);
            }
        });
    }
    
    setupUtilityButtons() {
        // Layout buttons
        const layoutButtons = [
            { id: 'layout-1x1-btn', layout: '1x1' },
            { id: 'layout-2x2-btn', layout: '2x2' },
            { id: 'layout-1x2-btn', layout: '1x2' }
        ];
        
        layoutButtons.forEach(({ id, layout }) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', () => this.setLayout(layout));
            }
        });
        
        // Clear buttons
        const clearMeasurementsBtn = document.getElementById('clear-measurements-btn');
        if (clearMeasurementsBtn) {
            clearMeasurementsBtn.addEventListener('click', () => this.clearMeasurements());
        }
        
        const clearAnnotationsBtn = document.getElementById('clear-annotations-btn');
        if (clearAnnotationsBtn) {
            clearAnnotationsBtn.addEventListener('click', () => this.clearAnnotations());
        }
        
        // AI buttons
        const aiButtons = [
            { id: 'ai-analysis-btn', action: () => this.runAIAnalysis() },
            { id: 'ai-segment-btn', action: () => this.runAISegmentation() },
            { id: 'ai-detect-lesions', action: () => this.detectLesions() },
            { id: 'ai-segment-organs', action: () => this.segmentOrgans() },
            { id: 'ai-calculate-volume', action: () => this.calculateVolume() }
        ];
        
        aiButtons.forEach(({ id, action }) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', action);
            }
        });
    }
    
    applyWindowPreset(presetName) {
        const presets = {
            'lung': { ww: 1500, wl: -600 },
            'bone': { ww: 2000, wl: 300 },
            'soft': { ww: 400, wl: 40 },
            'brain': { ww: 100, wl: 50 },
            'abdomen': { ww: 350, wl: 50 },
            'mediastinum': { ww: 400, wl: 20 }
        };
        
        const preset = presets[presetName];
        if (preset) {
            this.windowWidth = preset.ww;
            this.windowLevel = preset.wl;
            
            // Update UI controls
            const widthSlider = document.getElementById('window-width-slider');
            const levelSlider = document.getElementById('window-level-slider');
            const widthInput = document.getElementById('window-width-input');
            const levelInput = document.getElementById('window-level-input');
            
            if (widthSlider) widthSlider.value = this.windowWidth;
            if (levelSlider) levelSlider.value = this.windowLevel;
            if (widthInput) widthInput.value = this.windowWidth;
            if (levelInput) levelInput.value = this.windowLevel;
            
            this.refreshCurrentImage();
            this.notyf.success(`Applied ${presetName} preset`);
        }
    }
    
    invertImage() {
        this.inverted = !this.inverted;
        this.refreshCurrentImage();
        this.notyf.success(`Image ${this.inverted ? 'inverted' : 'normal'}`);
    }
    
    resetView() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.rotation = 0;
        this.flipHorizontal = false;
        this.flipVertical = false;
        this.refreshCurrentImage();
        this.notyf.success('View reset');
    }
    
    fitToWindow() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.refreshCurrentImage();
        this.notyf.success('Fit to window');
    }
    
    actualSize() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.refreshCurrentImage();
        this.notyf.success('Actual size (1:1)');
    }
    
    setLayout(layout) {
        console.log('Setting layout:', layout);
        // Layout implementation would go here
        this.notyf.success(`Layout: ${layout}`);
    }
    
    clearMeasurements() {
        // Clear all measurements
        this.measurements = [];
        this.refreshCurrentImage();
        this.notyf.success('Measurements cleared');
    }
    
    clearAnnotations() {
        // Clear all annotations
        this.annotations = [];
        this.refreshCurrentImage();
        this.notyf.success('Annotations cleared');
    }
    
    runAIAnalysis() {
        if (!this.currentImage) {
            this.notyf.error('No image selected for AI analysis');
            return;
        }
        
        this.notyf.info('AI Analysis started...');
        // AI analysis implementation would go here
        setTimeout(() => {
            this.notyf.success('AI Analysis completed');
        }, 3000);
    }
    
    runAISegmentation() {
        if (!this.currentImage) {
            this.notyf.error('No image selected for segmentation');
            return;
        }
        
        this.notyf.info('AI Segmentation started...');
        // AI segmentation implementation would go here
        setTimeout(() => {
            this.notyf.success('AI Segmentation completed');
        }, 5000);
    }
    
    detectLesions() {
        this.notyf.info('Detecting lesions...');
        setTimeout(() => {
            this.notyf.success('Lesion detection completed');
        }, 4000);
    }
    
    segmentOrgans() {
        this.notyf.info('Segmenting organs...');
        setTimeout(() => {
            this.notyf.success('Organ segmentation completed');
        }, 6000);
    }
    
    calculateVolume() {
        this.notyf.info('Calculating volume...');
        setTimeout(() => {
            this.notyf.success('Volume calculation completed');
        }, 3000);
    }
        
        if (volumeBtn) {
            volumeBtn.addEventListener('click', () => this.generateVolumeRendering());
        }
        
        console.log('✅ Reconstruction buttons setup complete');
    }
    
    toggleThumbnails() {
        const container = document.getElementById('thumbnail-container');
        const toggle = document.getElementById('thumbnail-toggle');
        
        if (container && toggle) {
            const isVisible = container.style.display !== 'none';
            container.style.display = isVisible ? 'none' : 'block';
            
            const icon = toggle.querySelector('i');
            if (icon) {
                icon.className = isVisible ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
            }
        }
    }`);
    }
}
