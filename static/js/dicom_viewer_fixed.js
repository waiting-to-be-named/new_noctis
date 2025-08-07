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

        // DICOM Standard Properties
        this.dicomMetadata = null;
        this.pixelSpacing = { x: 1.0, y: 1.0 }; // mm per pixel
        this.sliceThickness = 1.0; // mm
        this.windowCenter = 40; // Default for soft tissue
        this.windowWidth = 400; // Default for soft tissue
        this.rescaleSlope = 1; // For HU calculation
        this.rescaleIntercept = -1024; // For HU calculation
        this.photometricInterpretation = 'MONOCHROME2';
        this.bitsAllocated = 16;
        this.bitsStored = 12;
        this.highBit = 11;
        this.pixelRepresentation = 0; // Unsigned
        
        // Standard DICOM Window Presets
        this.windowPresets = {
            'abdomen': { center: 60, width: 400 },
            'angio': { center: 300, width: 600 },
            'bone': { center: 300, width: 1500 },
            'brain': { center: 40, width: 80 },
            'chest': { center: 40, width: 400 },
            'lungs': { center: -400, width: 1500 },
            'mediastinum': { center: 50, width: 350 },
            'spine': { center: 30, width: 400 },
            'stroke': { center: 40, width: 40 },
            'subdural': { center: 75, width: 215 }
        };
        
        // Magnification properties
        this.magnificationEnabled = false;
        this.magnificationLevel = 2.0;
        this.magnificationRadius = 75; // pixels
        this.magnificationPos = { x: 0, y: 0 };
        this.magnificationCanvas = null;
        this.magnificationCtx = null;
        
        // Measurement properties
        this.measurements = [];
        this.activeMeasurement = null;
        this.measurementUnits = 'mm'; // Default to millimeters
        this.measurementTools = {
            'distance': { active: false, points: [] },
            'angle': { active: false, points: [] },
            'rectangle': { active: false, points: [] },
            'ellipse': { active: false, points: [] },
            'polygon': { active: false, points: [] },
            'freehand': { active: false, points: [] }
        };
        
        // Annotation properties
        this.annotations = [];
        this.activeAnnotation = null;
        this.annotationFont = '14px Arial';
        this.annotationColor = '#FFFF00'; // Standard DICOM yellow
        
        // Hounsfield Unit display
        this.showHounsfieldValues = true;
        this.hounsfieldDisplay = null;
        
        this.initializeMagnificationCanvas();
        this.initializeHounsfieldDisplay();
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
            // Create MPR workspace
            this.createMPRWorkspace();
            
            // Load volume data
            await this.loadVolumeData();
            
            // Generate MPR views
            this.generateMPRViews();
            
            this.notyf.success('MPR reconstruction initialized');
            
        } catch (error) {
            console.error('Error initializing MPR:', error);
            this.notyf.error('Failed to initialize MPR reconstruction');
            this.mprEnabled = false;
        }
    }

    createMPRWorkspace() {
        // Create MPR container if it doesn't exist
        let mprContainer = document.getElementById('mpr-container');
        if (!mprContainer) {
            mprContainer = document.createElement('div');
            mprContainer.id = 'mpr-container';
            mprContainer.className = 'mpr-workspace';
            mprContainer.innerHTML = `
                <div class="mpr-header">
                    <h3>Multi-Planar Reconstruction</h3>
                    <div class="mpr-controls">
                        <button id="mpr-axial-btn" class="mpr-view-btn active">Axial</button>
                        <button id="mpr-sagittal-btn" class="mpr-view-btn">Sagittal</button>
                        <button id="mpr-coronal-btn" class="mpr-view-btn">Coronal</button>
                        <button id="mpr-3d-btn" class="mpr-view-btn">3D</button>
                        <button id="mpr-close-btn" class="btn-close">×</button>
                    </div>
                </div>
                <div class="mpr-views">
                    <div class="mpr-view-panel" id="mpr-axial-panel">
                        <h4>Axial View</h4>
                        <canvas id="mpr-axial-canvas" width="256" height="256"></canvas>
                        <div class="mpr-slice-control">
                            <input type="range" id="axial-slice-slider" min="0" max="100" value="50">
                            <span id="axial-slice-info">Slice: 50/100</span>
                        </div>
                    </div>
                    <div class="mpr-view-panel" id="mpr-sagittal-panel">
                        <h4>Sagittal View</h4>
                        <canvas id="mpr-sagittal-canvas" width="256" height="256"></canvas>
                        <div class="mpr-slice-control">
                            <input type="range" id="sagittal-slice-slider" min="0" max="100" value="50">
                            <span id="sagittal-slice-info">Slice: 50/100</span>
                        </div>
                    </div>
                    <div class="mpr-view-panel" id="mpr-coronal-panel">
                        <h4>Coronal View</h4>
                        <canvas id="mpr-coronal-canvas" width="256" height="256"></canvas>
                        <div class="mpr-slice-control">
                            <input type="range" id="coronal-slice-slider" min="0" max="100" value="50">
                            <span id="coronal-slice-info">Slice: 50/100</span>
                        </div>
                    </div>
                    <div class="mpr-view-panel" id="mpr-3d-panel">
                        <h4>3D Volume Rendering</h4>
                        <canvas id="mpr-3d-canvas" width="400" height="400"></canvas>
                        <div class="render-controls">
                            <label>Opacity: <input type="range" id="volume-opacity" min="0" max="100" value="50"></label>
                            <label>Threshold: <input type="range" id="volume-threshold" min="0" max="4095" value="500"></label>
                            <button id="rotate-3d-btn">Auto Rotate</button>
                        </div>
                    </div>
                </div>
            `;
            
            // Add to main content area
            const mainContent = document.querySelector('.main-content-advanced');
            mainContent.appendChild(mprContainer);
            
            // Setup MPR event handlers
            this.setupMPREventHandlers();
        }
        
        // Show MPR container
        mprContainer.style.display = 'block';
    }

    setupMPREventHandlers() {
        // View switching buttons
        document.getElementById('mpr-axial-btn').addEventListener('click', () => this.switchMPRView('axial'));
        document.getElementById('mpr-sagittal-btn').addEventListener('click', () => this.switchMPRView('sagittal'));
        document.getElementById('mpr-coronal-btn').addEventListener('click', () => this.switchMPRView('coronal'));
        document.getElementById('mpr-3d-btn').addEventListener('click', () => this.switchMPRView('3d'));
        
        // Close button
        document.getElementById('mpr-close-btn').addEventListener('click', () => this.disableMPR());
        
        // Slice sliders
        document.getElementById('axial-slice-slider').addEventListener('input', (e) => {
            this.currentSlice.axial = parseInt(e.target.value);
            this.renderMPRView('axial');
            this.updateSliceInfo('axial');
        });
        
        document.getElementById('sagittal-slice-slider').addEventListener('input', (e) => {
            this.currentSlice.sagittal = parseInt(e.target.value);
            this.renderMPRView('sagittal');
            this.updateSliceInfo('sagittal');
        });
        
        document.getElementById('coronal-slice-slider').addEventListener('input', (e) => {
            this.currentSlice.coronal = parseInt(e.target.value);
            this.renderMPRView('coronal');
            this.updateSliceInfo('coronal');
        });
        
        // 3D controls
        document.getElementById('volume-opacity').addEventListener('input', (e) => {
            this.volumeOpacity = parseInt(e.target.value) / 100;
            this.render3DVolume();
        });
        
        document.getElementById('volume-threshold').addEventListener('input', (e) => {
            this.volumeThreshold = parseInt(e.target.value);
            this.render3DVolume();
        });
        
        document.getElementById('rotate-3d-btn').addEventListener('click', () => this.toggle3DRotation());
    }

    async loadVolumeData() {
        if (!this.currentImages || this.currentImages.length === 0) {
            throw new Error('No images available for volume reconstruction');
        }

        this.notyf.info('Loading volume data...');
        
        // Initialize volume data structure
        this.volumeData = {
            images: [],
            dimensions: { x: 0, y: 0, z: this.currentImages.length },
            spacing: { x: 1.0, y: 1.0, z: 1.0 },
            origin: { x: 0, y: 0, z: 0 },
            pixelData: null
        };

        // Load all images and extract pixel data
        for (let i = 0; i < this.currentImages.length; i++) {
            try {
                const imageData = await this.loadImagePixelData(this.currentImages[i]);
                this.volumeData.images.push(imageData);
                
                if (i === 0) {
                    // Set dimensions from first image
                    this.volumeData.dimensions.x = imageData.width;
                    this.volumeData.dimensions.y = imageData.height;
                }
            } catch (error) {
                console.error(`Error loading image ${i}:`, error);
            }
        }

        // Create 3D pixel array
        this.create3DPixelArray();
        
        // Initialize slice positions
        this.currentSlice = {
            axial: Math.floor(this.volumeData.dimensions.z / 2),
            sagittal: Math.floor(this.volumeData.dimensions.x / 2),
            coronal: Math.floor(this.volumeData.dimensions.y / 2)
        };

        this.notyf.success('Volume data loaded successfully');
    }

    async loadImagePixelData(imageInfo) {
        // Create a temporary canvas to extract pixel data
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                tempCanvas.width = img.width;
                tempCanvas.height = img.height;
                tempCtx.drawImage(img, 0, 0);
                
                const imageData = tempCtx.getImageData(0, 0, img.width, img.height);
                resolve({
                    width: img.width,
                    height: img.height,
                    data: imageData.data,
                    grayscaleData: this.convertToGrayscale(imageData.data)
                });
            };
            img.onerror = reject;
            
            // Load the image (this would need actual image data)
            img.src = `/viewer/api/get-image/${imageInfo.id}/`;
        });
    }

    convertToGrayscale(rgbaData) {
        const grayscale = new Uint16Array(rgbaData.length / 4);
        for (let i = 0; i < grayscale.length; i++) {
            const r = rgbaData[i * 4];
            const g = rgbaData[i * 4 + 1];
            const b = rgbaData[i * 4 + 2];
            // Convert to grayscale and scale to 16-bit
            grayscale[i] = Math.round((r * 0.299 + g * 0.587 + b * 0.114) * 257);
        }
        return grayscale;
    }

    create3DPixelArray() {
        const { x, y, z } = this.volumeData.dimensions;
        this.volumeData.pixelData = new Uint16Array(x * y * z);
        
        // Fill 3D array from individual images
        for (let zi = 0; zi < z; zi++) {
            if (this.volumeData.images[zi]) {
                const imageData = this.volumeData.images[zi].grayscaleData;
                for (let yi = 0; yi < y; yi++) {
                    for (let xi = 0; xi < x; xi++) {
                        const index = zi * x * y + yi * x + xi;
                        const imageIndex = yi * x + xi;
                        if (imageIndex < imageData.length) {
                            this.volumeData.pixelData[index] = imageData[imageIndex];
                        }
                    }
                }
            }
        }
    }

    generateMPRViews() {
        this.renderMPRView('axial');
        this.renderMPRView('sagittal');
        this.renderMPRView('coronal');
        this.updateAllSliceInfo();
    }

    renderMPRView(view) {
        const canvas = document.getElementById(`mpr-${view}-canvas`);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const { x, y, z } = this.volumeData.dimensions;
        
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        if (!this.volumeData.pixelData) return;
        
        let imageData, sliceIndex;
        
        switch (view) {
            case 'axial':
                sliceIndex = this.currentSlice.axial;
                imageData = this.extractAxialSlice(sliceIndex);
                break;
            case 'sagittal':
                sliceIndex = this.currentSlice.sagittal;
                imageData = this.extractSagittalSlice(sliceIndex);
                break;
            case 'coronal':
                sliceIndex = this.currentSlice.coronal;
                imageData = this.extractCoronalSlice(sliceIndex);
                break;
        }
        
        if (imageData) {
            this.displaySliceOnCanvas(ctx, imageData, canvas.width, canvas.height);
        }
    }

    extractAxialSlice(sliceIndex) {
        const { x, y, z } = this.volumeData.dimensions;
        if (sliceIndex < 0 || sliceIndex >= z) return null;
        
        const sliceData = new Uint16Array(x * y);
        const startIndex = sliceIndex * x * y;
        
        for (let i = 0; i < x * y; i++) {
            sliceData[i] = this.volumeData.pixelData[startIndex + i];
        }
        
        return { data: sliceData, width: x, height: y };
    }

    extractSagittalSlice(sliceIndex) {
        const { x, y, z } = this.volumeData.dimensions;
        if (sliceIndex < 0 || sliceIndex >= x) return null;
        
        const sliceData = new Uint16Array(z * y);
        
        for (let zi = 0; zi < z; zi++) {
            for (let yi = 0; yi < y; yi++) {
                const volumeIndex = zi * x * y + yi * x + sliceIndex;
                const sliceDataIndex = zi * y + yi;
                sliceData[sliceDataIndex] = this.volumeData.pixelData[volumeIndex];
            }
        }
        
        return { data: sliceData, width: z, height: y };
    }

    extractCoronalSlice(sliceIndex) {
        const { x, y, z } = this.volumeData.dimensions;
        if (sliceIndex < 0 || sliceIndex >= y) return null;
        
        const sliceData = new Uint16Array(x * z);
        
        for (let zi = 0; zi < z; zi++) {
            for (let xi = 0; xi < x; xi++) {
                const volumeIndex = zi * x * y + sliceIndex * x + xi;
                const sliceDataIndex = zi * x + xi;
                sliceData[sliceDataIndex] = this.volumeData.pixelData[volumeIndex];
            }
        }
        
        return { data: sliceData, width: x, height: z };
    }

    displaySliceOnCanvas(ctx, sliceData, canvasWidth, canvasHeight) {
        const { data, width, height } = sliceData;
        
        // Create ImageData for the slice
        const imageData = ctx.createImageData(width, height);
        const pixels = imageData.data;
        
        // Convert 16-bit grayscale to 8-bit RGBA
        for (let i = 0; i < data.length; i++) {
            const value = Math.min(255, Math.floor(data[i] / 257)); // Convert to 8-bit
            const pixelIndex = i * 4;
            pixels[pixelIndex] = value;     // R
            pixels[pixelIndex + 1] = value; // G
            pixels[pixelIndex + 2] = value; // B
            pixels[pixelIndex + 3] = 255;   // A
        }
        
        // Create temporary canvas for scaling
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        tempCanvas.width = width;
        tempCanvas.height = height;
        tempCtx.putImageData(imageData, 0, 0);
        
        // Draw scaled to main canvas
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(tempCanvas, 0, 0, canvasWidth, canvasHeight);
        
        // Add crosshairs
        this.drawMPRCrosshairs(ctx, canvasWidth, canvasHeight);
    }

    drawMPRCrosshairs(ctx, width, height) {
        ctx.strokeStyle = '#ff0000';
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 5]);
        
        // Vertical line
        ctx.beginPath();
        ctx.moveTo(width / 2, 0);
        ctx.lineTo(width / 2, height);
        ctx.stroke();
        
        // Horizontal line
        ctx.beginPath();
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.stroke();
        
        ctx.setLineDash([]);
    }

    switchMPRView(view) {
        // Hide all panels
        document.querySelectorAll('.mpr-view-panel').forEach(panel => {
            panel.style.display = 'none';
        });
        
        // Remove active class from all buttons
        document.querySelectorAll('.mpr-view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Show selected panel and activate button
        const panel = document.getElementById(`mpr-${view}-panel`);
        const button = document.getElementById(`mpr-${view}-btn`);
        
        if (panel) panel.style.display = 'block';
        if (button) button.classList.add('active');
        
        // Render 3D if selected
        if (view === '3d') {
            this.render3DVolume();
        }
    }

    updateSliceInfo(view) {
        const infoElement = document.getElementById(`${view}-slice-info`);
        if (infoElement) {
            const max = this.volumeData.dimensions[view === 'axial' ? 'z' : view === 'sagittal' ? 'x' : 'y'];
            const current = this.currentSlice[view];
            infoElement.textContent = `Slice: ${current}/${max}`;
        }
    }

    updateAllSliceInfo() {
        this.updateSliceInfo('axial');
        this.updateSliceInfo('sagittal');
        this.updateSliceInfo('coronal');
        
        // Update slider max values
        const { x, y, z } = this.volumeData.dimensions;
        document.getElementById('axial-slice-slider').max = z - 1;
        document.getElementById('sagittal-slice-slider').max = x - 1;
        document.getElementById('coronal-slice-slider').max = y - 1;
    }

    // === MAXIMUM INTENSITY PROJECTION (MIP) ===
    
    enableMIP() {
        if (!this.currentImages || this.currentImages.length < 5) {
            this.notyf.error('Need at least 5 images for MIP reconstruction');
            return;
        }

        this.notyf.info('Generating Maximum Intensity Projection...');
        this.generateMIP();
    }

    async generateMIP() {
        try {
            if (!this.volumeData) {
                await this.loadVolumeData();
            }
            
            // Create MIP workspace
            this.createMIPWorkspace();
            
            // Generate MIP projections
            this.generateMIPProjections();
            
            this.notyf.success('MIP reconstruction completed');
            
        } catch (error) {
            console.error('Error generating MIP:', error);
            this.notyf.error('Failed to generate MIP reconstruction');
        }
    }

    createMIPWorkspace() {
        let mipContainer = document.getElementById('mip-container');
        if (!mipContainer) {
            mipContainer = document.createElement('div');
            mipContainer.id = 'mip-container';
            mipContainer.className = 'mip-workspace';
            mipContainer.innerHTML = `
                <div class="mip-header">
                    <h3>Maximum Intensity Projection</h3>
                    <div class="mip-controls">
                        <button id="mip-ap-btn" class="mip-view-btn active">Anterior-Posterior</button>
                        <button id="mip-lateral-btn" class="mip-view-btn">Lateral</button>
                        <button id="mip-superior-btn" class="mip-view-btn">Superior-Inferior</button>
                        <button id="mip-rotating-btn" class="mip-view-btn">Rotating</button>
                        <button id="mip-close-btn" class="btn-close">×</button>
                    </div>
                </div>
                <div class="mip-views">
                    <div class="mip-view-panel" id="mip-ap-panel">
                        <h4>Anterior-Posterior MIP</h4>
                        <canvas id="mip-ap-canvas" width="400" height="400"></canvas>
                    </div>
                    <div class="mip-view-panel" id="mip-lateral-panel">
                        <h4>Lateral MIP</h4>
                        <canvas id="mip-lateral-canvas" width="400" height="400"></canvas>
                    </div>
                    <div class="mip-view-panel" id="mip-superior-panel">
                        <h4>Superior-Inferior MIP</h4>
                        <canvas id="mip-superior-canvas" width="400" height="400"></canvas>
                    </div>
                    <div class="mip-view-panel" id="mip-rotating-panel">
                        <h4>Rotating MIP</h4>
                        <canvas id="mip-rotating-canvas" width="400" height="400"></canvas>
                        <div class="rotation-controls">
                            <button id="start-rotation-btn">Start Rotation</button>
                            <button id="stop-rotation-btn">Stop Rotation</button>
                            <label>Speed: <input type="range" id="rotation-speed" min="1" max="10" value="5"></label>
                        </div>
                    </div>
                </div>
            `;
            
            const mainContent = document.querySelector('.main-content-advanced');
            mainContent.appendChild(mipContainer);
            
            this.setupMIPEventHandlers();
        }
        
        mipContainer.style.display = 'block';
    }

    setupMIPEventHandlers() {
        document.getElementById('mip-ap-btn').addEventListener('click', () => this.switchMIPView('ap'));
        document.getElementById('mip-lateral-btn').addEventListener('click', () => this.switchMIPView('lateral'));
        document.getElementById('mip-superior-btn').addEventListener('click', () => this.switchMIPView('superior'));
        document.getElementById('mip-rotating-btn').addEventListener('click', () => this.switchMIPView('rotating'));
        document.getElementById('mip-close-btn').addEventListener('click', () => this.closeMIP());
        
        document.getElementById('start-rotation-btn').addEventListener('click', () => this.startMIPRotation());
        document.getElementById('stop-rotation-btn').addEventListener('click', () => this.stopMIPRotation());
    }

    generateMIPProjections() {
        this.generateMIPProjection('ap');
        this.generateMIPProjection('lateral');
        this.generateMIPProjection('superior');
    }

    generateMIPProjection(direction) {
        const canvas = document.getElementById(`mip-${direction}-canvas`);
        if (!canvas || !this.volumeData) return;
        
        const ctx = canvas.getContext('2d');
        const { x, y, z } = this.volumeData.dimensions;
        
        let projectionData, width, height;
        
        switch (direction) {
            case 'ap': // Anterior-Posterior (looking from front)
                projectionData = this.projectAP();
                width = x;
                height = z;
                break;
            case 'lateral': // Lateral (looking from side)
                projectionData = this.projectLateral();
                width = y;
                height = z;
                break;
            case 'superior': // Superior-Inferior (looking from top)
                projectionData = this.projectSuperior();
                width = x;
                height = y;
                break;
        }
        
        if (projectionData) {
            this.displayMIPOnCanvas(ctx, projectionData, width, height, canvas.width, canvas.height);
        }
    }

    projectAP() {
        const { x, y, z } = this.volumeData.dimensions;
        const projection = new Uint16Array(x * z);
        
        for (let zi = 0; zi < z; zi++) {
            for (let xi = 0; xi < x; xi++) {
                let maxIntensity = 0;
                
                // Find maximum intensity along Y axis
                for (let yi = 0; yi < y; yi++) {
                    const volumeIndex = zi * x * y + yi * x + xi;
                    const intensity = this.volumeData.pixelData[volumeIndex];
                    if (intensity > maxIntensity) {
                        maxIntensity = intensity;
                    }
                }
                
                const projectionIndex = zi * x + xi;
                projection[projectionIndex] = maxIntensity;
            }
        }
        
        return projection;
    }

    projectLateral() {
        const { x, y, z } = this.volumeData.dimensions;
        const projection = new Uint16Array(y * z);
        
        for (let zi = 0; zi < z; zi++) {
            for (let yi = 0; yi < y; yi++) {
                let maxIntensity = 0;
                
                // Find maximum intensity along X axis
                for (let xi = 0; xi < x; xi++) {
                    const volumeIndex = zi * x * y + yi * x + xi;
                    const intensity = this.volumeData.pixelData[volumeIndex];
                    if (intensity > maxIntensity) {
                        maxIntensity = intensity;
                    }
                }
                
                const projectionIndex = zi * y + yi;
                projection[projectionIndex] = maxIntensity;
            }
        }
        
        return projection;
    }

    projectSuperior() {
        const { x, y, z } = this.volumeData.dimensions;
        const projection = new Uint16Array(x * y);
        
        for (let yi = 0; yi < y; yi++) {
            for (let xi = 0; xi < x; xi++) {
                let maxIntensity = 0;
                
                // Find maximum intensity along Z axis
                for (let zi = 0; zi < z; zi++) {
                    const volumeIndex = zi * x * y + yi * x + xi;
                    const intensity = this.volumeData.pixelData[volumeIndex];
                    if (intensity > maxIntensity) {
                        maxIntensity = intensity;
                    }
                }
                
                const projectionIndex = yi * x + xi;
                projection[projectionIndex] = maxIntensity;
            }
        }
        
        return projection;
    }

    displayMIPOnCanvas(ctx, projectionData, dataWidth, dataHeight, canvasWidth, canvasHeight) {
        // Create ImageData
        const imageData = ctx.createImageData(dataWidth, dataHeight);
        const pixels = imageData.data;
        
        // Convert to RGBA
        for (let i = 0; i < projectionData.length; i++) {
            const value = Math.min(255, Math.floor(projectionData[i] / 257));
            const pixelIndex = i * 4;
            pixels[pixelIndex] = value;     // R
            pixels[pixelIndex + 1] = value; // G
            pixels[pixelIndex + 2] = value; // B
            pixels[pixelIndex + 3] = 255;   // A
        }
        
        // Scale and display
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        tempCanvas.width = dataWidth;
        tempCanvas.height = dataHeight;
        tempCtx.putImageData(imageData, 0, 0);
        
        ctx.clearRect(0, 0, canvasWidth, canvasHeight);
        ctx.imageSmoothingEnabled = true;
        ctx.drawImage(tempCanvas, 0, 0, canvasWidth, canvasHeight);
    }

    switchMIPView(view) {
        // Hide all panels
        document.querySelectorAll('.mip-view-panel').forEach(panel => {
            panel.style.display = 'none';
        });
        
        // Remove active class
        document.querySelectorAll('.mip-view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Show selected
        const panel = document.getElementById(`mip-${view}-panel`);
        const button = document.getElementById(`mip-${view}-btn`);
        
        if (panel) panel.style.display = 'block';
        if (button) button.classList.add('active');
    }

    // === BONE RECONSTRUCTION ===
    
    enableBoneReconstruction() {
        if (!this.currentImages || this.currentImages.length < 10) {
            this.notyf.error('Need at least 10 images for bone reconstruction');
            return;
        }

        this.notyf.info('Initializing bone reconstruction...');
        this.generateBoneReconstruction();
    }

    async generateBoneReconstruction() {
        try {
            if (!this.volumeData) {
                await this.loadVolumeData();
            }
            
            // Create bone reconstruction workspace
            this.createBoneReconstructionWorkspace();
            
            // Apply bone segmentation
            this.performBoneSegmentation();
            
            // Generate 3D bone model
            this.generate3DBoneModel();
            
            this.notyf.success('Bone reconstruction completed');
            
        } catch (error) {
            console.error('Error in bone reconstruction:', error);
            this.notyf.error('Failed to complete bone reconstruction');
        }
    }

    createBoneReconstructionWorkspace() {
        let boneContainer = document.getElementById('bone-container');
        if (!boneContainer) {
            boneContainer = document.createElement('div');
            boneContainer.id = 'bone-container';
            boneContainer.className = 'bone-workspace';
            boneContainer.innerHTML = `
                <div class="bone-header">
                    <h3>Bone Reconstruction</h3>
                    <div class="bone-controls">
                        <label>HU Threshold: <input type="range" id="bone-threshold" min="150" max="3000" value="250"></label>
                        <label>Opacity: <input type="range" id="bone-opacity" min="0" max="100" value="80"></label>
                        <label>Quality: 
                            <select id="bone-quality">
                                <option value="low">Low (Fast)</option>
                                <option value="medium" selected>Medium</option>
                                <option value="high">High (Slow)</option>
                            </select>
                        </label>
                        <button id="bone-regenerate-btn">Regenerate</button>
                        <button id="bone-close-btn" class="btn-close">×</button>
                    </div>
                </div>
                <div class="bone-views">
                    <div class="bone-view-panel">
                        <h4>3D Bone Model</h4>
                        <canvas id="bone-3d-canvas" width="500" height="500"></canvas>
                        <div class="bone-3d-controls">
                            <button id="bone-rotate-btn">Auto Rotate</button>
                            <button id="bone-reset-view-btn">Reset View</button>
                            <label>Zoom: <input type="range" id="bone-zoom" min="0.5" max="3" step="0.1" value="1"></label>
                        </div>
                    </div>
                    <div class="bone-segmentation-panel">
                        <h4>Bone Segmentation Preview</h4>
                        <canvas id="bone-segmentation-canvas" width="300" height="300"></canvas>
                        <div class="segmentation-info">
                            <p>Bone Volume: <span id="bone-volume">Calculating...</span></p>
                            <p>Bone Density: <span id="bone-density">Calculating...</span></p>
                        </div>
                    </div>
                </div>
            `;
            
            const mainContent = document.querySelector('.main-content-advanced');
            mainContent.appendChild(boneContainer);
            
            this.setupBoneReconstructionEventHandlers();
        }
        
        boneContainer.style.display = 'block';
    }

    setupBoneReconstructionEventHandlers() {
        document.getElementById('bone-threshold').addEventListener('input', (e) => {
            this.boneThreshold = parseInt(e.target.value);
            this.performBoneSegmentation();
        });
        
        document.getElementById('bone-opacity').addEventListener('input', (e) => {
            this.boneOpacity = parseInt(e.target.value) / 100;
            this.generate3DBoneModel();
        });
        
        document.getElementById('bone-regenerate-btn').addEventListener('click', () => {
            this.generateBoneReconstruction();
        });
        
        document.getElementById('bone-close-btn').addEventListener('click', () => {
            this.closeBoneReconstruction();
        });
        
        document.getElementById('bone-rotate-btn').addEventListener('click', () => {
            this.toggleBoneRotation();
        });
        
        document.getElementById('bone-reset-view-btn').addEventListener('click', () => {
            this.resetBoneView();
        });
    }

    performBoneSegmentation() {
        if (!this.volumeData) return;
        
        this.boneThreshold = this.boneThreshold || 250; // Default bone HU threshold
        const { x, y, z } = this.volumeData.dimensions;
        
        // Create bone mask
        this.boneMask = new Uint8Array(x * y * z);
        let boneVoxelCount = 0;
        let totalBoneDensity = 0;
        
        for (let i = 0; i < this.volumeData.pixelData.length; i++) {
            const huValue = this.pixelToHU(this.volumeData.pixelData[i]);
            if (huValue >= this.boneThreshold) {
                this.boneMask[i] = 255;
                boneVoxelCount++;
                totalBoneDensity += huValue;
            } else {
                this.boneMask[i] = 0;
            }
        }
        
        // Calculate bone statistics
        const voxelVolume = 1.0; // mm³ per voxel (simplified)
        const boneVolume = boneVoxelCount * voxelVolume;
        const averageBoneDensity = boneVoxelCount > 0 ? totalBoneDensity / boneVoxelCount : 0;
        
        // Update UI
        document.getElementById('bone-volume').textContent = `${boneVolume.toFixed(1)} mm³`;
        document.getElementById('bone-density').textContent = `${averageBoneDensity.toFixed(1)} HU`;
        
        // Display segmentation preview
        this.displayBoneSegmentation();
    }

    pixelToHU(pixelValue) {
        // Convert pixel value to Hounsfield Units
        // This is a simplified conversion - real DICOM uses slope/intercept
        return (pixelValue / 257) * 4000 - 1000;
    }

    displayBoneSegmentation() {
        const canvas = document.getElementById('bone-segmentation-canvas');
        if (!canvas || !this.boneMask) return;
        
        const ctx = canvas.getContext('2d');
        const { x, y, z } = this.volumeData.dimensions;
        
        // Display middle axial slice with bone overlay
        const sliceIndex = Math.floor(z / 2);
        const sliceStart = sliceIndex * x * y;
        
        const imageData = ctx.createImageData(x, y);
        const pixels = imageData.data;
        
        for (let i = 0; i < x * y; i++) {
            const originalValue = Math.min(255, Math.floor(this.volumeData.pixelData[sliceStart + i] / 257));
            const boneValue = this.boneMask[sliceStart + i];
            
            const pixelIndex = i * 4;
            if (boneValue > 0) {
                // Highlight bone in red
                pixels[pixelIndex] = Math.min(255, originalValue + 100);     // R
                pixels[pixelIndex + 1] = originalValue;                      // G
                pixels[pixelIndex + 2] = originalValue;                      // B
            } else {
                pixels[pixelIndex] = originalValue;     // R
                pixels[pixelIndex + 1] = originalValue; // G
                pixels[pixelIndex + 2] = originalValue; // B
            }
            pixels[pixelIndex + 3] = 255; // A
        }
        
        // Scale and display
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        tempCanvas.width = x;
        tempCanvas.height = y;
        tempCtx.putImageData(imageData, 0, 0);
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.imageSmoothingEnabled = true;
        ctx.drawImage(tempCanvas, 0, 0, canvas.width, canvas.height);
    }

    generate3DBoneModel() {
        const canvas = document.getElementById('bone-3d-canvas');
        if (!canvas || !this.boneMask) return;
        
        const ctx = canvas.getContext('2d');
        
        // Simple 3D rendering using raycasting
        this.render3DBones(ctx, canvas.width, canvas.height);
    }

    render3DBones(ctx, width, height) {
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, width, height);
        
        const { x, y, z } = this.volumeData.dimensions;
        const centerX = width / 2;
        const centerY = height / 2;
        
        // Simple orthographic projection
        const scale = Math.min(width, height) / Math.max(x, y, z) * 0.8;
        
        this.boneOpacity = this.boneOpacity || 0.8;
        this.boneRotationAngle = this.boneRotationAngle || 0;
        
        const cos = Math.cos(this.boneRotationAngle);
        const sin = Math.sin(this.boneRotationAngle);
        
        // Render bone voxels as points
        for (let zi = 0; zi < z; zi += 2) { // Skip voxels for performance
            for (let yi = 0; yi < y; yi += 2) {
                for (let xi = 0; xi < x; xi += 2) {
                    const index = zi * x * y + yi * x + xi;
                    if (this.boneMask[index] > 0) {
                        // Apply rotation
                        const rotX = (xi - x/2) * cos - (zi - z/2) * sin;
                        const rotZ = (xi - x/2) * sin + (zi - z/2) * cos;
                        
                        const screenX = centerX + rotX * scale;
                        const screenY = centerY + (yi - y/2) * scale;
                        const depth = (rotZ + z/2) / z; // Normalized depth
                        
                        // Simple depth-based color and size
                        const intensity = Math.floor(155 + depth * 100);
                        const size = 1 + depth * 2;
                        
                        ctx.fillStyle = `rgba(${intensity}, ${intensity - 50}, ${intensity - 100}, ${this.boneOpacity})`;
                        ctx.fillRect(screenX, screenY, size, size);
                    }
                }
            }
        }
    }

    toggleBoneRotation() {
        if (this.boneRotationInterval) {
            clearInterval(this.boneRotationInterval);
            this.boneRotationInterval = null;
            document.getElementById('bone-rotate-btn').textContent = 'Auto Rotate';
        } else {
            this.boneRotationInterval = setInterval(() => {
                this.boneRotationAngle += 0.05;
                this.generate3DBoneModel();
            }, 50);
            document.getElementById('bone-rotate-btn').textContent = 'Stop Rotation';
        }
    }

    resetBoneView() {
        this.boneRotationAngle = 0;
        this.generate3DBoneModel();
    }

    closeBoneReconstruction() {
        const container = document.getElementById('bone-container');
        if (container) {
            container.style.display = 'none';
        }
        
        if (this.boneRotationInterval) {
            clearInterval(this.boneRotationInterval);
            this.boneRotationInterval = null;
        }
    }

    disableMPR() {
        this.mprEnabled = false;
        const mprContainer = document.getElementById('mpr-container');
        if (mprContainer) {
            mprContainer.style.display = 'none';
        }
    }

    closeMIP() {
        const mipContainer = document.getElementById('mip-container');
        if (mipContainer) {
            mipContainer.style.display = 'none';
        }
        
        if (this.mipRotationInterval) {
            clearInterval(this.mipRotationInterval);
            this.mipRotationInterval = null;
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
        // === BASIC TOOLS ===
        
        // Pan tool
        const panBtn = document.getElementById('pan-adv-btn') || document.getElementById('pan-btn');
        if (panBtn) {
            panBtn.addEventListener('click', () => {
                this.activeTool = 'pan';
                this.setActiveToolButton('pan');
                this.notyf.info('Pan tool activated - drag to move image');
            });
        }

        // Zoom tools
        const zoomInBtn = document.getElementById('zoom-in-btn');
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => this.zoomIn());
        }

        const zoomOutBtn = document.getElementById('zoom-out-btn');
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => this.zoomOut());
        }

        const resetZoomBtn = document.getElementById('reset-zoom-btn');
        if (resetZoomBtn) {
            resetZoomBtn.addEventListener('click', () => this.resetZoom());
        }

        const fitBtn = document.getElementById('fit-btn');
        if (fitBtn) {
            fitBtn.addEventListener('click', () => this.fitToWindow());
        }

        const actualSizeBtn = document.getElementById('actual-size-btn');
        if (actualSizeBtn) {
            actualSizeBtn.addEventListener('click', () => this.actualSize());
        }

        // === MAGNIFICATION ===
        const magnifyBtn = document.getElementById('magnify-btn');
        if (magnifyBtn) {
            magnifyBtn.addEventListener('click', () => this.toggleMagnification());
        }

        // === MEASUREMENT TOOLS ===
        const measureBtn = document.getElementById('measure-btn');
        if (measureBtn) {
            measureBtn.addEventListener('click', () => this.startMeasurement('distance'));
        }

        const angleBtn = document.getElementById('angle-btn');
        if (angleBtn) {
            angleBtn.addEventListener('click', () => this.startMeasurement('angle'));
        }

        const rectangleBtn = document.getElementById('rectangle-btn');
        if (rectangleBtn) {
            rectangleBtn.addEventListener('click', () => this.startMeasurement('rectangle'));
        }

        const ellipseBtn = document.getElementById('ellipse-btn');
        if (ellipseBtn) {
            ellipseBtn.addEventListener('click', () => this.startMeasurement('ellipse'));
        }

        // Toggle measurement units
        const toggleUnitsBtn = document.getElementById('toggle-units-btn');
        if (toggleUnitsBtn) {
            toggleUnitsBtn.addEventListener('click', () => this.toggleMeasurementUnits());
        }

        // Clear measurements
        const clearMeasurementsBtn = document.getElementById('clear-measurements-btn');
        if (clearMeasurementsBtn) {
            clearMeasurementsBtn.addEventListener('click', () => this.clearMeasurements());
        }

        // === WINDOWING AND IMAGE PROCESSING ===
        
        // Windowing tool
        const windowingBtn = document.getElementById('windowing-btn');
        if (windowingBtn) {
            windowingBtn.addEventListener('click', () => {
                this.activeTool = 'windowing';
                this.setActiveToolButton('windowing');
                this.notyf.info('Windowing tool - drag to adjust window/level');
            });
        }

        // Window presets
        const presetButtons = document.querySelectorAll('[data-window-preset]');
        presetButtons.forEach(btn => {
            const preset = btn.getAttribute('data-window-preset');
            btn.addEventListener('click', () => this.setWindowPreset(preset));
        });

        // Image processing tools
        const invertBtn = document.getElementById('invert-btn');
        if (invertBtn) {
            invertBtn.addEventListener('click', () => this.toggleInversion());
        }

        const contrastBtn = document.getElementById('contrast-btn');
        if (contrastBtn) {
            contrastBtn.addEventListener('click', () => this.adjustContrast());
        }

        const sharpenBtn = document.getElementById('sharpen-btn');
        if (sharpenBtn) {
            sharpenBtn.addEventListener('click', () => this.toggleSharpening());
        }

        const edgeEnhancementBtn = document.getElementById('edge-enhancement-btn');
        if (edgeEnhancementBtn) {
            edgeEnhancementBtn.addEventListener('click', () => this.toggleEdgeEnhancement());
        }

        // === ROTATION AND FLIP ===
        const rotateLeftBtn = document.getElementById('rotate-left-btn');
        if (rotateLeftBtn) {
            rotateLeftBtn.addEventListener('click', () => this.rotateLeft());
        }

        const rotateRightBtn = document.getElementById('rotate-right-btn');
        if (rotateRightBtn) {
            rotateRightBtn.addEventListener('click', () => this.rotateRight());
        }

        const flipHBtn = document.getElementById('flip-h-btn');
        if (flipHBtn) {
            flipHBtn.addEventListener('click', () => this.flipHorizontally());
        }

        const flipVBtn = document.getElementById('flip-v-btn');
        if (flipVBtn) {
            flipVBtn.addEventListener('click', () => this.flipVertically());
        }

        // === ADVANCED RECONSTRUCTION ===
        const mprBtn = document.getElementById('mpr-btn');
        if (mprBtn) {
            mprBtn.addEventListener('click', () => this.toggleMPR());
        }

        const mipBtn = document.getElementById('mip-btn');
        if (mipBtn) {
            mipBtn.addEventListener('click', () => this.enableMIP());
        }

        const boneReconBtn = document.getElementById('bone-recon-btn');
        if (boneReconBtn) {
            boneReconBtn.addEventListener('click', () => this.enableBoneReconstruction());
        }

        const volumeRenderBtn = document.getElementById('volume-render-btn');
        if (volumeRenderBtn) {
            volumeRenderBtn.addEventListener('click', () => this.enableVolumeRendering());
        }

        // === ANALYSIS TOOLS ===
        const roiBtn = document.getElementById('roi-btn');
        if (roiBtn) {
            roiBtn.addEventListener('click', () => this.toggleROIAnalysis());
        }

        const histogramBtn = document.getElementById('histogram-btn');
        if (histogramBtn) {
            histogramBtn.addEventListener('click', () => this.showImageHistogram());
        }

        const statisticsBtn = document.getElementById('statistics-btn');
        if (statisticsBtn) {
            statisticsBtn.addEventListener('click', () => this.showImageStatistics());
        }

        const metadataBtn = document.getElementById('metadata-btn');
        if (metadataBtn) {
            metadataBtn.addEventListener('click', () => this.showDICOMMetadata());
        }

        // === HOUNSFIELD DISPLAY ===
        const hounsfieldBtn = document.getElementById('hounsfield-btn');
        if (hounsfieldBtn) {
            hounsfieldBtn.addEventListener('click', () => this.toggleHounsfieldDisplay());
        }

        // === ANNOTATIONS ===
        const annotateBtn = document.getElementById('annotate-btn');
        if (annotateBtn) {
            annotateBtn.addEventListener('click', () => this.startAnnotation());
        }

        const arrowBtn = document.getElementById('arrow-btn');
        if (arrowBtn) {
            arrowBtn.addEventListener('click', () => this.startArrowAnnotation());
        }

        // === NAVIGATION ===
        const prevBtn = document.getElementById('prev-btn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.previousImage());
        }

        const nextBtn = document.getElementById('next-btn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.nextImage());
        }

        const playBtn = document.getElementById('play-btn');
        if (playBtn) {
            playBtn.addEventListener('click', () => this.toggleCineMode());
        }

        // === RESET AND CLEAR ===
        const resetBtn = document.getElementById('reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetAllSettings());
        }

        const clearAllBtn = document.getElementById('clear-all-btn');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => this.clearAllOverlays());
        }
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

    // === DICOM METADATA EXTRACTION ===
    
    extractDICOMMetadata(imageData) {
        // This would normally extract from actual DICOM headers
        // For now, we'll use reasonable defaults and update from any available metadata
        
        if (imageData && imageData.metadata) {
            const metadata = imageData.metadata;
            
            // Extract pixel spacing (0028,0030)
            if (metadata.pixelSpacing) {
                this.pixelSpacing.x = parseFloat(metadata.pixelSpacing[0]) || 1.0;
                this.pixelSpacing.y = parseFloat(metadata.pixelSpacing[1]) || 1.0;
            }
            
            // Extract slice thickness (0018,0050)
            if (metadata.sliceThickness) {
                this.sliceThickness = parseFloat(metadata.sliceThickness) || 1.0;
            }
            
            // Extract window center/width (0028,1050), (0028,1051)
            if (metadata.windowCenter) {
                this.windowCenter = parseFloat(metadata.windowCenter) || 40;
            }
            if (metadata.windowWidth) {
                this.windowWidth = parseFloat(metadata.windowWidth) || 400;
            }
            
            // Extract rescale slope/intercept (0028,1053), (0028,1052)
            if (metadata.rescaleSlope) {
                this.rescaleSlope = parseFloat(metadata.rescaleSlope) || 1;
            }
            if (metadata.rescaleIntercept) {
                this.rescaleIntercept = parseFloat(metadata.rescaleIntercept) || -1024;
            }
            
            // Extract image properties
            if (metadata.photometricInterpretation) {
                this.photometricInterpretation = metadata.photometricInterpretation;
            }
            if (metadata.bitsAllocated) {
                this.bitsAllocated = parseInt(metadata.bitsAllocated) || 16;
            }
            if (metadata.bitsStored) {
                this.bitsStored = parseInt(metadata.bitsStored) || 12;
            }
        }
        
        this.dicomMetadata = imageData?.metadata || {};
    }

    // === MAGNIFICATION IMPLEMENTATION ===
    
    initializeMagnificationCanvas() {
        this.magnificationCanvas = document.createElement('canvas');
        this.magnificationCanvas.width = this.magnificationRadius * 2;
        this.magnificationCanvas.height = this.magnificationRadius * 2;
        this.magnificationCanvas.style.position = 'absolute';
        this.magnificationCanvas.style.border = '2px solid #00ff00';
        this.magnificationCanvas.style.borderRadius = '50%';
        this.magnificationCanvas.style.pointerEvents = 'none';
        this.magnificationCanvas.style.display = 'none';
        this.magnificationCanvas.style.zIndex = '1000';
        this.magnificationCtx = this.magnificationCanvas.getContext('2d');
        
        // Add to canvas container
        this.canvas.parentElement.appendChild(this.magnificationCanvas);
    }

    toggleMagnification() {
        this.magnificationEnabled = !this.magnificationEnabled;
        this.setActiveToolButton('magnify');
        
        if (this.magnificationEnabled) {
            this.activeTool = 'magnify';
            this.magnificationCanvas.style.display = 'block';
            this.notyf.info('Magnification enabled - move mouse to magnify');
        } else {
            this.activeTool = null;
            this.magnificationCanvas.style.display = 'none';
            this.notyf.info('Magnification disabled');
        }
    }

    updateMagnification(mouseX, mouseY) {
        if (!this.magnificationEnabled || !this.imageData) return;
        
        // Update magnification position
        this.magnificationPos.x = mouseX;
        this.magnificationPos.y = mouseY;
        
        // Position the magnification canvas
        const rect = this.canvas.getBoundingClientRect();
        this.magnificationCanvas.style.left = (rect.left + mouseX + 20) + 'px';
        this.magnificationCanvas.style.top = (rect.top + mouseY - this.magnificationRadius) + 'px';
        
        // Clear magnification canvas
        this.magnificationCtx.clearRect(0, 0, this.magnificationCanvas.width, this.magnificationCanvas.height);
        
        // Create circular clipping path
        this.magnificationCtx.save();
        this.magnificationCtx.beginPath();
        this.magnificationCtx.arc(this.magnificationRadius, this.magnificationRadius, this.magnificationRadius - 2, 0, 2 * Math.PI);
        this.magnificationCtx.clip();
        
        // Calculate source region
        const sourceSize = this.magnificationRadius / this.magnificationLevel;
        const sourceX = Math.max(0, Math.min(this.canvas.width - sourceSize * 2, mouseX - sourceSize));
        const sourceY = Math.max(0, Math.min(this.canvas.height - sourceSize * 2, mouseY - sourceSize));
        
        // Draw magnified content
        this.magnificationCtx.drawImage(
            this.canvas,
            sourceX, sourceY, sourceSize * 2, sourceSize * 2,
            0, 0, this.magnificationCanvas.width, this.magnificationCanvas.height
        );
        
        // Draw crosshairs
        this.magnificationCtx.strokeStyle = '#ff0000';
        this.magnificationCtx.lineWidth = 1;
        this.magnificationCtx.setLineDash([5, 5]);
        
        // Vertical crosshair
        this.magnificationCtx.beginPath();
        this.magnificationCtx.moveTo(this.magnificationRadius, 0);
        this.magnificationCtx.lineTo(this.magnificationRadius, this.magnificationCanvas.height);
        this.magnificationCtx.stroke();
        
        // Horizontal crosshair
        this.magnificationCtx.beginPath();
        this.magnificationCtx.moveTo(0, this.magnificationRadius);
        this.magnificationCtx.lineTo(this.magnificationCanvas.width, this.magnificationRadius);
        this.magnificationCtx.stroke();
        
        this.magnificationCtx.setLineDash([]);
        this.magnificationCtx.restore();
        
        // Show pixel info and Hounsfield values
        this.updatePixelInfo(mouseX, mouseY);
    }

    // === HOUNSFIELD UNIT CALCULATIONS ===
    
    initializeHounsfieldDisplay() {
        this.hounsfieldDisplay = document.createElement('div');
        this.hounsfieldDisplay.id = 'hounsfield-display';
        this.hounsfieldDisplay.style.position = 'absolute';
        this.hounsfieldDisplay.style.top = '10px';
        this.hounsfieldDisplay.style.right = '10px';
        this.hounsfieldDisplay.style.background = 'rgba(0, 0, 0, 0.8)';
        this.hounsfieldDisplay.style.color = '#00ff00';
        this.hounsfieldDisplay.style.padding = '10px';
        this.hounsfieldDisplay.style.borderRadius = '5px';
        this.hounsfieldDisplay.style.fontFamily = 'monospace';
        this.hounsfieldDisplay.style.fontSize = '12px';
        this.hounsfieldDisplay.style.zIndex = '999';
        this.hounsfieldDisplay.style.display = 'none';
        
        this.canvas.parentElement.appendChild(this.hounsfieldDisplay);
    }

    calculateHounsfieldUnit(pixelValue) {
        // Standard DICOM HU calculation: HU = pixel_value * rescale_slope + rescale_intercept
        return Math.round(pixelValue * this.rescaleSlope + this.rescaleIntercept);
    }

    getPixelValue(x, y) {
        if (!this.imageData) return 0;
        
        const index = (Math.floor(y) * this.canvas.width + Math.floor(x)) * 4;
        if (index >= 0 && index < this.imageData.data.length) {
            // Convert RGB back to grayscale value (assuming grayscale image)
            const r = this.imageData.data[index];
            const g = this.imageData.data[index + 1];
            const b = this.imageData.data[index + 2];
            
            // For DICOM, we need the original pixel value, not the display value
            // This is a simplified approach - in real DICOM, we'd access the original pixel data
            return Math.round((r + g + b) / 3);
        }
        return 0;
    }

    updatePixelInfo(mouseX, mouseY) {
        if (!this.showHounsfieldValues) return;
        
        const pixelValue = this.getPixelValue(mouseX, mouseY);
        const hounsfieldUnit = this.calculateHounsfieldUnit(pixelValue);
        
        // Convert pixel coordinates to real-world coordinates
        const realWorldX = mouseX * this.pixelSpacing.x;
        const realWorldY = mouseY * this.pixelSpacing.y;
        
        this.hounsfieldDisplay.innerHTML = `
            <div>Position: (${Math.round(realWorldX)}, ${Math.round(realWorldY)}) mm</div>
            <div>Pixel: (${Math.round(mouseX)}, ${Math.round(mouseY)})</div>
            <div>Pixel Value: ${pixelValue}</div>
            <div>Hounsfield: ${hounsfieldUnit} HU</div>
            <div>Window: ${this.windowCenter}/${this.windowWidth}</div>
            <div>Zoom: ${(this.zoomLevel * 100).toFixed(0)}%</div>
        `;
        this.hounsfieldDisplay.style.display = 'block';
    }

    toggleHounsfieldDisplay() {
        this.showHounsfieldValues = !this.showHounsfieldValues;
        if (!this.showHounsfieldValues) {
            this.hounsfieldDisplay.style.display = 'none';
        }
        this.notyf.info(`Hounsfield display ${this.showHounsfieldValues ? 'enabled' : 'disabled'}`);
    }

    // === CALIBRATED MEASUREMENTS ===
    
    startMeasurement(tool) {
        this.activeTool = tool;
        this.setActiveToolButton(tool);
        
        // Reset active measurement
        if (this.measurementTools[tool]) {
            this.measurementTools[tool].active = true;
            this.measurementTools[tool].points = [];
        }
        
        this.notyf.info(`${tool.charAt(0).toUpperCase() + tool.slice(1)} measurement started`);
    }

    addMeasurementPoint(x, y) {
        const currentTool = this.activeTool;
        if (!currentTool || !this.measurementTools[currentTool]) return;
        
        const tool = this.measurementTools[currentTool];
        tool.points.push({ x, y });
        
        // Check if measurement is complete
        switch (currentTool) {
            case 'distance':
                if (tool.points.length === 2) {
                    this.completeMeasurement(currentTool);
                }
                break;
            case 'angle':
                if (tool.points.length === 3) {
                    this.completeMeasurement(currentTool);
                }
                break;
            case 'rectangle':
                if (tool.points.length === 2) {
                    this.completeMeasurement(currentTool);
                }
                break;
            case 'ellipse':
                if (tool.points.length === 2) {
                    this.completeMeasurement(currentTool);
                }
                break;
        }
        
        this.drawMeasurements();
    }

    completeMeasurement(tool) {
        const measurement = this.measurementTools[tool];
        const result = this.calculateMeasurement(tool, measurement.points);
        
        this.measurements.push({
            id: Date.now(),
            tool: tool,
            points: [...measurement.points],
            result: result,
            units: this.measurementUnits,
            timestamp: new Date().toISOString()
        });
        
        // Reset tool
        measurement.active = false;
        measurement.points = [];
        this.activeTool = null;
        this.setActiveToolButton(null);
        
        this.notyf.success(`${tool} measurement: ${result.value.toFixed(2)} ${result.unit}`);
        this.updateMeasurementsList();
    }

    calculateMeasurement(tool, points) {
        switch (tool) {
            case 'distance':
                return this.calculateDistance(points[0], points[1]);
            case 'angle':
                return this.calculateAngle(points[0], points[1], points[2]);
            case 'rectangle':
                return this.calculateRectangleArea(points[0], points[1]);
            case 'ellipse':
                return this.calculateEllipseArea(points[0], points[1]);
            default:
                return { value: 0, unit: 'unknown' };
        }
    }

    calculateDistance(point1, point2) {
        const dx = (point2.x - point1.x) * this.pixelSpacing.x;
        const dy = (point2.y - point1.y) * this.pixelSpacing.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        return {
            value: distance,
            unit: 'mm',
            pixels: Math.sqrt(Math.pow(point2.x - point1.x, 2) + Math.pow(point2.y - point1.y, 2))
        };
    }

    calculateAngle(point1, point2, point3) {
        // Calculate angle at point2
        const vector1 = { x: point1.x - point2.x, y: point1.y - point2.y };
        const vector2 = { x: point3.x - point2.x, y: point3.y - point2.y };
        
        const dot = vector1.x * vector2.x + vector1.y * vector2.y;
        const mag1 = Math.sqrt(vector1.x * vector1.x + vector1.y * vector1.y);
        const mag2 = Math.sqrt(vector2.x * vector2.x + vector2.y * vector2.y);
        
        const angle = Math.acos(dot / (mag1 * mag2)) * (180 / Math.PI);
        
        return {
            value: angle,
            unit: 'degrees'
        };
    }

    calculateRectangleArea(point1, point2) {
        const width = Math.abs(point2.x - point1.x) * this.pixelSpacing.x;
        const height = Math.abs(point2.y - point1.y) * this.pixelSpacing.y;
        const area = width * height;
        
        return {
            value: area,
            unit: 'mm²',
            width: width,
            height: height
        };
    }

    calculateEllipseArea(point1, point2) {
        const a = Math.abs(point2.x - point1.x) * this.pixelSpacing.x / 2; // Semi-major axis
        const b = Math.abs(point2.y - point1.y) * this.pixelSpacing.y / 2; // Semi-minor axis
        const area = Math.PI * a * b;
        
        return {
            value: area,
            unit: 'mm²',
            semiMajor: a,
            semiMinor: b
        };
    }

    drawMeasurements() {
        // Clear previous overlays
        this.clearOverlays();
        
        // Draw completed measurements
        this.measurements.forEach(measurement => {
            this.drawMeasurement(measurement);
        });
        
        // Draw active measurement
        Object.keys(this.measurementTools).forEach(tool => {
            const measurement = this.measurementTools[tool];
            if (measurement.active && measurement.points.length > 0) {
                this.drawActiveMeasurement(tool, measurement.points);
            }
        });
    }

    drawMeasurement(measurement) {
        this.ctx.save();
        this.ctx.strokeStyle = '#ffff00'; // DICOM standard yellow
        this.ctx.lineWidth = 2;
        this.ctx.font = this.annotationFont;
        this.ctx.fillStyle = '#ffff00';
        
        switch (measurement.tool) {
            case 'distance':
                this.drawDistanceMeasurement(measurement);
                break;
            case 'angle':
                this.drawAngleMeasurement(measurement);
                break;
            case 'rectangle':
                this.drawRectangleMeasurement(measurement);
                break;
            case 'ellipse':
                this.drawEllipseMeasurement(measurement);
                break;
        }
        
        this.ctx.restore();
    }

    drawDistanceMeasurement(measurement) {
        const [p1, p2] = measurement.points;
        
        // Draw line
        this.ctx.beginPath();
        this.ctx.moveTo(p1.x, p1.y);
        this.ctx.lineTo(p2.x, p2.y);
        this.ctx.stroke();
        
        // Draw endpoints
        this.drawMeasurementPoint(p1.x, p1.y);
        this.drawMeasurementPoint(p2.x, p2.y);
        
        // Draw measurement text
        const midX = (p1.x + p2.x) / 2;
        const midY = (p1.y + p2.y) / 2;
        const text = `${measurement.result.value.toFixed(2)} ${measurement.result.unit}`;
        this.ctx.fillText(text, midX + 5, midY - 5);
    }

    drawAngleMeasurement(measurement) {
        const [p1, p2, p3] = measurement.points;
        
        // Draw lines
        this.ctx.beginPath();
        this.ctx.moveTo(p1.x, p1.y);
        this.ctx.lineTo(p2.x, p2.y);
        this.ctx.lineTo(p3.x, p3.y);
        this.ctx.stroke();
        
        // Draw points
        this.drawMeasurementPoint(p1.x, p1.y);
        this.drawMeasurementPoint(p2.x, p2.y);
        this.drawMeasurementPoint(p3.x, p3.y);
        
        // Draw angle arc
        const radius = 30;
        const angle1 = Math.atan2(p1.y - p2.y, p1.x - p2.x);
        const angle2 = Math.atan2(p3.y - p2.y, p3.x - p2.x);
        
        this.ctx.beginPath();
        this.ctx.arc(p2.x, p2.y, radius, angle1, angle2);
        this.ctx.stroke();
        
        // Draw measurement text
        const text = `${measurement.result.value.toFixed(1)}°`;
        this.ctx.fillText(text, p2.x + 35, p2.y - 5);
    }

    drawRectangleMeasurement(measurement) {
        const [p1, p2] = measurement.points;
        const width = p2.x - p1.x;
        const height = p2.y - p1.y;
        
        // Draw rectangle
        this.ctx.strokeRect(p1.x, p1.y, width, height);
        
        // Draw corners
        this.drawMeasurementPoint(p1.x, p1.y);
        this.drawMeasurementPoint(p2.x, p2.y);
        
        // Draw measurement text
        const centerX = p1.x + width / 2;
        const centerY = p1.y + height / 2;
        const text = `${measurement.result.value.toFixed(2)} ${measurement.result.unit}`;
        this.ctx.fillText(text, centerX, centerY);
    }

    drawEllipseMeasurement(measurement) {
        const [p1, p2] = measurement.points;
        const centerX = (p1.x + p2.x) / 2;
        const centerY = (p1.y + p2.y) / 2;
        const radiusX = Math.abs(p2.x - p1.x) / 2;
        const radiusY = Math.abs(p2.y - p1.y) / 2;
        
        // Draw ellipse
        this.ctx.beginPath();
        this.ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
        this.ctx.stroke();
        
        // Draw control points
        this.drawMeasurementPoint(p1.x, p1.y);
        this.drawMeasurementPoint(p2.x, p2.y);
        
        // Draw measurement text
        const text = `${measurement.result.value.toFixed(2)} ${measurement.result.unit}`;
        this.ctx.fillText(text, centerX, centerY);
    }

    drawMeasurementPoint(x, y) {
        this.ctx.beginPath();
        this.ctx.arc(x, y, 3, 0, 2 * Math.PI);
        this.ctx.fill();
    }

    drawActiveMeasurement(tool, points) {
        this.ctx.save();
        this.ctx.strokeStyle = '#ff0000'; // Red for active measurement
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([5, 5]);
        
        if (points.length >= 1) {
            points.forEach(point => {
                this.drawMeasurementPoint(point.x, point.y);
            });
        }
        
        if (points.length >= 2 && (tool === 'distance' || tool === 'rectangle' || tool === 'ellipse')) {
            const [p1, p2] = points;
            this.ctx.beginPath();
            this.ctx.moveTo(p1.x, p1.y);
            this.ctx.lineTo(p2.x, p2.y);
            this.ctx.stroke();
        }
        
        if (points.length >= 2 && tool === 'angle') {
            const [p1, p2] = points;
            this.ctx.beginPath();
            this.ctx.moveTo(p1.x, p1.y);
            this.ctx.lineTo(p2.x, p2.y);
            this.ctx.stroke();
        }
        
        if (points.length === 3 && tool === 'angle') {
            const [p1, p2, p3] = points;
            this.ctx.beginPath();
            this.ctx.moveTo(p2.x, p2.y);
            this.ctx.lineTo(p3.x, p3.y);
            this.ctx.stroke();
        }
        
        this.ctx.restore();
    }

    // === STANDARD DICOM WINDOWING ===
    
    setWindowPreset(presetName) {
        if (this.windowPresets[presetName]) {
            const preset = this.windowPresets[presetName];
            this.windowCenter = preset.center;
            this.windowWidth = preset.width;
            this.applyWindowing();
            this.updateWindowLevelDisplay();
            this.notyf.info(`Applied ${presetName} window preset (${preset.center}/${preset.width})`);
        }
    }

    applyWindowing() {
        if (!this.originalImageData) return;
        
        const imageData = this.ctx.createImageData(this.originalImageData);
        const data = imageData.data;
        const originalData = this.originalImageData.data;
        
        const windowMin = this.windowCenter - this.windowWidth / 2;
        const windowMax = this.windowCenter + this.windowWidth / 2;
        
        for (let i = 0; i < data.length; i += 4) {
            // Get original grayscale value
            const originalValue = (originalData[i] + originalData[i + 1] + originalData[i + 2]) / 3;
            
            // Convert to Hounsfield units
            const hu = this.calculateHounsfieldUnit(originalValue);
            
            // Apply windowing
            let displayValue;
            if (hu <= windowMin) {
                displayValue = 0;
            } else if (hu >= windowMax) {
                displayValue = 255;
            } else {
                displayValue = Math.round(((hu - windowMin) / this.windowWidth) * 255);
            }
            
            // Apply photometric interpretation
            if (this.photometricInterpretation === 'MONOCHROME1') {
                displayValue = 255 - displayValue; // Invert for MONOCHROME1
            }
            
            data[i] = displayValue;     // R
            data[i + 1] = displayValue; // G
            data[i + 2] = displayValue; // B
            data[i + 3] = originalData[i + 3]; // A
        }
        
        this.ctx.putImageData(imageData, 0, 0);
        this.imageData = imageData;
    }

    // === ENHANCED EVENT HANDLING ===
    
    setupEventListeners() {
        // ... existing event listeners ...
        
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            
            // Update magnification
            if (this.magnificationEnabled) {
                this.updateMagnification(mouseX, mouseY);
            }
            
            // Update pixel info
            this.updatePixelInfo(mouseX, mouseY);
            
            // Handle windowing
            if (this.activeTool === 'windowing' && e.buttons === 1) {
                const deltaX = e.movementX;
                const deltaY = e.movementY;
                
                this.windowCenter += deltaX;
                this.windowWidth = Math.max(1, this.windowWidth + deltaY);
                
                this.applyWindowing();
                this.updateWindowLevelDisplay();
            }
        });
        
        this.canvas.addEventListener('click', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            
            // Handle measurement tools
            if (this.activeTool && this.measurementTools[this.activeTool]) {
                this.addMeasurementPoint(mouseX, mouseY);
            }
        });
        
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            
            if (e.ctrlKey) {
                // Zoom
                const zoomDelta = e.deltaY > 0 ? 0.9 : 1.1;
                this.zoomLevel = Math.max(0.1, Math.min(10, this.zoomLevel * zoomDelta));
                this.redraw();
            } else if (e.shiftKey) {
                // Magnification level
                if (this.magnificationEnabled) {
                    this.magnificationLevel = Math.max(1, Math.min(10, this.magnificationLevel + (e.deltaY > 0 ? -0.5 : 0.5)));
                    const rect = this.canvas.getBoundingClientRect();
                    const mouseX = e.clientX - rect.left;
                    const mouseY = e.clientY - rect.top;
                    this.updateMagnification(mouseX, mouseY);
                }
            }
        });
    }

    // === MISSING DICOM STANDARD METHODS ===

    toggleMeasurementUnits() {
        this.measurementUnits = this.measurementUnits === 'mm' ? 'cm' : 'mm';
        this.notyf.info(`Measurement units: ${this.measurementUnits}`);
        
        // Update existing measurements
        this.measurements.forEach(measurement => {
            if (measurement.units !== this.measurementUnits) {
                const conversionFactor = this.measurementUnits === 'cm' ? 0.1 : 10;
                measurement.result.value *= conversionFactor;
                measurement.units = this.measurementUnits;
            }
        });
        
        this.drawMeasurements();
        this.updateMeasurementsList();
    }

    clearMeasurements() {
        this.measurements = [];
        this.activeMeasurement = null;
        Object.keys(this.measurementTools).forEach(tool => {
            this.measurementTools[tool].active = false;
            this.measurementTools[tool].points = [];
        });
        this.activeTool = null;
        this.setActiveToolButton(null);
        this.redraw();
        this.notyf.info('All measurements cleared');
    }

    resetAllSettings() {
        // Reset zoom and transformations
        this.zoomLevel = 1.0;
        this.rotation = 0;
        this.flipH = false;
        this.flipV = false;
        this.panOffset = { x: 0, y: 0 };
        
        // Reset windowing to defaults
        this.windowCenter = 40;
        this.windowWidth = 400;
        
        // Reset image processing
        this.inverted = false;
        this.contrastBoost = 1.0;
        this.sharpenEnabled = false;
        this.densityEnhancement = false;
        
        // Reset tools
        this.activeTool = null;
        this.magnificationEnabled = false;
        this.magnificationCanvas.style.display = 'none';
        
        // Clear overlays
        this.clearAllOverlays();
        
        // Redraw
        this.redraw();
        this.updateWindowLevelDisplay();
        this.notyf.success('All settings reset to defaults');
    }

    clearAllOverlays() {
        this.measurements = [];
        this.annotations = [];
        this.clearMeasurements();
        this.redraw();
        this.notyf.info('All overlays cleared');
    }

    toggleSharpening() {
        this.sharpenEnabled = !this.sharpenEnabled;
        this.setActiveToolButton('sharpen');
        this.applyImageEnhancements();
        this.notyf.info(`Image sharpening ${this.sharpenEnabled ? 'enabled' : 'disabled'}`);
    }

    toggleEdgeEnhancement() {
        this.edgeEnhancement = !this.edgeEnhancement;
        this.setActiveToolButton('edge-enhancement');
        this.applyImageEnhancements();
        this.notyf.info(`Edge enhancement ${this.edgeEnhancement ? 'enabled' : 'disabled'}`);
    }

    // === ANNOTATION TOOLS ===

    startAnnotation() {
        this.activeTool = 'annotate';
        this.setActiveToolButton('annotate');
        this.notyf.info('Annotation tool - click to add text annotations');
    }

    startArrowAnnotation() {
        this.activeTool = 'arrow';
        this.setActiveToolButton('arrow');
        this.notyf.info('Arrow tool - click and drag to draw arrows');
    }

    addAnnotation(x, y, text = '') {
        if (!text) {
            text = prompt('Enter annotation text:');
            if (!text) return;
        }

        const annotation = {
            id: Date.now(),
            type: 'text',
            x: x,
            y: y,
            text: text,
            color: this.annotationColor,
            font: this.annotationFont,
            timestamp: new Date().toISOString()
        };

        this.annotations.push(annotation);
        this.drawAnnotations();
        this.notyf.success('Annotation added');
    }

    drawAnnotations() {
        this.annotations.forEach(annotation => {
            this.ctx.save();
            this.ctx.fillStyle = annotation.color;
            this.ctx.font = annotation.font;
            this.ctx.fillText(annotation.text, annotation.x, annotation.y);
            this.ctx.restore();
        });
    }

    // === CINE MODE ===

    toggleCineMode() {
        if (this.cineMode) {
            this.stopCineMode();
        } else {
            this.startCineMode();
        }
    }

    startCineMode() {
        if (!this.currentImages || this.currentImages.length < 2) {
            this.notyf.error('Need multiple images for cine mode');
            return;
        }

        this.cineMode = true;
        this.cineInterval = setInterval(() => {
            this.nextImage();
        }, this.cineSpeed || 200);

        this.notyf.info('Cine mode started');
        const playBtn = document.getElementById('play-btn');
        if (playBtn) {
            playBtn.innerHTML = '<i class="fas fa-pause"></i>';
        }
    }

    stopCineMode() {
        this.cineMode = false;
        if (this.cineInterval) {
            clearInterval(this.cineInterval);
            this.cineInterval = null;
        }

        this.notyf.info('Cine mode stopped');
        const playBtn = document.getElementById('play-btn');
        if (playBtn) {
            playBtn.innerHTML = '<i class="fas fa-play"></i>';
        }
    }

    // === UTILITY METHODS ===

    clearOverlays() {
        // Clear the canvas overlay for measurements and annotations
        this.ctx.save();
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.restore();
        
        // Redraw the image
        if (this.currentImage) {
            this.displayProcessedImage(this.currentImage.image);
        }
    }

    updateMeasurementsList() {
        const measurementsList = document.getElementById('measurements-list');
        if (!measurementsList) return;

        measurementsList.innerHTML = '';
        
        this.measurements.forEach((measurement, index) => {
            const listItem = document.createElement('div');
            listItem.className = 'measurement-item';
            listItem.innerHTML = `
                <div class="measurement-info">
                    <span class="measurement-type">${measurement.tool.charAt(0).toUpperCase() + measurement.tool.slice(1)}</span>
                    <span class="measurement-value">${measurement.result.value.toFixed(2)} ${measurement.result.unit}</span>
                </div>
                <button class="delete-measurement" onclick="dicomViewer.deleteMeasurement(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            measurementsList.appendChild(listItem);
        });
    }

    deleteMeasurement(index) {
        if (index >= 0 && index < this.measurements.length) {
            this.measurements.splice(index, 1);
            this.drawMeasurements();
            this.updateMeasurementsList();
            this.notyf.info('Measurement deleted');
        }
    }

    // === ENHANCED REDRAW METHOD ===

    redraw() {
        if (!this.currentImage) return;

        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Apply all transformations and display the image
        this.displayProcessedImage(this.currentImage.image);

        // Redraw overlays
        this.drawMeasurements();
        this.drawAnnotations();

        // Update displays
        this.updateViewportInfo();
        this.updateWindowLevelDisplay();
    }
}

// Initialize the fixed viewer when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const studyId = urlParams.get('study_id');
    
    window.fixedDicomViewer = new FixedDicomViewer(studyId);
});
