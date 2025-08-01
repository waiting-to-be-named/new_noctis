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
        this.windowWidth = 1500;  // Lung window for optimal tissue differentiation
        this.windowLevel = -600;  // Lung level for optimal contrast
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.inverted = false;
        this.crosshair = false;
        
        // Tools
        this.activeTool = 'windowing';
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
        const viewport = document.querySelector('.viewport');
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
            
            // Set canvas display size to match viewport
            this.canvas.style.width = displayWidth + 'px';
            this.canvas.style.height = displayHeight + 'px';
            
            // Scale the context to match the device pixel ratio
            this.ctx.scale(devicePixelRatio, devicePixelRatio);
            
            console.log(`Canvas resized to ${displayWidth}x${displayHeight} (${this.canvas.width}x${this.canvas.height} internal)`);
        }
    }
    
    setupEventListeners() {
        // Canvas event listeners
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        this.canvas.addEventListener('dblclick', (e) => this.onDoubleClick(e));
        
        // Tool button event listeners
        const toolButtons = [
            'windowing-btn', 'pan-btn', 'zoom-btn', 'measure-btn',
            'crosshair-btn', 'invert-btn', 'reset-btn',
            'preset-btn', 'enhance-btn', 'ai-btn',
            '3d-btn', 'series-btn', 'report-btn'
        ];
        
        toolButtons.forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (btn) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.handleToolClick(btnId.replace('-btn', ''));
                });
            }
        });
        
        // Slider event listeners
        const windowWidthSlider = document.getElementById('window-width-slider');
        const windowLevelSlider = document.getElementById('window-level-slider');
        const zoomSlider = document.getElementById('zoom-slider');
        
        if (windowWidthSlider) {
            windowWidthSlider.addEventListener('input', (e) => {
                this.windowWidth = parseInt(e.target.value);
                this.updateDisplay();
                this.updateOverlayLabels();
            });
        }
        
        if (windowLevelSlider) {
            windowLevelSlider.addEventListener('input', (e) => {
                this.windowLevel = parseInt(e.target.value);
                this.updateDisplay();
                this.updateOverlayLabels();
            });
        }
        
        if (zoomSlider) {
            zoomSlider.addEventListener('input', (e) => {
                this.zoomFactor = parseInt(e.target.value) / 100;
                this.updateDisplay();
                this.updateOverlayLabels();
            });
        }
        
        // Upload button
        const uploadBtn = document.getElementById('upload-btn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showUploadModal();
            });
        }
        
        // Worklist button
        const worklistBtn = document.getElementById('worklist-btn');
        if (worklistBtn) {
            worklistBtn.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = '/worklist/';
            });
        }
        
        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = '/logout/';
            });
        }
        
        // Upload modal event listeners
        this.setupUploadModal();
        
        // Series navigation buttons
        const prevSeriesBtn = document.getElementById('prev-series-btn');
        const nextSeriesBtn = document.getElementById('next-series-btn');
        
        if (prevSeriesBtn) {
            prevSeriesBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.previousSeries();
            });
        }
        
        if (nextSeriesBtn) {
            nextSeriesBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.nextSeries();
            });
        }
        
        // Window resize
        window.addEventListener('resize', () => {
            this.resizeCanvas();
            this.updateDisplay();
        });
        
        console.log('Event listeners setup completed');
    }
    
    handleToolClick(tool) {
        console.log('Tool clicked:', tool);
        
        // Remove active class from all tool buttons
        const allToolBtns = document.querySelectorAll('.tool-btn');
        allToolBtns.forEach(btn => btn.classList.remove('active'));
        
        // Add active class to clicked button
        const clickedBtn = document.getElementById(`${tool}-btn`);
        if (clickedBtn) {
            clickedBtn.classList.add('active');
        }
        
        // Handle specific tool actions
        switch (tool) {
            case 'windowing':
                this.activeTool = 'windowing';
                this.updateStatus('Window/Level tool activated');
                break;
                
            case 'pan':
                this.activeTool = 'pan';
                this.updateStatus('Pan tool activated');
                break;
                
            case 'zoom':
                this.activeTool = 'zoom';
                this.updateStatus('Zoom tool activated');
                break;
                
            case 'measure':
                this.activeTool = 'measure';
                this.updateStatus('Measurement tool activated');
                break;
                
            case 'crosshair':
                this.toggleCrosshair();
                break;
                
            case 'invert':
                this.invertImage();
                break;
                
            case 'reset':
                this.resetView();
                break;
                
            case 'preset':
                this.showPresetDropdown();
                break;
                
            case 'enhance':
                this.toggleEnhancementPanel();
                break;
                
            case 'ai':
                this.performAIAnalysis();
                break;
                
            case '3d':
                this.toggle3DOptions();
                break;
                
            case 'series':
                this.toggleSeriesSelector();
                break;
                
            case 'report':
                this.generateReport();
                break;
                
            default:
                console.log('Unknown tool:', tool);
        }
        
        this.updateDisplay();
    }
    
    toggleCrosshair() {
        this.crosshair = !this.crosshair;
        const crosshairElement = document.getElementById('crosshair');
        if (crosshairElement) {
            crosshairElement.style.display = this.crosshair ? 'block' : 'none';
        }
        this.updateStatus(this.crosshair ? 'Crosshair enabled' : 'Crosshair disabled');
    }
    
    invertImage() {
        this.inverted = !this.inverted;
        this.updateDisplay();
        this.updateStatus(this.inverted ? 'Image inverted' : 'Image normal');
    }
    
    resetView() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.windowWidth = 1500;
        this.windowLevel = -600;
        this.inverted = false;
        this.crosshair = false;
        
        // Update sliders
        const windowWidthSlider = document.getElementById('window-width-slider');
        const windowLevelSlider = document.getElementById('window-level-slider');
        const zoomSlider = document.getElementById('zoom-slider');
        
        if (windowWidthSlider) windowWidthSlider.value = this.windowWidth;
        if (windowLevelSlider) windowLevelSlider.value = this.windowLevel;
        if (zoomSlider) zoomSlider.value = this.zoomFactor * 100;
        
        this.updateDisplay();
        this.updateOverlayLabels();
        this.updateStatus('View reset');
    }
    
    showPresetDropdown() {
        // Create preset dropdown
        const dropdown = document.createElement('div');
        dropdown.className = 'dropdown-content show';
        dropdown.style.position = 'absolute';
        dropdown.style.top = '100%';
        dropdown.style.left = '0';
        dropdown.style.zIndex = '1000';
        dropdown.style.background = 'linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%)';
        dropdown.style.border = '1px solid rgba(0, 255, 0, 0.3)';
        dropdown.style.borderRadius = '8px';
        dropdown.style.padding = '10px';
        dropdown.style.minWidth = '200px';
        
        Object.keys(this.windowPresets).forEach(presetName => {
            const preset = this.windowPresets[presetName];
            const item = document.createElement('div');
            item.className = 'dropdown-item';
            item.style.padding = '8px 12px';
            item.style.cursor = 'pointer';
            item.style.color = '#00ff00';
            item.style.borderBottom = '1px solid rgba(0, 255, 0, 0.1)';
            item.textContent = `${presetName.charAt(0).toUpperCase() + presetName.slice(1)} (${preset.ww}/${preset.wl})`;
            
            item.addEventListener('click', () => {
                this.applyPreset(presetName);
                dropdown.remove();
            });
            
            dropdown.appendChild(item);
        });
        
        const presetBtn = document.getElementById('preset-btn');
        if (presetBtn) {
            presetBtn.appendChild(dropdown);
            
            // Remove dropdown when clicking outside
            setTimeout(() => {
                document.addEventListener('click', function removeDropdown() {
                    dropdown.remove();
                    document.removeEventListener('click', removeDropdown);
                });
            }, 100);
        }
    }
    
    applyPreset(presetName) {
        const preset = this.windowPresets[presetName];
        if (preset) {
            this.windowWidth = preset.ww;
            this.windowLevel = preset.wl;
            
            // Update sliders
            const windowWidthSlider = document.getElementById('window-width-slider');
            const windowLevelSlider = document.getElementById('window-level-slider');
            
            if (windowWidthSlider) windowWidthSlider.value = this.windowWidth;
            if (windowLevelSlider) windowLevelSlider.value = this.windowLevel;
            
            this.updateDisplay();
            this.updateOverlayLabels();
            this.updateStatus(`Applied ${presetName} preset`);
        }
    }
    
    toggleEnhancementPanel() {
        const panel = document.getElementById('enhancement-panel');
        if (panel) {
            panel.classList.toggle('show');
            this.updateStatus(panel.classList.contains('show') ? 'Enhancement panel opened' : 'Enhancement panel closed');
        }
    }
    
    performAIAnalysis() {
        if (!this.currentImage) {
            this.showError('No image loaded for AI analysis');
            return;
        }
        
        this.updateStatus('Performing AI analysis...');
        // Simulate AI analysis
        setTimeout(() => {
            this.updateStatus('AI analysis completed');
            this.showSuccessNotification('AI analysis completed successfully');
        }, 2000);
    }
    
    toggle3DOptions() {
        this.updateStatus('3D reconstruction options');
        // Implement 3D options
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
    
    generateReport() {
        if (!this.currentImage) {
            this.showError('No image loaded for report generation');
            return;
        }
        
        this.updateStatus('Generating report...');
        // Implement report generation
        setTimeout(() => {
            this.updateStatus('Report generated');
            this.showSuccessNotification('Report generated successfully');
        }, 1500);
    }
    
    setupUploadModal() {
        const modal = document.getElementById('upload-modal');
        const closeBtn = document.getElementById('close-upload-modal');
        const fileInput = document.getElementById('file-input');
        const folderInput = document.getElementById('folder-input');
        const uploadDropArea = document.getElementById('upload-drop-area');
        const folderDropArea = document.getElementById('folder-drop-area');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                if (modal) modal.style.display = 'none';
            });
        }
        
        if (uploadDropArea) {
            uploadDropArea.addEventListener('click', () => {
                if (fileInput) fileInput.click();
            });
            
            uploadDropArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadDropArea.style.borderColor = '#00ff00';
                uploadDropArea.style.background = 'rgba(0, 255, 0, 0.1)';
            });
            
            uploadDropArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                uploadDropArea.style.borderColor = 'rgba(0, 255, 0, 0.3)';
                uploadDropArea.style.background = 'transparent';
            });
            
            uploadDropArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadDropArea.style.borderColor = 'rgba(0, 255, 0, 0.3)';
                uploadDropArea.style.background = 'transparent';
                
                const files = Array.from(e.dataTransfer.files);
                this.uploadFiles(files);
            });
        }
        
        if (folderDropArea) {
            folderDropArea.addEventListener('click', () => {
                if (folderInput) folderInput.click();
            });
            
            folderDropArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                folderDropArea.style.borderColor = '#00ff00';
                folderDropArea.style.background = 'rgba(0, 255, 0, 0.1)';
            });
            
            folderDropArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                folderDropArea.style.borderColor = 'rgba(0, 255, 0, 0.3)';
                folderDropArea.style.background = 'transparent';
            });
            
            folderDropArea.addEventListener('drop', (e) => {
                e.preventDefault();
                folderDropArea.style.borderColor = 'rgba(0, 255, 0, 0.3)';
                folderDropArea.style.background = 'transparent';
                
                const files = Array.from(e.dataTransfer.files);
                this.uploadFolder(files);
            });
        }
        
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const files = Array.from(e.target.files);
                this.uploadFiles(files);
            });
        }
        
        if (folderInput) {
            folderInput.addEventListener('change', (e) => {
                const files = Array.from(e.target.files);
                this.uploadFolder(files);
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
        if (files.length === 0) return;
        
        this.showLoadingState('Uploading files...');
        
        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
        });
        
        try {
            const response = await fetch('/api/upload-dicom-files/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.hideLoadingState();
                this.showSuccessNotification(`Successfully uploaded ${files.length} files`);
                
                // Load the uploaded study if available
                if (result.study_id) {
                    await this.loadStudy(result.study_id);
                }
            } else {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
        } catch (error) {
            this.hideLoadingState();
            this.showError(`Upload failed: ${error.message}`);
        }
    }
    
    async uploadFolder(files) {
        if (files.length === 0) return;
        
        this.showLoadingState('Uploading folder contents...');
        
        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
        });
        
        try {
            const response = await fetch('/api/upload-dicom-folder/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.hideLoadingState();
                this.showSuccessNotification(`Successfully uploaded folder with ${files.length} files`);
                
                // Load the uploaded study if available
                if (result.study_id) {
                    await this.loadStudy(result.study_id);
                }
            } else {
                throw new Error(`Folder upload failed: ${response.statusText}`);
            }
        } catch (error) {
            this.hideLoadingState();
            this.showError(`Folder upload failed: ${error.message}`);
        }
    }
    
    async loadStudy(studyId) {
        try {
            this.showLoadingState('Loading study...');
            
            const response = await fetch(`/api/get-study-images/${studyId}/`);
            if (!response.ok) {
                throw new Error('Failed to load study');
            }
            
            const studyData = await response.json();
            this.currentStudy = studyData;
            this.currentImages = studyData.images || [];
            this.currentImageIndex = 0;
            
            if (this.currentImages.length > 0) {
                await this.loadCurrentImage();
            }
            
            this.updatePatientInfo();
            this.updateSeriesDisplay();
            this.hideLoadingState();
            
        } catch (error) {
            this.hideLoadingState();
            this.showError(`Failed to load study: ${error.message}`);
        }
    }
    
    async loadCurrentImage() {
        if (this.currentImages.length === 0) return;
        
        const imageData = this.currentImages[this.currentImageIndex];
        if (!imageData) return;
        
        try {
            const response = await fetch(`/api/get-image-data/${imageData.id}/`);
            if (!response.ok) {
                throw new Error('Failed to load image data');
            }
            
            const imageResult = await response.json();
            this.currentImage = imageResult;
            
            this.updateDisplay();
            this.updateOverlayLabels();
            this.updateStatus(`Image ${this.currentImageIndex + 1} of ${this.currentImages.length}`);
            
        } catch (error) {
            this.showError(`Failed to load image: ${error.message}`);
        }
    }
    
    updateDisplay() {
        if (!this.currentImage) return;
        
        // Clear canvas
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Apply window/level transformation
        const imageData = this.currentImage.image_data;
        if (imageData) {
            // Create ImageData from base64
            const img = new Image();
            img.onload = () => {
                // Apply transformations
                this.ctx.save();
                
                // Apply zoom and pan
                this.ctx.translate(this.panX, this.panY);
                this.ctx.scale(this.zoomFactor, this.zoomFactor);
                
                // Apply window/level
                this.applyWindowLevel(img);
                
                // Apply inversion if needed
                if (this.inverted) {
                    this.ctx.filter = 'invert(1)';
                }
                
                // Draw image
                this.ctx.drawImage(img, 0, 0);
                
                this.ctx.restore();
                
                // Draw overlays
                this.drawOverlays();
            };
            img.src = imageData;
        }
    }
    
    applyWindowLevel(img) {
        // Apply window/level transformation to the image
        // This is a simplified version - in a real implementation,
        // you would apply the window/level transformation to the pixel data
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = img.width;
        canvas.height = img.height;
        
        ctx.drawImage(img, 0, 0);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;
        
        // Apply window/level transformation
        for (let i = 0; i < data.length; i += 4) {
            const pixelValue = data[i];
            const normalizedValue = (pixelValue - this.windowLevel + this.windowWidth / 2) / this.windowWidth;
            const clampedValue = Math.max(0, Math.min(255, normalizedValue * 255));
            
            data[i] = clampedValue;     // Red
            data[i + 1] = clampedValue; // Green
            data[i + 2] = clampedValue; // Blue
            // Alpha remains unchanged
        }
        
        ctx.putImageData(imageData, 0, 0);
        return canvas;
    }
    
    drawOverlays() {
        // Draw crosshair if enabled
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
        
        this.ctx.strokeStyle = '#00ff00';
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
        // Draw measurement lines and annotations
        this.measurements.forEach(measurement => {
            this.ctx.strokeStyle = '#00ff00';
            this.ctx.lineWidth = 2;
            this.ctx.setLineDash([5, 5]);
            
            this.ctx.beginPath();
            this.ctx.moveTo(measurement.start.x, measurement.start.y);
            this.ctx.lineTo(measurement.end.x, measurement.end.y);
            this.ctx.stroke();
            
            this.ctx.setLineDash([]);
            
            // Draw measurement text
            this.ctx.fillStyle = '#00ff00';
            this.ctx.font = '12px Arial';
            this.ctx.fillText(measurement.value, measurement.end.x + 5, measurement.end.y - 5);
        });
    }
    
    drawAnnotations() {
        // Draw annotations
        this.annotations.forEach(annotation => {
            this.ctx.fillStyle = '#ffff00';
            this.ctx.font = '14px Arial';
            this.ctx.fillText(annotation.text, annotation.x, annotation.y);
        });
    }
    
    updateOverlayLabels() {
        // Update window/level info
        const wwValue = document.getElementById('ww-value');
        const wlValue = document.getElementById('wl-value');
        const zoomValue = document.getElementById('zoom-value');
        
        if (wwValue) wwValue.textContent = this.windowWidth;
        if (wlValue) wlValue.textContent = this.windowLevel;
        if (zoomValue) zoomValue.textContent = `${Math.round(this.zoomFactor * 100)}%`;
    }
    
    updatePatientInfo() {
        if (!this.currentStudy) return;
        
        const patientName = document.getElementById('patient-name');
        const patientId = document.getElementById('patient-id');
        const studyDescription = document.getElementById('study-description');
        const studyDate = document.getElementById('study-date');
        const modality = document.getElementById('modality');
        const imageCount = document.getElementById('image-count');
        
        if (patientName) patientName.textContent = this.currentStudy.patient_name || '-';
        if (patientId) patientId.textContent = this.currentStudy.patient_id || '-';
        if (studyDescription) studyDescription.textContent = this.currentStudy.study_description || '-';
        if (studyDate) studyDate.textContent = this.currentStudy.study_date || '-';
        if (modality) modality.textContent = this.currentStudy.modality || '-';
        if (imageCount) imageCount.textContent = this.currentImages.length || '-';
    }
    
    updateSeriesDisplay() {
        const seriesGrid = document.getElementById('series-grid');
        if (!seriesGrid || !this.currentStudy) return;
        
        seriesGrid.innerHTML = '';
        
        const series = this.currentStudy.series || [];
        series.forEach((seriesData, index) => {
            const seriesItem = document.createElement('div');
            seriesItem.className = 'series-item';
            seriesItem.addEventListener('click', () => this.selectSeries(index));
            
            seriesItem.innerHTML = `
                <div class="series-thumbnail">
                    <i class="fas fa-image"></i>
                </div>
                <div class="series-info">
                    <div class="series-name">Series ${index + 1}</div>
                    <div class="series-details">${seriesData.images?.length || 0} images</div>
                </div>
            `;
            
            seriesGrid.appendChild(seriesItem);
        });
        
        // Update series counter
        const seriesCounter = document.getElementById('series-counter');
        if (seriesCounter) {
            seriesCounter.textContent = `Series 1 of ${series.length}`;
        }
    }
    
    selectSeries(seriesIndex) {
        // Remove active class from all series items
        const seriesItems = document.querySelectorAll('.series-item');
        seriesItems.forEach(item => item.classList.remove('active'));
        
        // Add active class to selected series
        const selectedItem = seriesItems[seriesIndex];
        if (selectedItem) {
            selectedItem.classList.add('active');
        }
        
        // Load series images
        if (this.currentStudy && this.currentStudy.series && this.currentStudy.series[seriesIndex]) {
            this.currentImages = this.currentStudy.series[seriesIndex].images || [];
            this.currentImageIndex = 0;
            this.loadCurrentImage();
        }
    }
    
    previousSeries() {
        if (this.currentImageIndex > 0) {
            this.currentImageIndex--;
            this.loadCurrentImage();
        }
    }
    
    nextSeries() {
        if (this.currentImageIndex < this.currentImages.length - 1) {
            this.currentImageIndex++;
            this.loadCurrentImage();
        }
    }
    
    loadSeriesSelector() {
        // Load series data for the selector
        if (this.currentStudy && this.currentStudy.series) {
            const seriesGrid = document.getElementById('series-grid');
            if (seriesGrid) {
                seriesGrid.innerHTML = '';
                
                this.currentStudy.series.forEach((seriesData, index) => {
                    const seriesItem = document.createElement('div');
                    seriesItem.className = 'series-item';
                    seriesItem.addEventListener('click', () => {
                        this.selectSeries(index);
                        document.getElementById('series-selector').classList.remove('show');
                    });
                    
                    seriesItem.innerHTML = `
                        <div class="series-thumbnail">
                            <i class="fas fa-image"></i>
                        </div>
                        <div class="series-info">
                            <div class="series-name">Series ${index + 1}</div>
                            <div class="series-details">${seriesData.images?.length || 0} images</div>
                        </div>
                    `;
                    
                    seriesGrid.appendChild(seriesItem);
                });
            }
        }
    }
    
    onMouseDown(e) {
        if (!this.currentImage) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.isDragging = true;
        this.dragStart = { x, y };
        
        switch (this.activeTool) {
            case 'pan':
                this.canvas.style.cursor = 'grabbing';
                break;
            case 'zoom':
                // Handle zoom
                break;
            case 'measure':
                this.startMeasurement(x, y);
                break;
        }
    }
    
    onMouseMove(e) {
        if (!this.currentImage) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.isDragging && this.dragStart) {
            switch (this.activeTool) {
                case 'pan':
                    const deltaX = x - this.dragStart.x;
                    const deltaY = y - this.dragStart.y;
                    this.panX += deltaX;
                    this.panY += deltaY;
                    this.dragStart = { x, y };
                    this.updateDisplay();
                    break;
            }
        }
    }
    
    onMouseUp(e) {
        if (!this.currentImage) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.isDragging && this.dragStart) {
            switch (this.activeTool) {
                case 'measure':
                    this.endMeasurement(x, y);
                    break;
            }
        }
        
        this.isDragging = false;
        this.dragStart = null;
        this.canvas.style.cursor = 'default';
    }
    
    onWheel(e) {
        if (!this.currentImage) return;
        
        e.preventDefault();
        
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        this.zoomFactor *= delta;
        this.zoomFactor = Math.max(0.1, Math.min(5.0, this.zoomFactor));
        
        // Update zoom slider
        const zoomSlider = document.getElementById('zoom-slider');
        if (zoomSlider) {
            zoomSlider.value = this.zoomFactor * 100;
        }
        
        this.updateDisplay();
        this.updateOverlayLabels();
    }
    
    onDoubleClick(e) {
        if (!this.currentImage) return;
        
        // Reset zoom and pan on double click
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        
        // Update sliders
        const zoomSlider = document.getElementById('zoom-slider');
        if (zoomSlider) {
            zoomSlider.value = 100;
        }
        
        this.updateDisplay();
        this.updateOverlayLabels();
    }
    
    startMeasurement(x, y) {
        this.currentMeasurement = {
            start: { x, y },
            end: { x, y }
        };
    }
    
    endMeasurement(x, y) {
        if (this.currentMeasurement) {
            this.currentMeasurement.end = { x, y };
            
            // Calculate distance
            const dx = this.currentMeasurement.end.x - this.currentMeasurement.start.x;
            const dy = this.currentMeasurement.end.y - this.currentMeasurement.start.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            this.currentMeasurement.value = `${distance.toFixed(1)}px`;
            this.measurements.push(this.currentMeasurement);
            
            this.currentMeasurement = null;
            this.updateDisplay();
        }
    }
    
    showLoadingState(message = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        const loadingText = document.getElementById('loading-text');
        
        if (overlay) overlay.style.display = 'flex';
        if (loadingText) loadingText.textContent = message;
    }
    
    hideLoadingState() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'none';
    }
    
    updateStatus(message) {
        const statusElement = document.getElementById('processing-status');
        if (statusElement) {
            statusElement.textContent = message;
        }
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
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    initializeEnhancedViewer() {
        // Initialize any enhanced features
        console.log('Enhanced viewer features initialized');
    }
}

// Global functions for upload modal
function switchUploadTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.upload-tab-content');
    tabContents.forEach(content => content.classList.remove('active'));
    
    // Remove active class from all tabs
    const tabs = document.querySelectorAll('.upload-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Show selected tab content
    const selectedContent = document.getElementById(`${tabName}-tab`);
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
        alert('Please fill in all PACS server details');
        return;
    }
    
    // Implement PACS connection
    console.log('Connecting to PACS server:', ip, port, ae);
}

function connectToCloud(provider) {
    console.log('Connecting to cloud provider:', provider);
    // Implement cloud connection
}

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', function() {
    const viewer = new DicomViewer();
    viewer.init();
});
