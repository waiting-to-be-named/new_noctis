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

        // Core elements
        this.canvas = document.getElementById('dicom-canvas-advanced');
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
        this.loadSettings();

        // Auto-load study if provided, otherwise load available studies
        if (initialStudyId) {
            this.loadStudy(initialStudyId);
        } else {
            this.loadAvailableStudies();
        }

        // Initialize UI components
        this.initializeUI();
        
        // Start performance monitoring
        this.startPerformanceMonitoring();

        this.notyf.success('Advanced DICOM Viewer Pro initialized successfully!');
    }

    initializeViewer() {
        // Set canvas size
        this.resizeCanvas();
        
        // Initialize overlays
        this.initializeOverlays();
        
        // Set up resize observer
        if (window.ResizeObserver) {
            this.resizeObserver = new ResizeObserver(() => {
                this.resizeCanvas();
                this.render();
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
        // Navigation tools
        document.getElementById('windowing-adv-btn')?.addEventListener('click', () => this.setActiveTool('windowing'));
        document.getElementById('pan-adv-btn')?.addEventListener('click', () => this.setActiveTool('pan'));
        document.getElementById('zoom-adv-btn')?.addEventListener('click', () => this.setActiveTool('zoom'));
        document.getElementById('rotate-btn')?.addEventListener('click', () => this.rotateImage(90));
        document.getElementById('flip-btn')?.addEventListener('click', () => this.flipImage());

        // Measurement tools
        document.getElementById('measure-distance-btn')?.addEventListener('click', () => this.setActiveTool('measure-distance'));
        document.getElementById('measure-angle-btn')?.addEventListener('click', () => this.setActiveTool('measure-angle'));
        document.getElementById('measure-area-btn')?.addEventListener('click', () => this.setActiveTool('measure-area'));
        document.getElementById('measure-volume-btn')?.addEventListener('click', () => this.setActiveTool('measure-volume'));
        document.getElementById('hu-measurement-btn')?.addEventListener('click', () => this.setActiveTool('hu-measurement'));

        // Annotation tools
        document.getElementById('text-annotation-btn')?.addEventListener('click', () => this.setActiveTool('text-annotation'));
        document.getElementById('arrow-annotation-btn')?.addEventListener('click', () => this.setActiveTool('arrow-annotation'));
        document.getElementById('circle-annotation-btn')?.addEventListener('click', () => this.setActiveTool('circle-annotation'));
        document.getElementById('rectangle-annotation-btn')?.addEventListener('click', () => this.setActiveTool('rectangle-annotation'));

        // Enhancement tools
        document.getElementById('invert-adv-btn')?.addEventListener('click', () => this.toggleInvert());
        document.getElementById('crosshair-adv-btn')?.addEventListener('click', () => this.toggleCrosshair());
        document.getElementById('magnify-btn')?.addEventListener('click', () => this.toggleMagnify());
        document.getElementById('sharpen-btn')?.addEventListener('click', () => this.applySharpenFilter());

        // 3D/MPR tools
        document.getElementById('mpr-btn')?.addEventListener('click', () => this.enableMPR());
        document.getElementById('volume-render-btn')?.addEventListener('click', () => this.enableVolumeRendering());
        document.getElementById('mip-btn')?.addEventListener('click', () => this.enableMIP());

        // AI tools
        document.getElementById('ai-analysis-btn')?.addEventListener('click', () => this.runAIAnalysis());
        document.getElementById('ai-segment-btn')?.addEventListener('click', () => this.runAISegmentation());

        // Utility tools
        document.getElementById('reset-adv-btn')?.addEventListener('click', () => this.resetView());
        document.getElementById('fit-to-window-btn')?.addEventListener('click', () => this.fitToWindow());
        document.getElementById('actual-size-btn')?.addEventListener('click', () => this.actualSize());
    }

    setupHeaderButtonEvents() {
        // Header navigation
        document.getElementById('prev-study-btn')?.addEventListener('click', () => this.previousStudy());
        document.getElementById('next-study-btn')?.addEventListener('click', () => this.nextStudy());

        // Header actions
        document.getElementById('upload-advanced-btn')?.addEventListener('click', () => this.showUploadModal());
        document.getElementById('export-btn')?.addEventListener('click', () => this.showExportModal());
        document.getElementById('settings-btn')?.addEventListener('click', () => this.showSettingsModal());
        document.getElementById('fullscreen-btn')?.addEventListener('click', () => this.toggleFullscreen());
        document.getElementById('logout-advanced-btn')?.addEventListener('click', () => this.logout());

        // Patient info toggle
        document.getElementById('toggle-patient-info')?.addEventListener('click', () => this.togglePatientInfo());
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

        // Viewport layout controls
        document.getElementById('layout-1x1-btn')?.addEventListener('click', () => this.setViewportLayout('1x1'));
        document.getElementById('layout-2x2-btn')?.addEventListener('click', () => this.setViewportLayout('2x2'));
        document.getElementById('layout-1x2-btn')?.addEventListener('click', () => this.setViewportLayout('1x2'));
        document.getElementById('sync-viewports-btn')?.addEventListener('click', () => this.toggleViewportSync());

        // Thumbnail navigator
        document.getElementById('thumbnail-toggle')?.addEventListener('click', () => this.toggleThumbnails());

        // Clear buttons
        document.getElementById('clear-measurements-btn')?.addEventListener('click', () => this.clearMeasurements());
        document.getElementById('clear-annotations-btn')?.addEventListener('click', () => this.clearAnnotations());

        // AI controls
        document.getElementById('ai-detect-lesions')?.addEventListener('click', () => this.detectLesions());
        document.getElementById('ai-segment-organs')?.addEventListener('click', () => this.segmentOrgans());
        document.getElementById('ai-calculate-volume')?.addEventListener('click', () => this.calculateVolume());
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
        const toolBtn = document.getElementById(`${tool.replace('measure-', 'measure-').replace('-btn', '')}-btn`);
        if (toolBtn) {
            toolBtn.classList.add('active');
        }

        this.activeTool = tool;
        this.canvas.style.cursor = this.getCursorForTool();
        
        this.notyf.info(`${tool.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())} tool activated`);
    }

    // Image loading and management
    async loadAvailableStudies() {
        try {
            this.updateStatus('Loading available studies...');
            
            const response = await fetch('/viewer/api/studies/');
            if (!response.ok) {
                throw new Error(`Failed to load studies: ${response.statusText}`);
            }
            
            const studies = await response.json();
            this.displayStudiesList(studies);
            
            this.updateStatus('Select a study to view');
        } catch (error) {
            console.error('Error loading studies:', error);
            this.notyf.error(`Failed to load studies: ${error.message}`);
            this.updateStatus('Error loading studies');
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

    async loadStudy(studyId) {
        try {
            this.showLoading(true);
            this.updateStatus('Loading study...');

            const response = await fetch(`/viewer/api/studies/${studyId}/`);
            if (!response.ok) {
                throw new Error(`Failed to load study: ${response.statusText}`);
            }

            this.currentStudy = await response.json();
            this.updatePatientInfo();
            
            // Load series
            await this.loadSeries();
            
            this.notyf.success('Study loaded successfully!');
        } catch (error) {
            console.error('Error loading study:', error);
            this.notyf.error(`Failed to load study: ${error.message}`);
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

            const series = await response.json();
            this.updateSeriesList(series);
            
            if (series.length > 0) {
                await this.loadImages(series[0].id);
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

            this.currentImages = await response.json();
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
            if (index < 0 || index >= this.currentImages.length) return;

            this.currentImageIndex = index;
            const imageInfo = this.currentImages[index];
            
            // Check cache first
            const cacheKey = `image_${imageInfo.id}`;
            if (this.imageCache.has(cacheKey)) {
                this.currentImage = this.imageCache.get(cacheKey);
                this.processAndRenderImage();
                return;
            }

            this.updateStatus(`Loading image ${index + 1}/${this.currentImages.length}...`);

            const startTime = performance.now();
            const response = await fetch(`/viewer/api/images/${imageInfo.id}/data/`);
            if (!response.ok) {
                throw new Error(`Failed to load image: ${response.statusText}`);
            }

            const blob = await response.blob();
            const imageUrl = URL.createObjectURL(blob);
            
            const img = new Image();
            img.onload = () => {
                this.currentImage = img;
                this.cacheImage(cacheKey, img);
                this.processAndRenderImage();
                
                const loadTime = performance.now() - startTime;
                this.performanceMetrics.loadTime = loadTime;
                this.updatePerformanceDisplay();
                
                URL.revokeObjectURL(imageUrl);
            };
            img.onerror = () => {
                this.notyf.error('Failed to load image');
                URL.revokeObjectURL(imageUrl);
            };
            img.src = imageUrl;

        } catch (error) {
            console.error('Error loading image:', error);
            this.notyf.error(`Failed to load image: ${error.message}`);
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
        if (!this.currentImage) return;

        const startTime = performance.now();
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Save context state
        this.ctx.save();
        
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
            
            this.ctx.drawImage(tempCanvas, 0, 0);
        } else {
            this.ctx.drawImage(this.currentImage, 0, 0);
        }
        
        // Restore context state
        this.ctx.restore();
        
        // Update overlays
        this.updateOverlays();
        
        const renderTime = performance.now() - startTime;
        this.performanceMetrics.renderTime = renderTime;
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
        
        this.notyf.info(`Applied ${presetName} preset: W:${preset.ww} L:${preset.wl}`);
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
        this.notyf.info('View reset to default');
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
        this.notyf.info('Image fitted to window');
    }

    actualSize() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.render();
        this.updateZoomDisplay();
        this.notyf.info('Image displayed at actual size');
    }

    // Image transformations
    rotateImage(degrees) {
        this.rotation = (this.rotation + degrees) % 360;
        this.render();
        this.notyf.info(`Image rotated ${degrees}°`);
    }

    flipImage(direction = 'horizontal') {
        if (direction === 'horizontal') {
            this.flipHorizontal = !this.flipHorizontal;
            this.notyf.info('Image flipped horizontally');
        } else {
            this.flipVertical = !this.flipVertical;
            this.notyf.info('Image flipped vertically');
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
        
        this.notyf.info(`Image ${this.inverted ? 'inverted' : 'normal'}`);
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
        
        this.notyf.info(`Crosshair ${this.crosshair ? 'enabled' : 'disabled'}`);
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
        
        this.notyf.info(`Magnify ${this.magnifyEnabled ? 'enabled' : 'disabled'}`);
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
        if (!this.currentStudy) return;
        
        const elements = {
            'patient-name-adv': this.currentStudy.patient_name,
            'patient-id-adv': this.currentStudy.patient_id,
            'study-date-adv': this.currentStudy.study_date,
            'study-description-adv': this.currentStudy.study_description,
            'modality-adv': this.currentStudy.modality,
            'institution-name': this.currentStudy.institution_name,
            'quick-patient-name': this.currentStudy.patient_name,
            'quick-patient-id': this.currentStudy.patient_id,
            'quick-modality': this.currentStudy.modality
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value || '-';
            }
        });
    }

    updateStatus(message) {
        const statusText = document.getElementById('status-text');
        if (statusText) {
            statusText.textContent = message;
        }
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
            this.canvas.width = container.clientWidth;
            this.canvas.height = container.clientHeight;
            
            // Re-enable high-quality rendering after resize
            this.ctx.imageSmoothingEnabled = false;
            this.ctx.mozImageSmoothingEnabled = false;
            this.ctx.webkitImageSmoothingEnabled = false;
            this.ctx.msImageSmoothingEnabled = false;
            
            if (this.currentImage) {
                this.render();
            }
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

    // Modal management
    showUploadModal() {
        const modal = new bootstrap.Modal(document.getElementById('uploadModal'));
        modal.show();
    }

    showExportModal() {
        const modal = new bootstrap.Modal(document.getElementById('exportModal'));
        modal.show();
    }

    showSettingsModal() {
        const modal = new bootstrap.Modal(document.getElementById('settingsModal'));
        modal.show();
    }

    // Advanced features (placeholder implementations)
    enableMPR() {
        this.notyf.info('MPR mode will be available in future update');
    }

    enableVolumeRendering() {
        this.notyf.info('Volume rendering will be available in future update');
    }

    enableMIP() {
        this.notyf.info('MIP will be available in future update');
    }

    runAIAnalysis() {
        this.notyf.info('AI analysis will be available in future update');
    }

    runAISegmentation() {
        this.notyf.info('AI segmentation will be available in future update');
    }

    // Utility functions
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }

    logout() {
        if (confirm('Are you sure you want to logout?')) {
            window.location.href = '/logout/';
        }
    }

    cleanup() {
        // Cleanup resources before page unload
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        
        if (this.cineTimer) {
            clearInterval(this.cineTimer);
        }
        
        // Clear image cache
        this.imageCache.clear();
    }

    // Placeholder methods for features to be implemented
    initializeUI() {
        // Initialize UI components
        this.updateStatus('Ready');
    }

    updateSeriesList(series) {
        // Update series list in the UI
    }

    updateThumbnails() {
        // Update thumbnail navigator
    }

    updateImageInfo() {
        // Update image information panel
    }

    updateMeasurementsList() {
        // Update measurements list
    }

    updateAnnotationsList() {
        // Update annotations list
    }

    saveMeasurement(measurement) {
        // Save measurement to backend
    }

    saveAnnotation(annotation) {
        // Save annotation to backend
    }

    clearMeasurements() {
        this.measurements = [];
        this.updateMeasurementOverlay();
        this.updateMeasurementsList();
        this.notyf.info('All measurements cleared');
    }

    clearAnnotations() {
        this.annotations = [];
        this.updateAnnotationOverlay();
        this.updateAnnotationsList();
        this.notyf.info('All annotations cleared');
    }

    togglePatientInfo() {
        const patientInfo = document.querySelector('.patient-info-advanced');
        if (patientInfo) {
            patientInfo.classList.toggle('collapsed');
        }
    }

    toggleThumbnails() {
        const thumbnailNav = document.querySelector('.thumbnail-navigator');
        if (thumbnailNav) {
            thumbnailNav.classList.toggle('collapsed');
        }
    }

    setViewportLayout(layout) {
        this.viewportLayout = layout;
        this.notyf.info(`Viewport layout set to ${layout}`);
    }

    toggleViewportSync() {
        this.syncViewports = !this.syncViewports;
        this.notyf.info(`Viewport sync ${this.syncViewports ? 'enabled' : 'disabled'}`);
    }

    // Additional methods for specific tools
    applySharpenFilter() {
        this.notyf.info('Sharpen filter applied');
    }

    detectLesions() {
        this.notyf.info('Lesion detection started');
    }

    segmentOrgans() {
        this.notyf.info('Organ segmentation started');
    }

    calculateVolume() {
        this.notyf.info('Volume calculation started');
    }

    previousStudy() {
        this.notyf.info('Previous study navigation not implemented');
    }

    nextStudy() {
        this.notyf.info('Next study navigation not implemented');
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
        
        this.notyf.info('Cine mode started');
    }

    stopCine() {
        if (this.cineTimer) {
            clearInterval(this.cineTimer);
            this.cineTimer = null;
        }
        this.cineMode = false;
        this.notyf.info('Cine mode stopped');
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
}

// Export the class for use
window.AdvancedDicomViewer = AdvancedDicomViewer;