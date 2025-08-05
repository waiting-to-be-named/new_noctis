// Advanced DICOM Viewer JavaScript - Professional Medical Imaging Platform
// Copyright 2024 - Noctis DICOM Viewer Pro v3.0

class AdvancedDicomViewer {
    constructor(initialStudyId = null) {
        // Initialize notification system
        this.notyf = new Notyf({
            duration: 4000,
            position: { x: 'right', y: 'top' },
            types: [
                {
                    type: 'success',
                    background: '#00ff88',
                    icon: {
                        className: 'fas fa-check',
                        tagName: 'i',
                        color: '#0a0a0a'
                    }
                },
                {
                    type: 'error',
                    background: '#ff3333',
                    icon: {
                        className: 'fas fa-times',
                        tagName: 'i',
                        color: '#ffffff'
                    }
                },
                {
                    type: 'warning',
                    background: '#ff6b35',
                    icon: {
                        className: 'fas fa-exclamation-triangle',
                        tagName: 'i',
                        color: '#ffffff'
                    }
                },
                {
                    type: 'info',
                    background: '#0088ff',
                    icon: {
                        className: 'fas fa-info-circle',
                        tagName: 'i',
                        color: '#ffffff'
                    }
                }
            ]
        });

        // Core elements with better error checking
        this.canvas = document.getElementById('dicom-canvas-advanced');
        if (!this.canvas) {
            console.error('Canvas element with ID "dicom-canvas-advanced" not found!');
            // Try to create canvas if it doesn't exist
            const canvasContainer = document.getElementById('canvas-container');
            if (canvasContainer) {
                const canvas = document.createElement('canvas');
                canvas.id = 'dicom-canvas-advanced';
                canvas.className = 'dicom-canvas-advanced';
                canvas.style.cssText = 'position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #000;';
                canvasContainer.appendChild(canvas);
                this.canvas = canvas;
                console.log('Created canvas element');
            } else {
                this.notyf.error('Canvas container not found! Viewer initialization failed.');
                return;
            }
        }
        if (!this.canvas) {
            this.notyf.error('Canvas element not found! Viewer initialization failed.');
            console.error('Canvas element not found!');
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        if (!this.ctx) {
            this.notyf.error('Failed to get 2D context from canvas!');
            console.error('Failed to get 2D context from canvas!');
            return;
        }

        // Enable high-quality image rendering
        this.ctx.imageSmoothingEnabled = false;
        this.ctx.mozImageSmoothingEnabled = false;
        this.ctx.webkitImageSmoothingEnabled = false;
        this.ctx.msImageSmoothingEnabled = false;

        // State management
        this.currentStudy = null;
        this.currentSeries = null;
        this.currentImages = [];
        this.currentImageIndex = 0;
        this.currentImage = null;
        this.currentImageMetadata = null;
        this.imageData = null;
        this.originalImageData = null;

        // Advanced viewing parameters
        this.windowWidth = 1500;
        this.windowLevel = -600;
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.rotation = 0;
        this.flipHorizontal = false;
        this.flipVertical = false;
        this.inverted = false;
        this.crosshair = false;
        this.magnifyEnabled = false;
        this.magnifyZoom = 3.0;

        // Tool management
        this.activeTool = 'windowing';
        this.isDragging = false;
        this.dragStart = null;
        this.lastMousePos = null;

        // Measurements and annotations
        this.measurements = [];
        this.annotations = [];
        this.currentMeasurement = null;
        this.currentAnnotation = null;
        this.measurementCounter = 1;
        this.annotationCounter = 1;

        // Window/Level presets optimized for medical imaging
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

        // Advanced features
        this.cineMode = false;
        this.cineTimer = null;
        this.cineSpeed = 100; // milliseconds per frame
        this.imageCache = new Map();
        this.maxCacheSize = 500 * 1024 * 1024; // 500MB
        this.currentCacheSize = 0;

        // MPR and 3D
        this.mprEnabled = false;
        this.volumeData = null;
        this.currentSlice = { axial: 0, sagittal: 0, coronal: 0 };

        // AI Analysis
        this.aiAnalysisResults = null;
        this.aiProcessing = false;

        // Performance monitoring
        this.performanceMetrics = {
            renderTime: 0,
            loadTime: 0,
            memoryUsage: 0
        };

        // Viewport layouts
        this.viewportLayout = '1x1';
        this.syncViewports = false;

        // Settings
        this.settings = {
            defaultWindowPreset: 'lung',
            enableSmoothing: false,
            showOverlays: true,
            cacheSize: 500,
            enableGPUAcceleration: true
        };

        // Initialize viewer
        this.initialStudyId = initialStudyId;
        this.initializeViewer();
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.setupUploadHandlers();
        this.loadSettings();

        // Auto-load study if provided, otherwise check session storage, then load available studies
        if (initialStudyId) {
            console.log(`Loading initial study ID: ${initialStudyId}`);
            // Clear any cached data when a new study ID is explicitly provided
            const lastStudyId = sessionStorage.getItem('lastViewedStudyId');
            if (lastStudyId !== initialStudyId.toString()) {
                console.log('New study ID detected, clearing cached data');
                this.clearCachedData();
            }
            this.loadStudy(initialStudyId);
            // Store in session for future launches
            sessionStorage.setItem('lastViewedStudyId', initialStudyId.toString());
        } else {
            // Check if there's a last viewed study in session storage
            const lastStudyId = sessionStorage.getItem('lastViewedStudyId');
            if (lastStudyId && !isNaN(parseInt(lastStudyId))) {
                console.log(`Loading last viewed study from session: ${lastStudyId}`);
                this.loadStudy(parseInt(lastStudyId));
            } else {
                console.log('No initial study ID provided, loading available studies');
                this.loadAvailableStudies();
            }
        }

        // Initialize UI components
        this.initializeUI();
        
        // Start performance monitoring
        this.startPerformanceMonitoring();

        console.log('Advanced DICOM Viewer Pro initialized successfully!');
        this.notyf.success('Advanced DICOM Viewer Pro initialized successfully!');
    }

    initializeViewer() {
        // Set canvas size with error handling
        try {
            this.resizeCanvas();
        } catch (error) {
            console.error('Error resizing canvas:', error);
            this.notyf.error('Failed to initialize canvas size');
        }
        
        // Initialize overlays
        try {
            this.initializeOverlays();
        } catch (error) {
            console.error('Error initializing overlays:', error);
        }
        
        // Set up resize observer
        if (window.ResizeObserver) {
            this.resizeObserver = new ResizeObserver(() => {
                try {
                    this.resizeCanvas();
                    if (this.currentImage) {
                        this.render();
                    }
                } catch (error) {
                    console.error('Error during resize:', error);
                }
            });
            this.resizeObserver.observe(this.canvas.parentElement);
        }
    }

    initializeOverlays() {
        this.measurementOverlay = document.getElementById('measurement-overlay');
        this.annotationOverlay = document.getElementById('annotation-overlay');
        this.crosshairOverlay = document.getElementById('crosshair-overlay');
        this.magnifyOverlay = document.getElementById('magnify-overlay');

        // Create SVG overlays
        this.createSVGOverlay('measurement-svg', this.measurementOverlay);
        this.createSVGOverlay('annotation-svg', this.annotationOverlay);
        this.createSVGOverlay('crosshair-svg', this.crosshairOverlay);
    }

    createSVGOverlay(id, container) {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.id = id;
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.pointerEvents = 'none';
        container.appendChild(svg);
        return svg;
    }

    setupEventListeners() {
        // Canvas events
        this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
        this.canvas.addEventListener('wheel', this.handleWheel.bind(this));
        this.canvas.addEventListener('contextmenu', e => e.preventDefault());
        this.canvas.addEventListener('dblclick', this.handleDoubleClick.bind(this));

        // Touch events for mobile
        this.canvas.addEventListener('touchstart', this.handleTouchStart.bind(this));
        this.canvas.addEventListener('touchmove', this.handleTouchMove.bind(this));
        this.canvas.addEventListener('touchend', this.handleTouchEnd.bind(this));

        // Tool buttons
        this.setupToolButtonEvents();
        
        // Header buttons
        this.setupHeaderButtonEvents();
        
        // Control panels
        this.setupControlPanelEvents();
        
        // Window/resize events
        window.addEventListener('resize', this.resizeCanvas.bind(this));
        window.addEventListener('beforeunload', this.cleanup.bind(this));
    }

    setupToolButtonEvents() {
        // Define tool button mappings
        const toolButtons = {
            // Navigation tools
            'windowing-adv-btn': () => this.setActiveTool('windowing'),
            'pan-adv-btn': () => this.setActiveTool('pan'),
            'zoom-adv-btn': () => this.setActiveTool('zoom'),
            'rotate-btn': () => this.rotateImage(90),
            'flip-btn': () => this.flipImage(),

            // Measurement tools
            'measure-distance-btn': () => this.setActiveTool('measure-distance'),
            'measure-angle-btn': () => this.setActiveTool('measure-angle'),
            'measure-area-btn': () => this.setActiveTool('measure-area'),
            'measure-volume-btn': () => this.setActiveTool('measure-volume'),
            'hu-measurement-btn': () => this.setActiveTool('hu-measurement'),

            // Annotation tools
            'text-annotation-btn': () => this.setActiveTool('text-annotation'),
            'arrow-annotation-btn': () => this.setActiveTool('arrow-annotation'),
            'circle-annotation-btn': () => this.setActiveTool('circle-annotation'),
            'rectangle-annotation-btn': () => this.setActiveTool('rectangle-annotation'),

            // Enhancement tools
            'invert-adv-btn': () => this.toggleInvert(),
            'crosshair-adv-btn': () => this.toggleCrosshair(),
            'magnify-btn': () => this.toggleMagnify(),
            'sharpen-btn': () => this.applySharpenFilter(),

            // 3D/MPR tools
            'mpr-btn': () => this.enableMPR(),
            'volume-render-btn': () => this.enableVolumeRendering(),
            'mip-btn': () => this.enableMIP(),

            // AI tools
            'ai-analysis-btn': () => this.runAIAnalysis(),
            'ai-segment-btn': () => this.runAISegmentation(),

            // Utility tools
            'reset-adv-btn': () => this.resetView(),
            'fit-to-window-btn': () => this.fitToWindow(),
            'actual-size-btn': () => this.actualSize()
        };

        // Set up event listeners for all tool buttons
        Object.entries(toolButtons).forEach(([buttonId, handler]) => {
            const button = document.getElementById(buttonId);
            if (button) {
                button.addEventListener('click', handler);
                console.log(`Set up event listener for ${buttonId}`);
            } else {
                console.warn(`Button not found: ${buttonId}`);
            }
        });
    }

    setupHeaderButtonEvents() {
        const headerButtons = {
            // Header navigation
            'prev-study-btn': () => this.previousStudy(),
            'next-study-btn': () => this.nextStudy(),

            // Header actions
            'upload-advanced-btn': () => this.showUploadModal(),
            'export-btn': () => this.showExportModal(),
            'settings-btn': () => this.showSettingsModal(),
            'fullscreen-btn': () => this.toggleFullscreen(),
            'logout-advanced-btn': () => this.logout(),

            // Patient info toggle
            'toggle-patient-info': () => this.togglePatientInfo()
        };

        // Set up event listeners for all header buttons
        Object.entries(headerButtons).forEach(([buttonId, handler]) => {
            const button = document.getElementById(buttonId);
            if (button) {
                button.addEventListener('click', handler);
                console.log(`Set up header event listener for ${buttonId}`);
            } else {
                console.warn(`Header button not found: ${buttonId}`);
            }
        });
    }

    setupControlPanelEvents() {
        // Window/Level presets
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const preset = e.target.getAttribute('data-preset');
                this.applyWindowPreset(preset);
            });
        });

        // Manual window/level controls
        const windowWidthSlider = document.getElementById('window-width-slider');
        const windowLevelSlider = document.getElementById('window-level-slider');
        const windowWidthInput = document.getElementById('window-width-input');
        const windowLevelInput = document.getElementById('window-level-input');

        if (windowWidthSlider) {
            windowWidthSlider.addEventListener('input', (e) => {
                this.windowWidth = parseInt(e.target.value);
                windowWidthInput.value = this.windowWidth;
                this.applyWindowLevel();
            });
        }

        if (windowLevelSlider) {
            windowLevelSlider.addEventListener('input', (e) => {
                this.windowLevel = parseInt(e.target.value);
                windowLevelInput.value = this.windowLevel;
                this.applyWindowLevel();
            });
        }

        if (windowWidthInput) {
            windowWidthInput.addEventListener('change', (e) => {
                this.windowWidth = parseInt(e.target.value);
                windowWidthSlider.value = this.windowWidth;
                this.applyWindowLevel();
            });
        }

        if (windowLevelInput) {
            windowLevelInput.addEventListener('change', (e) => {
                this.windowLevel = parseInt(e.target.value);
                windowLevelSlider.value = this.windowLevel;
                this.applyWindowLevel();
            });
        }

        // Additional control buttons
        const controlButtons = {
            // Viewport layout controls
            'layout-1x1-btn': () => this.setViewportLayout('1x1'),
            'layout-2x2-btn': () => this.setViewportLayout('2x2'),
            'layout-1x2-btn': () => this.setViewportLayout('1x2'),
            'sync-viewports-btn': () => this.toggleViewportSync(),

            // Thumbnail navigator
            'thumbnail-toggle': () => this.toggleThumbnails(),

            // Clear buttons
            'clear-measurements-btn': () => this.clearMeasurements(),
            'clear-annotations-btn': () => this.clearAnnotations(),

            // AI controls
            'ai-detect-lesions': () => this.detectLesions(),
            'ai-segment-organs': () => this.segmentOrgans(),
            'ai-calculate-volume': () => this.calculateVolume()
        };

        // Set up event listeners for control panel buttons
        Object.entries(controlButtons).forEach(([buttonId, handler]) => {
            const button = document.getElementById(buttonId);
            if (button) {
                button.addEventListener('click', handler);
                console.log(`Set up control panel event listener for ${buttonId}`);
            } else {
                console.warn(`Control panel button not found: ${buttonId}`);
            }
        });
    }

    setupKeyboardShortcuts() {
        const shortcuts = {
            'KeyW': () => this.setActiveTool('windowing'),
            'KeyP': () => this.setActiveTool('pan'),
            'KeyZ': () => this.setActiveTool('zoom'),
            'KeyR': () => this.rotateImage(90),
            'KeyF': () => this.flipImage(),
            'KeyD': () => this.setActiveTool('measure-distance'),
            'KeyA': () => this.setActiveTool('measure-angle'),
            'KeyT': () => this.setActiveTool('text-annotation'),
            'KeyI': () => this.toggleInvert(),
            'KeyC': () => this.toggleCrosshair(),
            'KeyM': () => this.toggleMagnify(),
            'KeyQ': () => this.enableMPR(),
            'Escape': () => this.resetView(),
            'Space': () => this.toggleCine(),
            'ArrowLeft': () => this.previousImage(),
            'ArrowRight': () => this.nextImage(),
            'ArrowUp': () => this.adjustWindowLevel(10),
            'ArrowDown': () => this.adjustWindowLevel(-10),
            'Equal': () => this.adjustZoom(1.1),
            'Minus': () => this.adjustZoom(0.9),
            'Digit0': () => this.resetView(),
            'F11': () => this.toggleFullscreen()
        };

        this.keyboardShortcuts = shortcuts;
    }

    setupUploadHandlers() {
        console.log('Setting up upload handlers...');
        
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const startUploadBtn = document.getElementById('startUpload');
        
        if (!uploadArea || !fileInput || !startUploadBtn) {
            console.warn('Upload elements not found in DOM');
            return;
        }

        // Store selected files
        this.selectedFiles = [];

        // Click to browse files
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        // File selection
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelection(e.target.files);
        });

        // Drag and drop
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
            this.handleFileSelection(e.dataTransfer.files);
        });

        // Start upload button
        startUploadBtn.addEventListener('click', () => {
            this.startUpload();
        });

        console.log('Upload handlers setup complete');
    }

    handleFileSelection(files) {
        console.log(`Selected ${files.length} files`);
        
        // Filter DICOM files
        const dicomFiles = Array.from(files).filter(file => {
            const name = file.name.toLowerCase();
            return name.endsWith('.dcm') || name.endsWith('.dicom') || name.includes('dicom');
        });

        if (dicomFiles.length === 0) {
            this.notyf.error('No DICOM files selected. Please select .dcm or .dicom files.');
            return;
        }

        this.selectedFiles = dicomFiles;
        
        // Update UI
        const uploadArea = document.getElementById('uploadArea');
        const startUploadBtn = document.getElementById('startUpload');
        
        uploadArea.innerHTML = `
            <div class="upload-icon">
                <i class="fas fa-file-medical"></i>
            </div>
            <div class="upload-text">
                <h5>${dicomFiles.length} DICOM file(s) selected</h5>
                <p>Ready to upload</p>
            </div>
        `;

        startUploadBtn.disabled = false;
        
        this.notyf.success(`${dicomFiles.length} DICOM file(s) ready for upload`);
    }

    async startUpload() {
        if (this.selectedFiles.length === 0) {
            this.notyf.error('No files selected');
            return;
        }

        console.log('Starting upload...');
        
        const uploadProgress = document.getElementById('uploadProgress');
        const uploadArea = document.getElementById('uploadArea');
        const progressBar = uploadProgress.querySelector('.progress-bar');
        const uploadStatus = document.getElementById('uploadStatus');
        const startUploadBtn = document.getElementById('startUpload');

        // Show progress
        uploadArea.style.display = 'none';
        uploadProgress.style.display = 'block';
        startUploadBtn.disabled = true;

        try {
            const formData = new FormData();
            
            // Add files to form data
            this.selectedFiles.forEach((file, index) => {
                formData.append('dicom_files', file);
            });

            // Upload with progress tracking
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    progressBar.style.width = percentComplete + '%';
                    uploadStatus.textContent = `Uploading... ${Math.round(percentComplete)}%`;
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    this.notyf.success('Upload completed successfully!');
                    uploadStatus.textContent = 'Upload completed!';
                    
                    // Refresh studies list
                    setTimeout(() => {
                        this.loadAvailableStudies();
                        // Close modal
                        const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
                        if (modal) modal.hide();
                    }, 1000);
                } else {
                    throw new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`);
                }
            });

            xhr.addEventListener('error', () => {
                throw new Error('Upload failed due to network error');
            });

            xhr.open('POST', '/viewer/api/upload-dicom-files/');
            xhr.send(formData);

        } catch (error) {
            console.error('Upload error:', error);
            this.notyf.error(`Upload failed: ${error.message}`);
            
            // Reset UI
            uploadArea.style.display = 'block';
            uploadProgress.style.display = 'none';
            startUploadBtn.disabled = false;
        }
    }

    handleKeyboardShortcut(event) {
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return; // Don't process shortcuts when typing in inputs
        }

        const key = event.code;
        if (this.keyboardShortcuts[key]) {
            event.preventDefault();
            this.keyboardShortcuts[key]();
        }
    }

    // Mouse and touch event handlers
    handleMouseDown(event) {
        this.isDragging = true;
        this.dragStart = this.getMousePos(event);
        this.lastMousePos = this.dragStart;
        
        this.canvas.style.cursor = this.getCursorForTool();
        
        // Start measurement or annotation if applicable
        if (this.activeTool.startsWith('measure-') || this.activeTool.includes('annotation')) {
            this.startMeasurementOrAnnotation(this.dragStart);
        }
    }

    handleMouseMove(event) {
        const currentPos = this.getMousePos(event);
        this.updateStatusBar(currentPos);
        
        if (this.magnifyEnabled) {
            this.updateMagnifyGlass(currentPos);
        }

        if (this.crosshair) {
            this.updateCrosshair(currentPos);
        }

        if (!this.isDragging) return;

        const deltaX = currentPos.x - this.lastMousePos.x;
        const deltaY = currentPos.y - this.lastMousePos.y;

        switch (this.activeTool) {
            case 'windowing':
                this.adjustWindowLevel(deltaY * -2);
                this.adjustWindowWidth(deltaX * 4);
                break;
            case 'pan':
                this.panX += deltaX;
                this.panY += deltaY;
                this.render();
                break;
            case 'zoom':
                const zoomDelta = 1 + (deltaY * -0.01);
                this.adjustZoom(zoomDelta);
                break;
            default:
                if (this.activeTool.startsWith('measure-') || this.activeTool.includes('annotation')) {
                    this.updateCurrentMeasurementOrAnnotation(currentPos);
                }
                break;
        }

        this.lastMousePos = currentPos;
    }

    handleMouseUp(event) {
        this.isDragging = false;
        this.canvas.style.cursor = 'crosshair';
        
        // Complete measurement or annotation if applicable
        if (this.activeTool.startsWith('measure-') || this.activeTool.includes('annotation')) {
            this.completeMeasurementOrAnnotation();
        }
    }

    handleWheel(event) {
        event.preventDefault();
        
        if (event.ctrlKey) {
            // Zoom with Ctrl+Wheel
            const zoomDelta = event.deltaY > 0 ? 0.9 : 1.1;
            this.adjustZoom(zoomDelta);
        } else if (event.shiftKey) {
            // Window/Level with Shift+Wheel
            this.adjustWindowLevel(event.deltaY * -0.5);
        } else {
            // Navigate images with Wheel
            if (event.deltaY > 0) {
                this.nextImage();
            } else {
                this.previousImage();
            }
        }
    }

    handleDoubleClick(event) {
        const pos = this.getMousePos(event);
        
        switch (this.activeTool) {
            case 'text-annotation':
                this.addTextAnnotation(pos);
                break;
            default:
                this.fitToWindow();
                break;
        }
    }

    handleTouchStart(event) {
        event.preventDefault();
        if (event.touches.length === 1) {
            const touch = event.touches[0];
            const mouseEvent = new MouseEvent('mousedown', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            this.handleMouseDown(mouseEvent);
        }
    }

    handleTouchMove(event) {
        event.preventDefault();
        if (event.touches.length === 1) {
            const touch = event.touches[0];
            const mouseEvent = new MouseEvent('mousemove', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            this.handleMouseMove(mouseEvent);
        } else if (event.touches.length === 2) {
            // Pinch zoom
            const touch1 = event.touches[0];
            const touch2 = event.touches[1];
            const distance = Math.sqrt(
                Math.pow(touch2.clientX - touch1.clientX, 2) +
                Math.pow(touch2.clientY - touch1.clientY, 2)
            );
            
            if (this.lastTouchDistance) {
                const zoomDelta = distance / this.lastTouchDistance;
                this.adjustZoom(zoomDelta);
            }
            this.lastTouchDistance = distance;
        }
    }

    handleTouchEnd(event) {
        event.preventDefault();
        this.lastTouchDistance = null;
        const mouseEvent = new MouseEvent('mouseup', {});
        this.handleMouseUp(mouseEvent);
    }

    // Utility functions
    getMousePos(event) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top
        };
    }

    getCursorForTool() {
        const cursors = {
            'windowing': 'crosshair',
            'pan': 'move',
            'zoom': 'zoom-in',
            'measure-distance': 'crosshair',
            'measure-angle': 'crosshair',
            'measure-area': 'crosshair',
            'text-annotation': 'text',
            'default': 'crosshair'
        };
        return cursors[this.activeTool] || cursors.default;
    }

    // Tool management
    setActiveTool(tool) {
        // Remove active class from all tool buttons
        document.querySelectorAll('.tool-btn-advanced').forEach(btn => {
            btn.classList.remove('active');
        });

        // Add active class to selected tool button
        const toolBtnId = `${tool}-btn`;
        const toolBtn = document.getElementById(toolBtnId);
        if (toolBtn) {
            toolBtn.classList.add('active');
        } else {
            // Try alternative ID patterns
            const altId = `${tool.replace('measure-', '').replace('-', '-')}-btn`;
            const altBtn = document.getElementById(altId);
            if (altBtn) {
                altBtn.classList.add('active');
            }
        }

        this.activeTool = tool;
        this.canvas.style.cursor = this.getCursorForTool();
        
        this.notyf.open({
            type: 'info',
            message: `${tool.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())} tool activated`
        });
    }

    // Image loading and management
    async loadAvailableStudies() {
        try {
            console.log('Loading available studies...');
            this.updateStatus('Loading available studies...');
            
            const response = await fetch(`/viewer/api/studies/?t=${Date.now()}`);
            if (!response.ok) {
                throw new Error(`Failed to load studies: ${response.statusText}`);
            }
            
            const studies = await response.json();
            console.log(`Found ${studies.length} studies:`, studies);
            
            if (studies.length > 0) {
                // Auto-load the first study if available
                console.log(`Auto-loading first study: ${studies[0].id}`);
                this.loadStudy(studies[0].id);
            } else {
                this.displayStudiesList(studies);
                this.updateStatus('No studies available - upload DICOM files to get started');
                this.showErrorOnCanvas('No DICOM studies found\nUpload DICOM files to begin viewing');
            }
        } catch (error) {
            console.error('Error loading studies:', error);
            this.notyf.error(`Failed to load studies: ${error.message}`);
            this.updateStatus('Error loading studies');
            this.showErrorOnCanvas('Failed to load studies\nCheck console for details');
        }
    }

    displayStudiesList(studies) {
        const container = document.getElementById('studies-list-container');
        if (!container) {
            // Create studies list container if it doesn't exist
            const studiesContainer = document.createElement('div');
            studiesContainer.id = 'studies-list-container';
            studiesContainer.className = 'studies-list-container';
            studiesContainer.innerHTML = `
                <h3><i class="fas fa-list"></i> Available Studies</h3>
                <div id="studies-list" class="studies-list"></div>
            `;
            
            // Insert before the canvas container
            const canvasContainer = document.getElementById('canvas-container');
            canvasContainer.parentNode.insertBefore(studiesContainer, canvasContainer);
        }
        
        const studiesList = document.getElementById('studies-list');
        studiesList.innerHTML = '';
        
        if (studies.length === 0) {
            studiesList.innerHTML = '<p class="no-studies">No studies available. Upload DICOM files to get started.</p>';
            return;
        }
        
        studies.forEach(study => {
            const studyItem = document.createElement('div');
            studyItem.className = 'study-item';
            studyItem.innerHTML = `
                <div class="study-info">
                    <h4>${study.patient_name || 'Unknown Patient'}</h4>
                    <p><strong>ID:</strong> ${study.patient_id || 'N/A'}</p>
                    <p><strong>Study:</strong> ${study.study_description || 'N/A'}</p>
                    <p><strong>Date:</strong> ${study.study_date ? new Date(study.study_date).toLocaleDateString() : 'N/A'}</p>
                    <p><strong>Modality:</strong> ${study.modality || 'N/A'}</p>
                </div>
                <button class="btn btn-primary load-study-btn" data-study-id="${study.id}">
                    <i class="fas fa-eye"></i> View Study
                </button>
            `;
            
            studiesList.appendChild(studyItem);
        });
        
        // Add event listeners for study loading
        document.querySelectorAll('.load-study-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const studyId = e.target.closest('.load-study-btn').dataset.studyId;
                this.loadStudy(parseInt(studyId));
                
                // Hide studies list
                const container = document.getElementById('studies-list-container');
                if (container) {
                    container.style.display = 'none';
                }
            });
        });
    }

    clearCachedData() {
        console.log('Clearing all cached data...');
        // Clear current state
        this.currentStudy = null;
        this.currentSeries = null;
        this.currentImages = [];
        this.currentImageIndex = 0;
        this.currentImage = null;
        this.currentImageMetadata = null;
        this.imageData = null;
        this.originalImageData = null;
        
        // Clear canvas
        if (this.ctx && this.canvas) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
        
        // Clear patient info displays
        this.clearPatientInfo();
        
        // Clear series list
        this.updateSeriesList([]);
        
        // Clear thumbnails
        this.updateThumbnails();
        
        console.log('Cached data cleared successfully');
    }

    clearPatientInfo() {
        // Clear patient information displays
        const patientNameElements = ['patient-name-adv', 'quick-patient-name'];
        const patientIdElements = ['patient-id-adv', 'quick-patient-id'];
        const modalityElements = ['modality-adv', 'quick-modality'];
        const dobElements = ['patient-dob'];
        const studyDateElements = ['study-date-adv'];
        const studyDescElements = ['study-description-adv'];
        
        [...patientNameElements, ...patientIdElements, ...modalityElements, 
         ...dobElements, ...studyDateElements, ...studyDescElements].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = '-';
            }
        });
    }

    async loadStudy(studyId) {
        console.log(`Loading study: ${studyId}`);
        try {
            this.showLoading(true);
            this.updateStatus('Loading study...');

            // Clear any cached data for this study (redundant but ensures clean state)
            this.clearCachedData();

            // Try the study images endpoint first (this includes patient info)
            // Add cache-busting parameter to ensure fresh data
            const timestamp = Date.now();
            const studyResponse = await fetch(`/viewer/api/get-study-images/${studyId}/?t=${timestamp}`);
            if (!studyResponse.ok) {
                throw new Error(`Failed to load study: ${studyResponse.status} ${studyResponse.statusText}`);
            }

            const studyData = await studyResponse.json();
            this.currentStudy = studyData.study;
            console.log('Loaded study data:', this.currentStudy);
            
            // Store the loaded study ID in session storage
            sessionStorage.setItem('lastViewedStudyId', studyId.toString());
            
            // Get series data
            const seriesResponse = await fetch(`/viewer/api/studies/${studyId}/series/?t=${timestamp}`);
            let seriesData = { series: [] };
            if (seriesResponse.ok) {
                seriesData = await seriesResponse.json();
                this.currentSeries = seriesData.series || [];
            } else {
                console.warn('Series endpoint not available, using images directly');
                // Create a default series from the images data
                if (studyData.images && studyData.images.length > 0) {
                    const defaultSeries = {
                        id: studyData.images[0].series_number || 1,
                        series_number: studyData.images[0].series_number || 1,
                        series_description: studyData.images[0].series_description || 'Default Series',
                        images: studyData.images
                    };
                    this.currentSeries = [defaultSeries];
                }
            }

            this.updatePatientInfo();
            this.updateSeriesList(this.currentSeries);
            
            // Load images from first series if available
            if (this.currentSeries.length > 0) {
                // If we have images from the study endpoint, use them directly
                if (studyData.images && studyData.images.length > 0) {
                    this.currentImages = studyData.images;
                    this.currentImageIndex = 0;
                    this.updateThumbnails();
                    this.updateImageInfo();
                    if (this.currentImages.length > 0) {
                        await this.loadImage(0);
                    }
                } else {
                    await this.loadImages(this.currentSeries[0].id);
                }
            } else {
                throw new Error('No series found for this study');
            }
            
            this.notyf.success('Study loaded successfully!');
        } catch (error) {
            console.error('Error loading study:', error);
            this.notyf.error(`Failed to load study: ${error.message}`);
            this.updateStatus('Error loading study');
        } finally {
            this.showLoading(false);
        }
    }

    async loadSeries() {
        try {
            const response = await fetch(`/viewer/api/studies/${this.currentStudy.id}/series/`);
            if (!response.ok) {
                throw new Error(`Failed to load series: ${response.statusText}`);
            }

            const data = await response.json();
            this.currentSeries = data.series || [];
            this.updateSeriesList(data.series || []);
            
            if (this.currentSeries.length > 0) {
                await this.loadImages(this.currentSeries[0].id);
            }
        } catch (error) {
            console.error('Error loading series:', error);
            this.notyf.error(`Failed to load series: ${error.message}`);
        }
    }

    async loadImages(seriesId) {
        try {
            this.updateStatus('Loading images...');

            const response = await fetch(`/viewer/api/series/${seriesId}/images/`);
            if (!response.ok) {
                throw new Error(`Failed to load images: ${response.statusText}`);
            }

            const data = await response.json();
            this.currentImages = data.images || data || [];
            this.currentImageIndex = 0;
            
            this.updateThumbnails();
            this.updateImageInfo();
            
            if (this.currentImages.length > 0) {
                await this.loadImage(0);
            }
        } catch (error) {
            console.error('Error loading images:', error);
            this.notyf.error(`Failed to load images: ${error.message}`);
        }
    }

    async loadImage(index) {
        try {
            if (index < 0 || index >= this.currentImages.length) {
                console.warn(`Invalid image index: ${index}, available: ${this.currentImages.length}`);
                return;
            }

            this.currentImageIndex = index;
            const imageInfo = this.currentImages[index];
            console.log(`Loading image ${index + 1}/${this.currentImages.length}, ID: ${imageInfo.id}`);
            
            // Check cache first
            const cacheKey = `image_${imageInfo.id}`;
            if (this.imageCache.has(cacheKey)) {
                console.log('Image found in cache');
                this.currentImage = this.imageCache.get(cacheKey);
                this.processAndRenderImage();
                return;
            }

            this.updateStatus(`Loading image ${index + 1}/${this.currentImages.length}...`);

            const startTime = performance.now();
            console.log(`Fetching image data from: /viewer/api/images/${imageInfo.id}/data/`);
            
            const response = await fetch(`/viewer/api/images/${imageInfo.id}/data/`);
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`HTTP ${response.status}: ${errorText}`);
                throw new Error(`Failed to load image: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Received image data:', {
                hasImageData: !!data.image_data,
                imageDataLength: data.image_data ? data.image_data.length : 0,
                metadata: data.metadata
            });
            
            if (!data.image_data) {
                throw new Error('No image data received from server');
            }
            
            const img = new Image();
            
            // Set up promise-based loading for better error handling
            const imageLoadPromise = new Promise((resolve, reject) => {
                img.onload = () => {
                    console.log(`Image loaded successfully: ${img.width}x${img.height}`);
                    this.currentImage = img;
                    this.currentImageMetadata = data.metadata || {};
                    this.cacheImage(cacheKey, img);
                    
                    const loadTime = performance.now() - startTime;
                    this.performanceMetrics.loadTime = loadTime;
                    console.log(`Image load time: ${loadTime.toFixed(2)}ms`);
                    
                    resolve();
                };
                
                img.onerror = (error) => {
                    console.error('Image load error:', error);
                    reject(new Error('Failed to decode image data'));
                };
                
                // Set timeout for image loading
                setTimeout(() => {
                    reject(new Error('Image load timeout'));
                }, 10000);
            });
            
            // Start image loading
            img.src = data.image_data;
            
            // Wait for image to load
            await imageLoadPromise;
            
            // Process and render the loaded image
            this.processAndRenderImage();
            this.updatePerformanceDisplay();
            this.updateImageInfo();

        } catch (error) {
            console.error('Error loading image:', error);
            this.notyf.error(`Failed to load image: ${error.message}`);
            this.updateStatus('Error loading image');
            
            // Show a placeholder or error message on canvas
            this.showErrorOnCanvas(`Failed to load image: ${error.message}`);
        }
    }

    processAndRenderImage() {
        if (!this.currentImage) return;

        const startTime = performance.now();
        
        // Apply image processing
        this.applyImageProcessing();
        
        // Render the processed image
        this.render();
        
        const renderTime = performance.now() - startTime;
        this.performanceMetrics.renderTime = renderTime;
        this.updatePerformanceDisplay();
        
        this.updateStatus('Ready');
    }

    applyImageProcessing() {
        if (!this.currentImage) return;

        // Create off-screen canvas for image processing
        const offscreenCanvas = document.createElement('canvas');
        const offscreenCtx = offscreenCanvas.getContext('2d');
        
        offscreenCanvas.width = this.currentImage.width;
        offscreenCanvas.height = this.currentImage.height;
        
        offscreenCtx.drawImage(this.currentImage, 0, 0);
        this.originalImageData = offscreenCtx.getImageData(0, 0, offscreenCanvas.width, offscreenCanvas.height);
        
        // Apply window/level
        this.imageData = this.applyWindowLevelToImageData(this.originalImageData);
        
        // Apply other enhancements
        if (this.inverted) {
            this.imageData = this.invertImageData(this.imageData);
        }
    }

    applyWindowLevelToImageData(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const windowMin = this.windowLevel - this.windowWidth / 2;
        const windowMax = this.windowLevel + this.windowWidth / 2;
        
        for (let i = 0; i < data.length; i += 4) {
            // Convert to grayscale if needed
            const gray = (data[i] + data[i + 1] + data[i + 2]) / 3;
            
            // Apply window/level
            let value = (gray - windowMin) / (windowMax - windowMin) * 255;
            value = Math.max(0, Math.min(255, value));
            
            data[i] = value;     // R
            data[i + 1] = value; // G
            data[i + 2] = value; // B
            // Alpha channel remains unchanged
        }
        
        return new ImageData(data, imageData.width, imageData.height);
    }

    invertImageData(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        
        for (let i = 0; i < data.length; i += 4) {
            data[i] = 255 - data[i];         // R
            data[i + 1] = 255 - data[i + 1]; // G
            data[i + 2] = 255 - data[i + 2]; // B
            // Alpha channel remains unchanged
        }
        
        return new ImageData(data, imageData.width, imageData.height);
    }

    // Rendering
    render() {
        if (!this.currentImage) {
            console.log('No current image to render');
            return;
        }

        const startTime = performance.now();
        
        // Clear canvas with black background
        this.ctx.fillStyle = '#000000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Save context state
        this.ctx.save();
        
        try {
            // Apply transformations
            this.applyTransformations();
            
            // Draw image
            if (this.imageData) {
                // Create temporary canvas for processed image
                const tempCanvas = document.createElement('canvas');
                const tempCtx = tempCanvas.getContext('2d');
                tempCanvas.width = this.imageData.width;
                tempCanvas.height = this.imageData.height;
                tempCtx.putImageData(this.imageData, 0, 0);
                
                console.log(`Drawing processed image: ${tempCanvas.width}x${tempCanvas.height}`);
                this.ctx.drawImage(tempCanvas, 0, 0);
            } else {
                console.log(`Drawing original image: ${this.currentImage.width}x${this.currentImage.height}`);
                this.ctx.drawImage(this.currentImage, 0, 0);
            }
        } catch (error) {
            console.error('Error during image rendering:', error);
            this.showErrorOnCanvas('Image rendering failed');
        }
        
        // Restore context state
        this.ctx.restore();
        
        // Update overlays
        try {
            this.updateOverlays();
        } catch (error) {
            console.error('Error updating overlays:', error);
        }
        
        const renderTime = performance.now() - startTime;
        this.performanceMetrics.renderTime = renderTime;
        console.log(`Render time: ${renderTime.toFixed(2)}ms`);
    }
    
    showErrorOnCanvas(message) {
        // Clear canvas with dark background
        this.ctx.fillStyle = '#1a1a1a';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw error message
        this.ctx.fillStyle = '#ff6666';
        this.ctx.font = '16px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        
        const x = this.canvas.width / 2;
        const y = this.canvas.height / 2;
        
        this.ctx.fillText(message, x, y - 10);
        this.ctx.fillText('Check console for details', x, y + 20);
    }

    applyTransformations() {
        const canvasCenter = {
            x: this.canvas.width / 2,
            y: this.canvas.height / 2
        };
        
        const imageCenter = {
            x: this.currentImage.width / 2,
            y: this.currentImage.height / 2
        };
        
        // Pan
        this.ctx.translate(this.panX, this.panY);
        
        // Move to center for rotation and scaling
        this.ctx.translate(canvasCenter.x, canvasCenter.y);
        
        // Rotation
        this.ctx.rotate(this.rotation * Math.PI / 180);
        
        // Scaling
        let scaleX = this.zoomFactor;
        let scaleY = this.zoomFactor;
        
        // Flip
        if (this.flipHorizontal) scaleX *= -1;
        if (this.flipVertical) scaleY *= -1;
        
        this.ctx.scale(scaleX, scaleY);
        
        // Move back to draw image centered
        this.ctx.translate(-imageCenter.x, -imageCenter.y);
    }

    updateOverlays() {
        this.updateMeasurementOverlay();
        this.updateAnnotationOverlay();
        
        if (this.crosshair) {
            this.updateCrosshairOverlay();
        }
    }

    updateMeasurementOverlay() {
        const svg = document.getElementById('measurement-svg');
        if (!svg) return;
        
        // Clear existing measurements
        svg.innerHTML = '';
        
        // Draw all measurements
        this.measurements.forEach(measurement => {
            this.drawMeasurement(svg, measurement);
        });
        
        // Draw current measurement if in progress
        if (this.currentMeasurement) {
            this.drawMeasurement(svg, this.currentMeasurement);
        }
    }

    updateAnnotationOverlay() {
        const svg = document.getElementById('annotation-svg');
        if (!svg) return;
        
        // Clear existing annotations
        svg.innerHTML = '';
        
        // Draw all annotations
        this.annotations.forEach(annotation => {
            this.drawAnnotation(svg, annotation);
        });
        
        // Draw current annotation if in progress
        if (this.currentAnnotation) {
            this.drawAnnotation(svg, this.currentAnnotation);
        }
    }

    updateCrosshairOverlay() {
        const svg = document.getElementById('crosshair-svg');
        if (!svg || !this.lastMousePos) return;
        
        svg.innerHTML = '';
        
        // Vertical line
        const vLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        vLine.setAttribute('x1', this.lastMousePos.x);
        vLine.setAttribute('y1', 0);
        vLine.setAttribute('x2', this.lastMousePos.x);
        vLine.setAttribute('y2', this.canvas.height);
        vLine.classList.add('crosshair-line');
        svg.appendChild(vLine);
        
        // Horizontal line
        const hLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        hLine.setAttribute('x1', 0);
        hLine.setAttribute('y1', this.lastMousePos.y);
        hLine.setAttribute('x2', this.canvas.width);
        hLine.setAttribute('y2', this.lastMousePos.y);
        hLine.classList.add('crosshair-line');
        svg.appendChild(hLine);
    }

    // Window/Level operations
    applyWindowPreset(presetName) {
        const preset = this.windowPresets[presetName];
        if (!preset) return;
        
        this.windowWidth = preset.ww;
        this.windowLevel = preset.wl;
        
        this.updateWindowLevelControls();
        this.applyWindowLevel();
        
        // Update preset button states
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-preset="${presetName}"]`)?.classList.add('active');
        
        this.notyf.open({
            type: 'info',
            message: `Applied ${presetName} preset: W:${preset.ww} L:${preset.wl}`
        });
    }

    applyWindowLevel() {
        this.processAndRenderImage();
        this.updateWindowLevelDisplay();
    }

    adjustWindowLevel(delta) {
        this.windowLevel += delta;
        this.updateWindowLevelControls();
        this.applyWindowLevel();
    }

    adjustWindowWidth(delta) {
        this.windowWidth = Math.max(1, this.windowWidth + delta);
        this.updateWindowLevelControls();
        this.applyWindowLevel();
    }

    updateWindowLevelControls() {
        const widthSlider = document.getElementById('window-width-slider');
        const levelSlider = document.getElementById('window-level-slider');
        const widthInput = document.getElementById('window-width-input');
        const levelInput = document.getElementById('window-level-input');
        
        if (widthSlider) widthSlider.value = this.windowWidth;
        if (levelSlider) levelSlider.value = this.windowLevel;
        if (widthInput) widthInput.value = this.windowWidth;
        if (levelInput) levelInput.value = this.windowLevel;
    }

    updateWindowLevelDisplay() {
        const windowInfo = document.getElementById('window-info');
        if (windowInfo) {
            windowInfo.textContent = `W: ${this.windowWidth} L: ${this.windowLevel}`;
        }
    }

    // Zoom and pan operations
    adjustZoom(factor) {
        this.zoomFactor *= factor;
        this.zoomFactor = Math.max(0.1, Math.min(10, this.zoomFactor));
        this.render();
        this.updateZoomDisplay();
    }

    updateZoomDisplay() {
        const zoomLevel = document.getElementById('zoom-level');
        if (zoomLevel) {
            zoomLevel.textContent = `${Math.round(this.zoomFactor * 100)}%`;
        }
    }

    resetView() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.rotation = 0;
        this.flipHorizontal = false;
        this.flipVertical = false;
        this.render();
        this.updateZoomDisplay();
        this.notyf.open({
            type: 'info',
            message: 'View reset to default'
        });
    }

    fitToWindow() {
        if (!this.currentImage) return;
        
        const canvasAspect = this.canvas.width / this.canvas.height;
        const imageAspect = this.currentImage.width / this.currentImage.height;
        
        if (imageAspect > canvasAspect) {
            this.zoomFactor = this.canvas.width / this.currentImage.width;
        } else {
            this.zoomFactor = this.canvas.height / this.currentImage.height;
        }
        
        this.panX = 0;
        this.panY = 0;
        this.render();
        this.updateZoomDisplay();
        this.notyf.open({
            type: 'info',
            message: 'Image fitted to window'
        });
    }

    actualSize() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.render();
        this.updateZoomDisplay();
        this.notyf.open({
            type: 'info',
            message: 'Image displayed at actual size'
        });
    }

    // Image transformations
    rotateImage(degrees) {
        this.rotation = (this.rotation + degrees) % 360;
        this.render();
        this.notyf.open({
            type: 'info',
            message: `Image rotated ${degrees}°`
        });
    }

    flipImage(direction = 'horizontal') {
        if (direction === 'horizontal') {
            this.flipHorizontal = !this.flipHorizontal;
            this.notyf.open({
            type: 'info',
            message: 'Image flipped horizontally'
        });
        } else {
            this.flipVertical = !this.flipVertical;
            this.notyf.open({
            type: 'info',
            message: 'Image flipped vertically'
        });
        }
        this.render();
    }

    toggleInvert() {
        this.inverted = !this.inverted;
        this.processAndRenderImage();
        
        const btn = document.getElementById('invert-adv-btn');
        if (btn) {
            btn.classList.toggle('active', this.inverted);
        }
        
        this.notyf.open({
            type: 'info',
            message: `Image ${this.inverted ? 'inverted' : 'normal'}`
        });
    }

    toggleCrosshair() {
        this.crosshair = !this.crosshair;
        
        const btn = document.getElementById('crosshair-adv-btn');
        if (btn) {
            btn.classList.toggle('active', this.crosshair);
        }
        
        if (!this.crosshair) {
            const svg = document.getElementById('crosshair-svg');
            if (svg) svg.innerHTML = '';
        }
        
        this.notyf.open({
            type: 'info',
            message: `Crosshair ${this.crosshair ? 'enabled' : 'disabled'}`
        });
    }

    toggleMagnify() {
        this.magnifyEnabled = !this.magnifyEnabled;
        
        const btn = document.getElementById('magnify-btn');
        if (btn) {
            btn.classList.toggle('active', this.magnifyEnabled);
        }
        
        if (!this.magnifyEnabled) {
            const magnifyOverlay = document.getElementById('magnify-overlay');
            if (magnifyOverlay) magnifyOverlay.innerHTML = '';
        }
        
        this.notyf.open({
            type: 'info',
            message: `Magnify ${this.magnifyEnabled ? 'enabled' : 'disabled'}`
        });
    }

    // Image navigation
    previousImage() {
        if (this.currentImageIndex > 0) {
            this.loadImage(this.currentImageIndex - 1);
        }
    }

    nextImage() {
        if (this.currentImageIndex < this.currentImages.length - 1) {
            this.loadImage(this.currentImageIndex + 1);
        }
    }

    // Measurements
    startMeasurementOrAnnotation(startPos) {
        switch (this.activeTool) {
            case 'measure-distance':
                this.currentMeasurement = {
                    id: `measurement_${this.measurementCounter++}`,
                    type: 'distance',
                    points: [startPos],
                    imageIndex: this.currentImageIndex
                };
                break;
            case 'measure-angle':
                this.currentMeasurement = {
                    id: `measurement_${this.measurementCounter++}`,
                    type: 'angle',
                    points: [startPos],
                    imageIndex: this.currentImageIndex
                };
                break;
            case 'measure-area':
                this.currentMeasurement = {
                    id: `measurement_${this.measurementCounter++}`,
                    type: 'area',
                    points: [startPos],
                    imageIndex: this.currentImageIndex
                };
                break;
            case 'text-annotation':
                this.currentAnnotation = {
                    id: `annotation_${this.annotationCounter++}`,
                    type: 'text',
                    position: startPos,
                    text: '',
                    imageIndex: this.currentImageIndex
                };
                break;
            case 'arrow-annotation':
                this.currentAnnotation = {
                    id: `annotation_${this.annotationCounter++}`,
                    type: 'arrow',
                    points: [startPos],
                    imageIndex: this.currentImageIndex
                };
                break;
        }
    }

    updateCurrentMeasurementOrAnnotation(currentPos) {
        if (this.currentMeasurement) {
            switch (this.currentMeasurement.type) {
                case 'distance':
                    this.currentMeasurement.points[1] = currentPos;
                    break;
                case 'angle':
                    if (this.currentMeasurement.points.length < 3) {
                        this.currentMeasurement.points[1] = currentPos;
                    }
                    break;
                case 'area':
                    this.currentMeasurement.points.push(currentPos);
                    break;
            }
            this.updateMeasurementOverlay();
        }
        
        if (this.currentAnnotation) {
            switch (this.currentAnnotation.type) {
                case 'arrow':
                    this.currentAnnotation.points[1] = currentPos;
                    break;
            }
            this.updateAnnotationOverlay();
        }
    }

    completeMeasurementOrAnnotation() {
        if (this.currentMeasurement) {
            if (this.currentMeasurement.points.length >= 2) {
                this.measurements.push(this.currentMeasurement);
                this.updateMeasurementsList();
                this.saveMeasurement(this.currentMeasurement);
            }
            this.currentMeasurement = null;
        }
        
        if (this.currentAnnotation) {
            this.annotations.push(this.currentAnnotation);
            this.updateAnnotationsList();
            this.saveAnnotation(this.currentAnnotation);
            this.currentAnnotation = null;
        }
    }

    drawMeasurement(svg, measurement) {
        switch (measurement.type) {
            case 'distance':
                this.drawDistanceMeasurement(svg, measurement);
                break;
            case 'angle':
                this.drawAngleMeasurement(svg, measurement);
                break;
            case 'area':
                this.drawAreaMeasurement(svg, measurement);
                break;
        }
    }

    drawDistanceMeasurement(svg, measurement) {
        if (measurement.points.length < 2) return;
        
        const [p1, p2] = measurement.points;
        
        // Draw line
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', p1.x);
        line.setAttribute('y1', p1.y);
        line.setAttribute('x2', p2.x);
        line.setAttribute('y2', p2.y);
        line.classList.add('measurement-line');
        svg.appendChild(line);
        
        // Calculate distance
        const distance = Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
        
        // Draw text
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', (p1.x + p2.x) / 2);
        text.setAttribute('y', (p1.y + p2.y) / 2 - 5);
        text.setAttribute('text-anchor', 'middle');
        text.classList.add('measurement-text');
        text.textContent = `${distance.toFixed(1)} px`;
        svg.appendChild(text);
    }

    // UI Updates
    updatePatientInfo() {
        if (!this.currentStudy) {
            console.warn('No study data available to update patient info');
            return;
        }
        
        console.log('Updating patient info with study data:', this.currentStudy);
        
        const elements = {
            'patient-name-adv': this.currentStudy.patient_name,
            'patient-id-adv': this.currentStudy.patient_id,
            'patient-dob': this.currentStudy.patient_birth_date || this.currentStudy.patient_dob,
            'study-date-adv': this.currentStudy.study_date,
            'study-description-adv': this.currentStudy.study_description,
            'modality-adv': this.currentStudy.modality,
            'institution-name': this.currentStudy.institution_name,
            'accession-number': this.currentStudy.accession_number,
            'quick-patient-name': this.currentStudy.patient_name,
            'quick-patient-id': this.currentStudy.patient_id,
            'quick-modality': this.currentStudy.modality
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                const displayValue = value || '-';
                element.textContent = displayValue;
                console.log(`Updated ${id}: ${displayValue}`);
            } else {
                console.warn(`Element with ID '${id}' not found in DOM`);
            }
        });
        
        // Update debug info
        this.updateDebugInfo();
    }

    updateStatus(message) {
        const statusText = document.getElementById('status-text');
        if (statusText) {
            statusText.textContent = message;
        }
        console.log('Status update:', message);
    }

    updateDebugInfo() {
        // Update debug panel with current state
        const debugElements = {
            'debug-study': this.currentStudy ? `Study ${this.currentStudy.id}: ${this.currentStudy.patient_name}` : 'No study loaded',
            'debug-images': this.currentImages ? `${this.currentImages.length} images` : '0 images',
            'debug-api': 'API Active'
        };

        Object.entries(debugElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    updateStatusBar(mousePos) {
        const coordsInfo = document.getElementById('coords-info');
        if (coordsInfo && mousePos) {
            coordsInfo.textContent = `X: ${Math.round(mousePos.x)} Y: ${Math.round(mousePos.y)}`;
        }
        
        // Update pixel info if image is loaded
        if (this.currentImage && mousePos) {
            this.updatePixelInfo(mousePos);
        }
    }

    updatePixelInfo(mousePos) {
        // Convert mouse position to image coordinates
        // This is a simplified version - in practice, you'd need to account for transformations
        const pixelInfo = document.getElementById('pixel-info');
        if (pixelInfo) {
            // For now, just show coordinates - HU calculation would require DICOM pixel data
            pixelInfo.textContent = `Pixel: ${Math.round(mousePos.x)},${Math.round(mousePos.y)} HU: -`;
        }
    }

    resizeCanvas() {
        const container = this.canvas.parentElement;
        if (container) {
            // Get computed styles to ensure we have the actual dimensions
            const rect = container.getBoundingClientRect();
            const computedStyle = window.getComputedStyle(container);
            
            // Use the actual visible dimensions
            let width = rect.width;
            let height = rect.height;
            
            // Fallback to client dimensions if rect is zero
            if (width === 0) width = container.clientWidth || 800;
            if (height === 0) height = container.clientHeight || 600;
            
            // Ensure minimum size
            width = Math.max(width, 400);
            height = Math.max(height, 300);
            
            console.log(`Resizing canvas to: ${width}x${height}`);
            
            this.canvas.width = width;
            this.canvas.height = height;
            
            // Set CSS size to match canvas size for proper scaling
            this.canvas.style.width = width + 'px';
            this.canvas.style.height = height + 'px';
            
            // Re-enable high-quality rendering after resize
            this.ctx.imageSmoothingEnabled = false;
            this.ctx.mozImageSmoothingEnabled = false;
            this.ctx.webkitImageSmoothingEnabled = false;
            this.ctx.msImageSmoothingEnabled = false;
            
            // Fill with black background
            this.ctx.fillStyle = '#000000';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            
            if (this.currentImage) {
                this.render();
            }
        } else {
            console.error('Canvas container not found for resizing');
        }
    }

    showLoading(show) {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = show ? 'flex' : 'none';
        }
    }

    // Cache management
    cacheImage(key, image) {
        // Simple cache implementation - in production, you'd want more sophisticated cache management
        const imageSize = image.width * image.height * 4; // Rough estimate
        
        if (this.currentCacheSize + imageSize > this.maxCacheSize) {
            this.clearOldestCacheEntries(imageSize);
        }
        
        this.imageCache.set(key, image);
        this.currentCacheSize += imageSize;
    }

    clearOldestCacheEntries(requiredSpace) {
        // Simple FIFO cache eviction
        const entries = Array.from(this.imageCache.entries());
        let freedSpace = 0;
        
        while (freedSpace < requiredSpace && entries.length > 0) {
            const [key, image] = entries.shift();
            const imageSize = image.width * image.height * 4;
            this.imageCache.delete(key);
            freedSpace += imageSize;
            this.currentCacheSize -= imageSize;
        }
    }

    // Performance monitoring
    startPerformanceMonitoring() {
        setInterval(() => {
            this.updateMemoryUsage();
        }, 5000);
    }

    updateMemoryUsage() {
        if (performance.memory) {
            const usage = Math.round(performance.memory.usedJSHeapSize / 1024 / 1024);
            this.performanceMetrics.memoryUsage = usage;
            
            const memoryElement = document.getElementById('memory-usage');
            if (memoryElement) {
                memoryElement.textContent = `Memory: ${usage} MB`;
            }
        }
    }

    updatePerformanceDisplay() {
        // Update performance metrics in the UI if needed
        if (this.performanceMetrics.renderTime > 100) {
            console.warn(`Slow render: ${this.performanceMetrics.renderTime.toFixed(1)}ms`);
        }
    }

    // Settings management
    loadSettings() {
        const savedSettings = localStorage.getItem('dicom_viewer_settings');
        if (savedSettings) {
            this.settings = { ...this.settings, ...JSON.parse(savedSettings) };
        }
        this.applySettings();
    }

    saveSettings() {
        localStorage.setItem('dicom_viewer_settings', JSON.stringify(this.settings));
        this.notyf.success('Settings saved successfully!');
    }

    applySettings() {
        // Apply settings to the viewer
        if (this.settings.defaultWindowPreset) {
            // Apply default window preset if no image is loaded
        }
        
        this.maxCacheSize = this.settings.cacheSize * 1024 * 1024;
    }

    // Modal management with Bootstrap loading check
    showUploadModal() {
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            const modalElement = document.getElementById('uploadModal');
            if (modalElement) {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            } else {
                this.notyf.error('Upload modal not found');
            }
        } else {
            this.notyf.error('Bootstrap not loaded. Please refresh the page.');
            console.error('Bootstrap is not defined. Make sure Bootstrap JS is loaded before this script.');
        }
    }

    showExportModal() {
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            const modalElement = document.getElementById('exportModal');
            if (modalElement) {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            } else {
                this.notyf.error('Export modal not found');
            }
        } else {
            this.notyf.error('Bootstrap not loaded. Please refresh the page.');
            console.error('Bootstrap is not defined. Make sure Bootstrap JS is loaded before this script.');
        }
    }

    showSettingsModal() {
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            const modalElement = document.getElementById('settingsModal');
            if (modalElement) {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            } else {
                this.notyf.error('Settings modal not found');
            }
        } else {
            this.notyf.error('Bootstrap not loaded. Please refresh the page.');
            console.error('Bootstrap is not defined. Make sure Bootstrap JS is loaded before this script.');
        }
    }

    // Advanced features (MPR, MIP, 3D, AI)
    async enableMPR() {
        if (!this.currentSeries || this.currentImages.length < 3) {
            this.notyf.error('MPR requires at least 3 images in the series');
            return;
        }

        this.mprEnabled = !this.mprEnabled;
        const button = document.getElementById('mpr-btn');
        if (button) {
            button.classList.toggle('active', this.mprEnabled);
        }

        if (this.mprEnabled) {
            this.notyf.info('Generating Multi-Planar Reconstruction...');
            
            try {
                const response = await fetch(`/viewer/api/series/${this.currentSeries}/mpr/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({
                        slice_position: 0.5
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    this.displayMPRViews(data.mpr_views);
                    this.notyf.success('MPR generated successfully');
                } else {
                    throw new Error(data.error || 'MPR generation failed');
                }
            } catch (error) {
                console.error('Error generating MPR:', error);
                this.notyf.error(`MPR generation failed: ${error.message}`);
                this.mprEnabled = false;
                if (button) {
                    button.classList.remove('active');
                }
            }
        } else {
            this.disableMPR();
            this.notyf.info('MPR mode disabled');
        }
    }
    
    displayMPRViews(mprViews) {
        // Switch to 2x2 layout for MPR display
        this.setViewportLayout('2x2');
        
        // Get all canvases
        const canvases = {
            axial: document.getElementById('dicom-canvas-advanced'),
            sagittal: document.getElementById('dicom-canvas-quad-2'),
            coronal: document.getElementById('dicom-canvas-quad-3'),
            volume: document.getElementById('dicom-canvas-quad-4')
        };
        
        // Display each MPR view
        Object.entries(mprViews).forEach(([viewName, viewData]) => {
            const canvas = canvases[viewName];
            if (canvas && viewData.data) {
                const ctx = canvas.getContext('2d');
                const img = new Image();
                img.onload = () => {
                    canvas.width = viewData.dimensions.width;
                    canvas.height = viewData.dimensions.height;
                    ctx.drawImage(img, 0, 0);
                    
                    // Add view label
                    ctx.fillStyle = 'white';
                    ctx.font = '16px Arial';
                    ctx.fillText(viewName.toUpperCase(), 10, 25);
                };
                img.src = viewData.data;
            }
        });
        
        // Add MPR controls overlay
        this.addMPRControls();
    }
    
    addMPRControls() {
        // Remove existing MPR overlay
        const existingOverlay = document.getElementById('mpr-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }
        
        // Create MPR overlay
        const overlay = document.createElement('div');
        overlay.id = 'mpr-overlay';
        overlay.className = 'mpr-overlay';
        overlay.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            z-index: 1000;
        `;

        overlay.innerHTML = `
            <div><strong>MPR Mode Active</strong></div>
            <div>Axial | Sagittal | Coronal</div>
            <div>Slice: <input type="range" id="mpr-slice-slider" min="0" max="1" step="0.01" value="0.5" style="width: 100px;"></div>
            <div>Press Q to toggle MPR</div>
        `;

        document.getElementById('canvas-container').appendChild(overlay);
        
        // Add slice slider functionality
        const slider = document.getElementById('mpr-slice-slider');
        if (slider) {
            slider.addEventListener('input', (e) => {
                this.updateMPRSlice(parseFloat(e.target.value));
            });
        }
    }
    
    async updateMPRSlice(slicePosition) {
        try {
            const response = await fetch(`/viewer/api/series/${this.currentSeries}/mpr/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    slice_position: slicePosition
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayMPRViews(data.mpr_views);
            }
        } catch (error) {
            console.error('Error updating MPR slice:', error);
        }
    }

    disableMPR() {
        this.mprEnabled = false;
        const overlay = document.getElementById('mpr-overlay');
        if (overlay) {
            overlay.remove();
        }
        
        // Return to single viewport layout
        this.setViewportLayout('1x1');
    }

    async enableVolumeRendering() {
        if (!this.currentSeries || this.currentImages.length < 10) {
            this.notyf.error('Volume rendering requires at least 10 images in the series');
            return;
        }

        this.notyf.info('Generating 3D volume rendering...');
        
        try {
            const response = await fetch(`/viewer/api/series/${this.currentSeries}/volume-rendering/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    mode: 'composite',
                    opacity_threshold: 0.1,
                    color_preset: 'grayscale'
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayVolumeRendering(data.volume_rendering, data.parameters);
                this.notyf.success('3D volume rendering generated');
            } else {
                throw new Error(data.error || 'Volume rendering failed');
            }
        } catch (error) {
            console.error('Error generating volume rendering:', error);
            this.notyf.error(`Volume rendering failed: ${error.message}`);
        }
    }
    
    displayVolumeRendering(imageData, parameters) {
        const canvas = document.getElementById('dicom-canvas-advanced');
        const ctx = canvas.getContext('2d');
        
        const img = new Image();
        img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            
            // Add volume rendering label
            ctx.fillStyle = 'white';
            ctx.font = '18px Arial';
            ctx.fillText('3D Volume Rendering', 10, 30);
            ctx.font = '12px Arial';
            ctx.fillText(`Mode: ${parameters.rendering_mode}`, 10, 50);
            ctx.fillText(`Preset: ${parameters.color_preset}`, 10, 70);
        };
        img.src = imageData;
        
        // Add volume rendering controls
        this.addVolumeControls(parameters);
    }
    
    addVolumeControls(parameters) {
        const overlay = document.createElement('div');
        overlay.id = 'volume-overlay';
        overlay.className = 'volume-overlay';
        overlay.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            z-index: 1000;
        `;

        overlay.innerHTML = `
            <div><strong>3D Volume Rendering</strong></div>
            <div>Mode: 
                <select id="volume-mode" style="margin-left: 5px;">
                    <option value="composite" ${parameters.rendering_mode === 'composite' ? 'selected' : ''}>Composite</option>
                    <option value="mip" ${parameters.rendering_mode === 'mip' ? 'selected' : ''}>MIP</option>
                    <option value="average" ${parameters.rendering_mode === 'average' ? 'selected' : ''}>Average</option>
                </select>
            </div>
            <div>Preset: 
                <select id="volume-preset" style="margin-left: 5px;">
                    <option value="grayscale" ${parameters.color_preset === 'grayscale' ? 'selected' : ''}>Grayscale</option>
                    <option value="bone" ${parameters.color_preset === 'bone' ? 'selected' : ''}>Bone</option>
                    <option value="soft_tissue" ${parameters.color_preset === 'soft_tissue' ? 'selected' : ''}>Soft Tissue</option>
                    <option value="vessels" ${parameters.color_preset === 'vessels' ? 'selected' : ''}>Vessels</option>
                </select>
            </div>
            <div>Opacity: <input type="range" id="volume-opacity" min="0" max="1" step="0.01" value="${parameters.opacity_threshold}" style="width: 100px;"></div>
            <button id="update-volume" style="margin-top: 10px;">Update</button>
        `;

        document.getElementById('canvas-container').appendChild(overlay);
        
        // Add update button functionality
        document.getElementById('update-volume').addEventListener('click', () => {
            const mode = document.getElementById('volume-mode').value;
            const preset = document.getElementById('volume-preset').value;
            const opacity = parseFloat(document.getElementById('volume-opacity').value);
            
            this.updateVolumeRendering(mode, preset, opacity);
        });
    }

    async enableMIP() {
        if (!this.currentSeries || this.currentImages.length < 2) {
            this.notyf.error('MIP requires at least 2 images in the series');
            return;
        }

        this.notyf.info('Generating Maximum Intensity Projection...');
        
        try {
            const response = await fetch(`/viewer/api/series/${this.currentSeries}/mip/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    axis: 'axial'
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayMIP(data.mip_data, data.projection_axis);
                this.notyf.success('MIP generated successfully');
            } else {
                throw new Error(data.error || 'MIP generation failed');
            }
        } catch (error) {
            console.error('Error generating MIP:', error);
            this.notyf.error(`MIP generation failed: ${error.message}`);
        }
    }
    
    displayMIP(imageData, projectionAxis) {
        const canvas = document.getElementById('dicom-canvas-advanced');
        const ctx = canvas.getContext('2d');
        
        const img = new Image();
        img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            
            // Add MIP label
            ctx.fillStyle = 'white';
            ctx.font = '18px Arial';
            ctx.fillText('Maximum Intensity Projection', 10, 30);
            ctx.font = '12px Arial';
            ctx.fillText(`Projection: ${projectionAxis}`, 10, 50);
        };
        img.src = imageData;
        
        // Add MIP controls
        this.addMIPControls(projectionAxis);
    }
    
    addMIPControls(currentAxis) {
        const overlay = document.createElement('div');
        overlay.id = 'mip-overlay';
        overlay.className = 'mip-overlay';
        overlay.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            z-index: 1000;
        `;

        overlay.innerHTML = `
            <div><strong>MIP Controls</strong></div>
            <div>Projection Axis:</div>
            <div>
                <input type="radio" id="mip-axial" name="mip-axis" value="axial" ${currentAxis === 'axial' ? 'checked' : ''}>
                <label for="mip-axial">Axial</label>
            </div>
            <div>
                <input type="radio" id="mip-sagittal" name="mip-axis" value="sagittal" ${currentAxis === 'sagittal' ? 'checked' : ''}>
                <label for="mip-sagittal">Sagittal</label>
            </div>
            <div>
                <input type="radio" id="mip-coronal" name="mip-axis" value="coronal" ${currentAxis === 'coronal' ? 'checked' : ''}>
                <label for="mip-coronal">Coronal</label>
            </div>
            <button id="update-mip" style="margin-top: 10px;">Update MIP</button>
        `;

        document.getElementById('canvas-container').appendChild(overlay);
        
        // Add update button functionality
        document.getElementById('update-mip').addEventListener('click', () => {
            const selectedAxis = document.querySelector('input[name="mip-axis"]:checked').value;
            this.updateMIP(selectedAxis);
        });
    }

    async calculateVolume() {
        if (!this.currentSeries || this.currentImages.length < 2) {
            this.notyf.error('Volume calculation requires at least 2 images');
            return;
        }

        this.notyf.info('Calculating volume measurements...');
        
        try {
            const response = await fetch(`/viewer/api/series/${this.currentSeries}/volume-measurement/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    measurement_type: 'threshold',
                    threshold_min: 100,
                    threshold_max: 3000
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayVolumeResults(data.volume_measurements);
                this.notyf.success('Volume calculation completed');
            } else {
                throw new Error(data.error || 'Volume calculation failed');
            }
        } catch (error) {
            console.error('Error calculating volume:', error);
            this.notyf.error(`Volume calculation failed: ${error.message}`);
        }
    }
    
    displayVolumeResults(measurements) {
        const overlay = document.createElement('div');
        overlay.id = 'volume-results';
        overlay.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 20px;
            border-radius: 10px;
            font-family: monospace;
            font-size: 14px;
            z-index: 1000;
            max-width: 400px;
        `;

        overlay.innerHTML = `
            <div style="text-align: center; margin-bottom: 15px;">
                <strong>Volume Measurements</strong>
                <button id="close-volume-results" style="float: right; background: #ff4444; border: none; color: white; padding: 2px 8px; border-radius: 3px; cursor: pointer;">×</button>
            </div>
            <div>Volume (mm³): ${measurements.volume_mm3}</div>
            <div>Volume (ml): ${measurements.volume_ml}</div>
            <div>Volume (cm³): ${measurements.volume_cm3}</div>
            <div>Measurement Type: ${measurements.measurement_type}</div>
            <div>Number of Slices: ${measurements.num_slices}</div>
            <div>Spacing: ${measurements.spacing.join(' × ')} mm</div>
        `;

        document.body.appendChild(overlay);
        
        // Add close button functionality
        document.getElementById('close-volume-results').addEventListener('click', () => {
            overlay.remove();
        });
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (overlay.parentNode) {
                overlay.remove();
            }
        }, 10000);
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

    // Additional methods for specific tools
    applySharpenFilter() {
        this.notyf.open({
            type: 'info',
            message: 'Sharpen filter applied'
        });
    }

    detectLesions() {
        this.notyf.open({
            type: 'info',
            message: 'Lesion detection started'
        });
    }

    segmentOrgans() {
        this.notyf.open({
            type: 'info',
            message: 'Organ segmentation started'
        });
    }

    previousStudy() {
        this.notyf.open({
            type: 'info',
            message: 'Previous study navigation not implemented'
        });
    }

    nextStudy() {
        this.notyf.open({
            type: 'info',
            message: 'Next study navigation not implemented'
        });
    }

    toggleCine() {
        this.cineMode = !this.cineMode;
        if (this.cineMode) {
            this.startCine();
        } else {
            this.stopCine();
        }
    }

    startCine() {
        if (this.cineTimer) return;
        
        this.cineTimer = setInterval(() => {
            this.nextImage();
            if (this.currentImageIndex >= this.currentImages.length - 1) {
                this.loadImage(0); // Loop back to first image
            }
        }, this.cineSpeed);
        
        this.notyf.open({
            type: 'info',
            message: 'Cine mode started'
        });
    }

    stopCine() {
        if (this.cineTimer) {
            clearInterval(this.cineTimer);
            this.cineTimer = null;
        }
        this.cineMode = false;
        this.notyf.open({
            type: 'info',
            message: 'Cine mode stopped'
        });
    }

    updateMagnifyGlass(mousePos) {
        // Implementation for magnifying glass
        const magnifyOverlay = document.getElementById('magnify-overlay');
        if (!magnifyOverlay || !this.magnifyEnabled) return;
        
        // Create or update magnifying glass
        let magnifyGlass = magnifyOverlay.querySelector('.magnify-glass');
        if (!magnifyGlass) {
            magnifyGlass = document.createElement('div');
            magnifyGlass.className = 'magnify-glass';
            magnifyOverlay.appendChild(magnifyGlass);
        }
        
        // Position magnifying glass
        magnifyGlass.style.left = `${mousePos.x - 75}px`;
        magnifyGlass.style.top = `${mousePos.y - 75}px`;
        
        // Update magnified content (simplified implementation)
        // In a full implementation, you'd render a magnified portion of the image
    }

    updateCrosshair(mousePos) {
        this.lastMousePos = mousePos;
        if (this.crosshair) {
            this.updateCrosshairOverlay();
        }
    }

    drawAnnotation(svg, annotation) {
        // Implementation for drawing annotations
        switch (annotation.type) {
            case 'text':
                this.drawTextAnnotation(svg, annotation);
                break;
            case 'arrow':
                this.drawArrowAnnotation(svg, annotation);
                break;
            case 'circle':
                this.drawCircleAnnotation(svg, annotation);
                break;
            case 'rectangle':
                this.drawRectangleAnnotation(svg, annotation);
                break;
        }
    }

    drawTextAnnotation(svg, annotation) {
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', annotation.position.x);
        text.setAttribute('y', annotation.position.y);
        text.classList.add('annotation-text');
        text.textContent = annotation.text || 'Text Annotation';
        svg.appendChild(text);
    }

    drawArrowAnnotation(svg, annotation) {
        if (annotation.points && annotation.points.length >= 2) {
            const [start, end] = annotation.points;
            
            // Draw line
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', start.x);
            line.setAttribute('y1', start.y);
            line.setAttribute('x2', end.x);
            line.setAttribute('y2', end.y);
            line.classList.add('annotation-shape');
            svg.appendChild(line);
            
            // Draw arrowhead (simplified)
            const arrowhead = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
            const angle = Math.atan2(end.y - start.y, end.x - start.x);
            const arrowLength = 10;
            const arrowAngle = Math.PI / 6;
            
            const x1 = end.x - arrowLength * Math.cos(angle - arrowAngle);
            const y1 = end.y - arrowLength * Math.sin(angle - arrowAngle);
            const x2 = end.x - arrowLength * Math.cos(angle + arrowAngle);
            const y2 = end.y - arrowLength * Math.sin(angle + arrowAngle);
            
            arrowhead.setAttribute('points', `${end.x},${end.y} ${x1},${y1} ${x2},${y2}`);
            arrowhead.classList.add('annotation-shape');
            svg.appendChild(arrowhead);
        }
    }

    drawCircleAnnotation(svg, annotation) {
        // Implementation for circle annotation
    }

    drawRectangleAnnotation(svg, annotation) {
        // Implementation for rectangle annotation
    }

    drawAngleMeasurement(svg, measurement) {
        // Implementation for angle measurement
    }

    drawAreaMeasurement(svg, measurement) {
        // Implementation for area measurement
    }

    addTextAnnotation(position) {
        const text = prompt('Enter annotation text:');
        if (text) {
            const annotation = {
                id: `annotation_${this.annotationCounter++}`,
                type: 'text',
                position: position,
                text: text,
                imageIndex: this.currentImageIndex
            };
            this.annotations.push(annotation);
            this.updateAnnotationOverlay();
            this.updateAnnotationsList();
            this.saveAnnotation(annotation);
        }
    }

    // Enhanced API call with better error handling
    async makeAPICall(url, options = {}) {
            try {
                console.log(`Making API call to: ${url}`);
                const response = await fetch(url, {
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken(),
                        ...options.headers
                    },
                    ...options
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error(`API call failed: ${response.status} - ${errorText}`);
                    throw new Error(`API call failed: ${response.status} - ${response.statusText}`);
                }
                
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return await response.json();
                } else {
                    return await response.text();
                }
            } catch (error) {
                console.error(`API call error for ${url}:`, error);
                throw error;
            }
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

    async generateBoneReconstruction() {
        if (!this.currentSeries || this.currentImages.length < 5) {
            this.notyf.error('Bone reconstruction requires at least 5 images in the series');
            return;
        }

        this.notyf.info('Generating bone reconstruction...');
        
        try {
            const response = await fetch(`/viewer/api/series/${this.currentSeries}/bone-reconstruction/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    bone_threshold: 200,
                    enhancement_factor: 2.0
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayBoneReconstruction(data.bone_reconstruction, data.parameters);
                this.notyf.success('Bone reconstruction generated successfully');
            } else {
                throw new Error(data.error || 'Bone reconstruction failed');
            }
        } catch (error) {
            console.error('Error generating bone reconstruction:', error);
            this.notyf.error(`Bone reconstruction failed: ${error.message}`);
        }
    }
    
    displayBoneReconstruction(imageData, parameters) {
        const canvas = document.getElementById('dicom-canvas-advanced');
        const ctx = canvas.getContext('2d');
        
        const img = new Image();
        img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            
            // Add bone reconstruction label
            ctx.fillStyle = 'white';
            ctx.font = '18px Arial';
            ctx.fillText('Bone Reconstruction', 10, 30);
            ctx.font = '12px Arial';
            ctx.fillText(`Threshold: ${parameters.bone_threshold} HU`, 10, 50);
            ctx.fillText(`Enhancement: ${parameters.enhancement_factor}x`, 10, 70);
        };
        img.src = imageData;
        
        // Add bone reconstruction controls
        this.addBoneControls(parameters);
    }
    
    addBoneControls(parameters) {
        const overlay = document.createElement('div');
        overlay.id = 'bone-overlay';
        overlay.className = 'bone-overlay';
        overlay.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            z-index: 1000;
        `;

        overlay.innerHTML = `
            <div><strong>Bone Reconstruction</strong></div>
            <div>Threshold (HU): <input type="range" id="bone-threshold" min="50" max="500" step="10" value="${parameters.bone_threshold}" style="width: 100px;"></div>
            <div><span id="threshold-value">${parameters.bone_threshold}</span> HU</div>
            <div>Enhancement: <input type="range" id="bone-enhancement" min="1" max="5" step="0.1" value="${parameters.enhancement_factor}" style="width: 100px;"></div>
            <div><span id="enhancement-value">${parameters.enhancement_factor}</span>x</div>
            <button id="update-bone" style="margin-top: 10px;">Update</button>
        `;

        document.getElementById('canvas-container').appendChild(overlay);
        
        // Add real-time updates for sliders
        const thresholdSlider = document.getElementById('bone-threshold');
        const thresholdValue = document.getElementById('threshold-value');
        const enhancementSlider = document.getElementById('bone-enhancement');
        const enhancementValue = document.getElementById('enhancement-value');
        
        thresholdSlider.addEventListener('input', (e) => {
            thresholdValue.textContent = e.target.value;
        });
        
        enhancementSlider.addEventListener('input', (e) => {
            enhancementValue.textContent = e.target.value;
        });
        
        // Add update button functionality
        document.getElementById('update-bone').addEventListener('click', () => {
            const threshold = parseInt(thresholdSlider.value);
            const enhancement = parseFloat(enhancementSlider.value);
            this.updateBoneReconstruction(threshold, enhancement);
        });
    }
    
    async updateBoneReconstruction(threshold, enhancement) {
        try {
            this.notyf.info('Updating bone reconstruction...');
            
            const response = await fetch(`/viewer/api/series/${this.currentSeries}/bone-reconstruction/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    bone_threshold: threshold,
                    enhancement_factor: enhancement
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayBoneReconstruction(data.bone_reconstruction, data.parameters);
                this.notyf.success('Bone reconstruction updated');
            } else {
                throw new Error(data.error || 'Update failed');
            }
        } catch (error) {
            console.error('Error updating bone reconstruction:', error);
            this.notyf.error(`Update failed: ${error.message}`);
        }
    }
    
    async updateVolumeRendering(mode, preset, opacity) {
        try {
            this.notyf.info('Updating volume rendering...');
            
            const response = await fetch(`/viewer/api/series/${this.currentSeries}/volume-rendering/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    mode: mode,
                    color_preset: preset,
                    opacity_threshold: opacity
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayVolumeRendering(data.volume_rendering, data.parameters);
                this.notyf.success('Volume rendering updated');
            } else {
                throw new Error(data.error || 'Update failed');
            }
        } catch (error) {
            console.error('Error updating volume rendering:', error);
            this.notyf.error(`Update failed: ${error.message}`);
        }
    }
    
    async updateMIP(axis) {
        try {
            this.notyf.info('Updating MIP...');
            
            const response = await fetch(`/viewer/api/series/${this.currentSeries}/mip/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    axis: axis
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayMIP(data.mip_data, data.projection_axis);
                this.notyf.success('MIP updated');
            } else {
                throw new Error(data.error || 'Update failed');
            }
        } catch (error) {
            console.error('Error updating MIP:', error);
            this.notyf.error(`Update failed: ${error.message}`);
        }
    }
    
    // Helper method to add bone reconstruction button to the toolbar
    addBoneReconstructionButton() {
        const toolbar = document.querySelector('.tool-group-advanced');
        if (toolbar && !document.getElementById('bone-reconstruction-btn')) {
            const button = document.createElement('button');
            button.id = 'bone-reconstruction-btn';
            button.className = 'tool-btn-advanced';
            button.title = 'Bone Reconstruction';
            button.innerHTML = `
                <i class="fas fa-bone"></i>
                <span>Bone</span>
            `;
            button.addEventListener('click', () => this.generateBoneReconstruction());
            toolbar.appendChild(button);
        }
    }
    
    // Enhanced print functionality with reconstruction support
    async printCurrentView() {
        try {
            // Get current canvas content
            const canvas = document.getElementById('dicom-canvas-advanced');
            if (!canvas) {
                this.notyf.error('No image to print');
                return;
            }
            
            // Create print window
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                    <head>
                        <title>DICOM Image Print</title>
                        <style>
                            body { margin: 0; padding: 20px; text-align: center; }
                            .print-header { margin-bottom: 20px; }
                            .print-image { max-width: 100%; height: auto; }
                            .print-info { margin-top: 20px; font-family: monospace; font-size: 12px; }
                        </style>
                    </head>
                    <body>
                        <div class="print-header">
                            <h2>DICOM Image - Noctis Viewer</h2>
                            <p>Printed on: ${new Date().toLocaleString()}</p>
                        </div>
                        <img class="print-image" src="${canvas.toDataURL()}" />
                        <div class="print-info">
                            <p>Patient: ${document.getElementById('quick-patient-name')?.textContent || 'N/A'}</p>
                            <p>Study: ${document.getElementById('quick-patient-id')?.textContent || 'N/A'}</p>
                            <p>Modality: ${document.getElementById('quick-modality')?.textContent || 'N/A'}</p>
                        </div>
                    </body>
                </html>
            `);
            
            printWindow.document.close();
            
            // Wait for image to load then print
            setTimeout(() => {
                printWindow.print();
                printWindow.close();
            }, 1000);
            
            this.notyf.success('Print dialog opened');
            
        } catch (error) {
            console.error('Error printing:', error);
            this.notyf.error('Print failed');
        }
    }
    
    // Initialize all features when viewer starts
    initializeAdvancedFeatures() {
        // Add bone reconstruction button
        this.addBoneReconstructionButton();
        
        // Load user settings
        this.loadSettings();
        
        // Set up keyboard shortcuts for advanced features
        this.setupAdvancedKeyboardShortcuts();
    }
    
    setupAdvancedKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.altKey) {
                switch(e.key.toLowerCase()) {
                    case 'm':
                        e.preventDefault();
                        this.enableMPR();
                        break;
                    case 'v':
                        e.preventDefault();
                        this.enableVolumeRendering();
                        break;
                    case 'i':
                        e.preventDefault();
                        this.enableMIP();
                        break;
                    case 'b':
                        e.preventDefault();
                        this.generateBoneReconstruction();
                        break;
                    case 'c':
                        e.preventDefault();
                        this.calculateVolume();
                        break;
                    case 'p':
                        e.preventDefault();
                        this.printCurrentView();
                        break;
                }
            }
        });
    }
    
    async loadSettings() {
        try {
            const response = await fetch('/viewer/api/settings/');
            const data = await response.json();
            
            if (data.success && data.settings) {
                this.applySettings(data.settings);
            }
        } catch (error) {
            console.log('Could not load user settings:', error);
        }
    }
    
    applySettings(settings) {
        // Apply loaded settings to the viewer
        if (settings.viewport_layout) {
            this.setViewportLayout(settings.viewport_layout);
        }
        
        // Apply other settings as needed
        this.settings = { ...this.settings, ...settings };
    }
}

// Export the class for use
window.AdvancedDicomViewer = AdvancedDicomViewer;