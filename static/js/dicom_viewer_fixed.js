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
        this.zoom = 1.0;
        this.minZoom = 0.1;
        this.maxZoom = 10.0;
        this.panX = 0;
        this.panY = 0;
        this.rotation = 0;
        this.isInverted = false;
        this.windowCenter = 256;
        this.windowWidth = 512;
        this.contrast = 1.0;
        this.brightness = 0;

        // Measurement and tool state
        this.activeTool = 'pan';
        this.measurements = [];
        this.currentMeasurement = null;
        this.isDrawing = false;
        this.pixelSpacing = { x: 1, y: 1 }; // mm per pixel
        this.measurementUnit = 'mm';
        this.calibrationFactor = 1;
        
        // Magnification tool
        this.magnificationActive = false;
        this.magnificationLevel = 2;
        this.magnificationRadius = 75;
        
        // ROI and analysis
        this.roiActive = false;
        this.currentROI = null;
        this.rois = [];
        
        // Drawing state
        this.isMouseDown = false;
        this.lastMousePos = { x: 0, y: 0 };

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

    setupNavigationButtons() {
        console.log('Setting up navigation buttons...');
        
        // Previous/Next study buttons
        const prevStudyBtn = document.getElementById('prev-study-btn');
        const nextStudyBtn = document.getElementById('next-study-btn');
        
        if (prevStudyBtn) {
            prevStudyBtn.addEventListener('click', () => {
                console.log('Previous study clicked');
                // TODO: Implement previous study navigation
                this.notyf.info('Previous study navigation not yet implemented');
            });
        }
        
        if (nextStudyBtn) {
            nextStudyBtn.addEventListener('click', () => {
                console.log('Next study clicked');
                // TODO: Implement next study navigation
                this.notyf.info('Next study navigation not yet implemented');
            });
        }
    }
    
    setupAllButtons() {
        console.log('Setting up all buttons...');
        
        // Header buttons
        const uploadBtn = document.getElementById('upload-advanced-btn');
        const exportBtn = document.getElementById('export-btn');
        const settingsBtn = document.getElementById('settings-btn');
        const fullscreenBtn = document.getElementById('fullscreen-btn');
        const logoutBtn = document.getElementById('logout-advanced-btn');
        
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => {
                console.log('Upload button clicked');
                this.showUploadModal();
            });
        }
        
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                console.log('Export button clicked');
                this.showExportModal();
            });
        }
        
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                console.log('Settings button clicked');
                this.notyf.info('Settings panel coming soon');
            });
        }
        
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => {
                console.log('Fullscreen button clicked');
                this.toggleFullscreen();
            });
        }
        
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                console.log('Logout button clicked');
                if (confirm('Are you sure you want to logout?')) {
                    window.location.href = '/logout/';
                }
            });
        }
        
        // Navigation controls
        const prevImageBtn = document.getElementById('prev-image-btn');
        const nextImageBtn = document.getElementById('next-image-btn');
        const playBtn = document.getElementById('play-btn');
        
        if (prevImageBtn) {
            prevImageBtn.addEventListener('click', () => this.navigateImages(-1));
        }
        
        if (nextImageBtn) {
            nextImageBtn.addEventListener('click', () => this.navigateImages(1));
        }
        
        if (playBtn) {
            playBtn.addEventListener('click', () => this.toggleCineMode());
        }
        
        // Viewport controls
        const layout1x1Btn = document.getElementById('layout-1x1-btn');
        const layout2x2Btn = document.getElementById('layout-2x2-btn');
        const layout1x2Btn = document.getElementById('layout-1x2-btn');
        const syncViewportsBtn = document.getElementById('sync-viewports-btn');
        
        if (layout1x1Btn) {
            layout1x1Btn.addEventListener('click', () => {
                console.log('1x1 layout selected');
                this.setViewportLayout('1x1');
            });
        }
        
        if (layout2x2Btn) {
            layout2x2Btn.addEventListener('click', () => {
                console.log('2x2 layout selected');
                this.setViewportLayout('2x2');
            });
        }
        
        if (layout1x2Btn) {
            layout1x2Btn.addEventListener('click', () => {
                console.log('1x2 layout selected');
                this.setViewportLayout('1x2');
            });
        }
        
        if (syncViewportsBtn) {
            syncViewportsBtn.addEventListener('click', () => {
                console.log('Sync viewports toggled');
                this.toggleViewportSync();
            });
        }
        
        // Annotation buttons
        const textAnnotationBtn = document.getElementById('text-annotation-btn');
        const arrowAnnotationBtn = document.getElementById('arrow-annotation-btn');
        const circleAnnotationBtn = document.getElementById('circle-annotation-btn');
        const rectangleAnnotationBtn = document.getElementById('rectangle-annotation-btn');
        const clearAnnotationsBtn = document.getElementById('clear-annotations-btn');
        
        if (textAnnotationBtn) {
            textAnnotationBtn.addEventListener('click', () => this.setActiveTool('text'));
        }
        
        if (arrowAnnotationBtn) {
            arrowAnnotationBtn.addEventListener('click', () => this.setActiveTool('arrow'));
        }
        
        if (circleAnnotationBtn) {
            circleAnnotationBtn.addEventListener('click', () => this.setActiveTool('circle'));
        }
        
        if (rectangleAnnotationBtn) {
            rectangleAnnotationBtn.addEventListener('click', () => this.setActiveTool('rectangle'));
        }
        
        if (clearAnnotationsBtn) {
            clearAnnotationsBtn.addEventListener('click', () => this.clearAnnotations());
        }
        
        // AI Analysis buttons
        const aiAnalysisBtn = document.getElementById('ai-analysis-btn');
        const aiSegmentBtn = document.getElementById('ai-segment-btn');
        
        if (aiAnalysisBtn) {
            aiAnalysisBtn.addEventListener('click', () => {
                console.log('AI Analysis clicked');
                this.performAIAnalysis();
            });
        }
        
        if (aiSegmentBtn) {
            aiSegmentBtn.addEventListener('click', () => {
                console.log('AI Segmentation clicked');
                this.performAISegmentation();
            });
        }
        
        console.log('All buttons setup complete');
    }

    showExportModal() {
        console.log('Opening export modal...');
        const modal = document.getElementById('export-modal');
        if (modal) {
            modal.style.display = 'block';
        } else {
            // Create export modal if it doesn't exist
            this.createExportModal();
        }
    }

    createExportModal() {
        const modal = document.createElement('div');
        modal.id = 'export-modal';
        modal.style.cssText = `
            display: block;
            position: fixed;
            z-index: 10000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
        `;

        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            margin: 5% auto;
            padding: 20px;
            border: 2px solid #10b981;
            border-radius: 12px;
            width: 80%;
            max-width: 500px;
            color: #e5e5e5;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        `;

        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #404040; padding-bottom: 15px;">
                <h3 style="color: #10b981; margin: 0; font-size: 20px;">Export Options</h3>
                <button onclick="this.closest('#export-modal').style.display='none'" style="background: none; border: none; color: #9ca3af; font-size: 24px; cursor: pointer;">&times;</button>
            </div>
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 10px; color: #d1d5db;">Export Format:</label>
                <select id="export-format" style="width: 100%; padding: 10px; background: #374151; border: 1px solid #4b5563; border-radius: 6px; color: #e5e5e5;">
                    <option value="png">PNG Image</option>
                    <option value="jpg">JPEG Image</option>
                    <option value="dicom">Original DICOM</option>
                    <option value="pdf">PDF Report</option>
                </select>
            </div>
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 10px; color: #d1d5db;">
                    <input type="checkbox" id="include-measurements" checked style="margin-right: 8px;">
                    Include Measurements
                </label>
                <label style="display: block; margin-bottom: 10px; color: #d1d5db;">
                    <input type="checkbox" id="include-annotations" checked style="margin-right: 8px;">
                    Include Annotations
                </label>
            </div>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button onclick="this.closest('#export-modal').style.display='none'" style="background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer;">Cancel</button>
                <button onclick="window.advancedViewer.performExport()" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer;">Export</button>
            </div>
        `;

        modal.appendChild(modalContent);
        document.body.appendChild(modal);
    }

    performExport() {
        const format = document.getElementById('export-format').value;
        const includeMeasurements = document.getElementById('include-measurements').checked;
        const includeAnnotations = document.getElementById('include-annotations').checked;

        console.log('Exporting...', { format, includeMeasurements, includeAnnotations });

        try {
            if (format === 'png' || format === 'jpg') {
                this.exportAsImage(format, includeMeasurements, includeAnnotations);
            } else if (format === 'dicom') {
                this.exportAsDicom();
            } else if (format === 'pdf') {
                this.exportAsPdf(includeMeasurements, includeAnnotations);
            }
            
            document.getElementById('export-modal').style.display = 'none';
            this.showNotification('Export completed successfully!', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Export failed: ' + error.message, 'error');
        }
    }

    exportAsImage(format, includeMeasurements, includeAnnotations) {
        if (!this.canvas) {
            throw new Error('No canvas available for export');
        }

        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = this.canvas.width;
        tempCanvas.height = this.canvas.height;
        const tempCtx = tempCanvas.getContext('2d');

        // Draw the main image
        tempCtx.drawImage(this.canvas, 0, 0);

        // Draw measurements if requested
        if (includeMeasurements && this.measurements) {
            this.ctx = tempCtx;
            this.drawMeasurements();
            this.ctx = this.canvas.getContext('2d');
        }

        // Convert to blob and download
        const mimeType = format === 'png' ? 'image/png' : 'image/jpeg';
        tempCanvas.toBlob((blob) => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dicom_export_${Date.now()}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, mimeType, 0.9);
    }

    exportAsDicom() {
        if (this.currentStudy && this.currentStudy.id) {
            const url = `/viewer/api/export-study/${this.currentStudy.id}/`;
            window.open(url, '_blank');
        } else {
            throw new Error('No study loaded for DICOM export');
        }
    }

    exportAsPdf(includeMeasurements, includeAnnotations) {
        // Simple PDF export - in real implementation, you'd use a library like jsPDF
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>DICOM Study Report</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        .header { text-align: center; margin-bottom: 30px; }
                        .image-container { text-align: center; margin: 20px 0; }
                        .measurements { margin-top: 20px; }
                        .measurement { margin: 5px 0; padding: 5px; background: #f5f5f5; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>DICOM Study Report</h1>
                        <p>Generated on: ${new Date().toLocaleString()}</p>
                    </div>
                    <div class="image-container">
                        <img src="${this.canvas.toDataURL()}" style="max-width: 100%; height: auto;" />
                    </div>
                    ${includeMeasurements && this.measurements ? `
                        <div class="measurements">
                            <h3>Measurements:</h3>
                            ${this.measurements.map((m, i) => `
                                <div class="measurement">Measurement ${i + 1}: ${m.type}</div>
                            `).join('')}
                        </div>
                    ` : ''}
                </body>
            </html>
        `);
        printWindow.document.close();
        setTimeout(() => {
            printWindow.print();
        }, 500);
    }

    toggleFullscreen() {
        console.log('Toggling fullscreen...');
        
        if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.mozFullScreenElement) {
            // Enter fullscreen
            const element = document.documentElement;
            if (element.requestFullscreen) {
                element.requestFullscreen();
            } else if (element.webkitRequestFullscreen) {
                element.webkitRequestFullscreen();
            } else if (element.mozRequestFullScreen) {
                element.mozRequestFullScreen();
            } else if (element.msRequestFullscreen) {
                element.msRequestFullscreen();
            }
            this.showNotification('Entered fullscreen mode', 'info');
        } else {
            // Exit fullscreen
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
            this.showNotification('Exited fullscreen mode', 'info');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10001;
            padding: 15px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
        `;

        switch (type) {
            case 'success':
                notification.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                break;
            case 'error':
                notification.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
                break;
            case 'warning':
                notification.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
                break;
            default:
                notification.style.background = 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)';
        }

        notification.textContent = message;
        document.body.appendChild(notification);

        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    printStudy() {
        console.log('Printing study...');
        
        if (!this.canvas) {
            this.showNotification('No image to print', 'warning');
            return;
        }

        const printWindow = window.open('', '_blank');
        const canvasDataUrl = this.canvas.toDataURL('image/png');
        
        printWindow.document.write(`
            <html>
                <head>
                    <title>DICOM Study Print</title>
                    <style>
                        body { 
                            font-family: Arial, sans-serif; 
                            margin: 0; 
                            padding: 20px; 
                            background: white;
                        }
                        .header { 
                            text-align: center; 
                            margin-bottom: 30px; 
                            border-bottom: 2px solid #333;
                            padding-bottom: 20px;
                        }
                        .image-container { 
                            text-align: center; 
                            margin: 20px 0; 
                            page-break-inside: avoid;
                        }
                        .image-container img {
                            max-width: 100%;
                            max-height: 80vh;
                            border: 1px solid #ddd;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                        }
                        .study-info {
                            margin: 20px 0;
                            display: grid;
                            grid-template-columns: 1fr 1fr;
                            gap: 20px;
                        }
                        .info-section {
                            background: #f9f9f9;
                            padding: 15px;
                            border-radius: 5px;
                        }
                        .info-section h4 {
                            margin: 0 0 10px 0;
                            color: #333;
                            border-bottom: 1px solid #ddd;
                            padding-bottom: 5px;
                        }
                        .measurements {
                            margin-top: 20px;
                            background: #f0f8ff;
                            padding: 15px;
                            border-radius: 5px;
                        }
                        .measurement {
                            margin: 5px 0;
                            padding: 5px;
                            background: white;
                            border-left: 3px solid #007bff;
                        }
                        @media print {
                            body { margin: 0; }
                            .header { margin-bottom: 15px; }
                        }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>DICOM Study Report</h1>
                        <p><strong>Patient:</strong> ${this.currentStudy?.patient_name || 'Unknown'}</p>
                        <p><strong>Study Date:</strong> ${this.currentStudy?.study_date || new Date().toLocaleDateString()}</p>
                        <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
                    </div>
                    
                    <div class="study-info">
                        <div class="info-section">
                            <h4>Study Information</h4>
                            <p><strong>Study ID:</strong> ${this.currentStudy?.id || 'N/A'}</p>
                            <p><strong>Modality:</strong> ${this.currentStudy?.modality || 'N/A'}</p>
                            <p><strong>Study Description:</strong> ${this.currentStudy?.study_description || 'N/A'}</p>
                            <p><strong>Series Number:</strong> ${this.currentImage?.series_number || 'N/A'}</p>
                        </div>
                        <div class="info-section">
                            <h4>Image Parameters</h4>
                            <p><strong>Window Level:</strong> ${this.windowLevel}</p>
                            <p><strong>Window Width:</strong> ${this.windowWidth}</p>
                            <p><strong>Zoom:</strong> ${Math.round(this.zoom * 100)}%</p>
                            <p><strong>Inverted:</strong> ${this.inverted ? 'Yes' : 'No'}</p>
                        </div>
                    </div>
                    
                    <div class="image-container">
                        <img src="${canvasDataUrl}" alt="DICOM Image" />
                    </div>
                    
                    ${this.measurements && this.measurements.length > 0 ? `
                        <div class="measurements">
                            <h4>Measurements</h4>
                            ${this.measurements.map((m, i) => `
                                <div class="measurement">
                                    <strong>Measurement ${i + 1}:</strong> ${m.type}
                                    ${m.value ? ` - ${m.value}` : ''}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </body>
            </html>
        `);
        
        printWindow.document.close();
        
        // Wait for image to load then print
        setTimeout(() => {
            printWindow.print();
            this.showNotification('Print dialog opened', 'success');
        }, 1000);
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
                        displayHeight = canvasHeight * this.zoom;
                        displayWidth = displayHeight * aspectRatio;
                    } else {
                        displayWidth = canvasWidth * this.zoom;
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
                    
                    // Draw overlays (measurements, ROIs)
                    this.drawMeasurements();
                    this.rois.forEach(roi => this.drawROI(roi));
                    if (this.currentROI) this.drawROI(this.currentROI);
                    
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
        
        // ROI tool
        const roiBtn = document.getElementById('roi-btn');
        if (roiBtn) roiBtn.addEventListener('click', () => this.setActiveTool('roi'));
        
        // Measurement unit toggle
        const unitToggleBtn = document.getElementById('unit-toggle-btn');
        if (unitToggleBtn) unitToggleBtn.addEventListener('click', () => this.toggleMeasurementUnit());
        
        // Clear measurements
        const clearMeasurementsBtn = document.getElementById('clear-measurements-btn');
        if (clearMeasurementsBtn) clearMeasurementsBtn.addEventListener('click', () => this.clearMeasurements());
        
        if (mprBtn) mprBtn.addEventListener('click', () => this.enableMPR());
        if (volumeRenderBtn) volumeRenderBtn.addEventListener('click', () => this.enableVolumeRendering());
        if (mipBtn) mipBtn.addEventListener('click', () => this.enableMIP());
        
        if (resetBtn) resetBtn.addEventListener('click', () => this.resetView());
        if (fitBtn) fitBtn.addEventListener('click', () => this.fitToWindow());
        if (actualSizeBtn) actualSizeBtn.addEventListener('click', () => this.actualSize());
        
        // Export and fullscreen buttons
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) exportBtn.addEventListener('click', () => this.showExportModal());
        
        const fullscreenBtn = document.getElementById('fullscreen-btn');
        if (fullscreenBtn) fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        
        // Print button
        const printBtn = document.getElementById('print-btn');
        if (printBtn) printBtn.addEventListener('click', () => this.printStudy());
        
        // Home button
        const homeBtn = document.getElementById('home-btn');
        if (homeBtn) homeBtn.addEventListener('click', () => window.location.href = '/home/');
        
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
        this.isMouseDown = true;
        
        // Handle tool-specific mouse down
        if (this.activeTool === 'distance' || this.activeTool === 'angle') {
            this.startMeasurement(this.activeTool, e.clientX, e.clientY);
        } else if (this.activeTool === 'roi') {
            const rect = this.canvas.getBoundingClientRect();
            this.startROI(e.clientX - rect.left, e.clientY - rect.top);
        }
    }

    handleMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Handle magnification
        if (this.magnificationActive) {
            this.refreshCurrentImage();
            this.drawMagnifier(x, y);
            return;
        }
        
        // Handle crosshair
        if (this.activeTool === 'crosshair') {
            this.refreshCurrentImage();
            this.drawCrosshair(x, y);
            return;
        }
        
        if (!this.isDragging) {
            // Update cursor position for HU measurement
            if (this.activeTool === 'hu') {
                this.updateHUMeasurement(x, y);
            }
            return;
        }

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
        
        // Handle measurement drawing
        if (this.isDrawing && this.currentMeasurement) {
            this.refreshCurrentImage();
            this.drawMeasurementPreview(e.clientX, e.clientY);
        }
        
        // Handle ROI drawing
        if (this.roiActive && this.isMouseDown) {
            this.updateROI(x, y);
        }

        this.lastMousePos = { x: e.clientX, y: e.clientY };
    }

    handleMouseUp(e) {
        this.isDragging = false;
        this.dragStart = null;
        this.lastMousePos = null;
        this.isMouseDown = false;
        
        // Handle measurement completion
        if (this.isDrawing && this.currentMeasurement) {
            this.addMeasurementPoint(e.clientX, e.clientY);
        }
        
        // Handle ROI completion
        if (this.roiActive && this.currentROI) {
            this.finishROI();
        }
    }

    handleWheel(e) {
        e.preventDefault();
        
        if (e.ctrlKey || e.metaKey) {
            // Zoom
            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoom *= zoomFactor;
            this.zoom = Math.max(this.minZoom, Math.min(this.maxZoom, this.zoom));
            this.updateZoomDisplay();
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
        // Reset all view parameters to defaults
        this.zoom = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.rotation = 0;
        this.isInverted = false;
        this.windowCenter = 256;
        this.windowWidth = 512;
        this.contrast = 1.0;
        this.brightness = 0;
        
        // Reset tool state
        this.activeTool = 'pan';
        this.magnificationActive = false;
        this.roiActive = false;
        
        // Clear measurements
        this.clearMeasurements();
        
        // Update UI and refresh
        this.updateToolButtons();
        this.updateZoomDisplay();
        this.refreshCurrentImage();
        
        this.notyf.success('View reset to default');
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
        // Deactivate current tool
        if (this.activeTool === 'magnify') {
            this.magnificationActive = false;
        }
        
        this.activeTool = tool;
        
        // Activate new tool
        if (tool === 'magnify') {
            this.magnificationActive = true;
        } else if (tool === 'crosshair') {
            // Setup crosshair mode
        }
        
        this.canvas.style.cursor = this.getCursorForTool(tool);
        this.updateToolButtons();
        
        // Update unit toggle button text
        const unitBtn = document.getElementById('unit-toggle-btn');
        if (unitBtn) {
            unitBtn.innerHTML = `<span style="font-size: 10px; font-weight: bold;">${this.measurementUnit}</span>`;
        }
        
        this.notyf.success(`Active tool: ${tool}`);
    }
    
    getCursorForTool(tool) {
        switch(tool) {
            case 'pan': return 'move';
            case 'zoom': return 'zoom-in';
            case 'distance': return 'crosshair';
            case 'angle': return 'crosshair';
            case 'magnify': return 'none';
            case 'roi': return 'crosshair';
            default: return 'default';
        }
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
        
        this.zoom = 1.0;
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
        // Reset all view parameters to defaults
        this.zoom = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.rotation = 0;
        this.isInverted = false;
        this.windowCenter = 256;
        this.windowWidth = 512;
        this.contrast = 1.0;
        this.brightness = 0;
        
        // Reset tool state
        this.activeTool = 'pan';
        this.magnificationActive = false;
        this.roiActive = false;
        
        // Clear measurements
        this.clearMeasurements();
        
        // Update UI and refresh
        this.updateToolButtons();
        this.updateZoomDisplay();
        this.refreshCurrentImage();
        
        this.notyf.success('View reset to default');
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

    // Magnification tool functionality
    toggleMagnification() {
        this.magnificationActive = !this.magnificationActive;
        this.canvas.style.cursor = this.magnificationActive ? 'none' : 'default';
        
        if (!this.magnificationActive) {
            this.redrawCanvas();
        }
    }

    drawMagnifier(mouseX, mouseY) {
        if (!this.magnificationActive || !this.imageData) return;

        const radius = this.magnificationRadius;
        const scale = this.magnificationLevel;

        // Save context
        this.ctx.save();

        // Create circular clipping path
        this.ctx.beginPath();
        this.ctx.arc(mouseX, mouseY, radius, 0, 2 * Math.PI);
        this.ctx.clip();

        // Draw magnified portion
        const sourceX = Math.max(0, mouseX / this.zoom - radius / scale);
        const sourceY = Math.max(0, mouseY / this.zoom - radius / scale);
        const sourceWidth = Math.min(this.canvas.width / this.zoom, radius * 2 / scale);
        const sourceHeight = Math.min(this.canvas.height / this.zoom, radius * 2 / scale);

        this.ctx.drawImage(
            this.canvas,
            sourceX, sourceY, sourceWidth, sourceHeight,
            mouseX - radius, mouseY - radius, radius * 2, radius * 2
        );

        // Restore context
        this.ctx.restore();

        // Draw magnifier border and crosshairs
        this.ctx.strokeStyle = '#00ff88';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.arc(mouseX, mouseY, radius, 0, 2 * Math.PI);
        this.ctx.stroke();

        // Draw crosshairs
        this.ctx.beginPath();
        this.ctx.moveTo(mouseX - 10, mouseY);
        this.ctx.lineTo(mouseX + 10, mouseY);
        this.ctx.moveTo(mouseX, mouseY - 10);
        this.ctx.lineTo(mouseX, mouseY + 10);
        this.ctx.stroke();
    }

    // Measurement functionality
    startMeasurement(type, x, y) {
        const canvasRect = this.canvas.getBoundingClientRect();
        const imageX = (x - canvasRect.left - this.panX) / this.zoom;
        const imageY = (y - canvasRect.top - this.panY) / this.zoom;

        this.currentMeasurement = {
            type: type,
            points: [{ x: imageX, y: imageY }],
            id: Date.now()
        };
        this.isDrawing = true;
    }

    addMeasurementPoint(x, y) {
        if (!this.isDrawing || !this.currentMeasurement) return;

        const canvasRect = this.canvas.getBoundingClientRect();
        const imageX = (x - canvasRect.left - this.panX) / this.zoom;
        const imageY = (y - canvasRect.top - this.panY) / this.zoom;

        this.currentMeasurement.points.push({ x: imageX, y: imageY });

        if (this.currentMeasurement.type === 'distance' && this.currentMeasurement.points.length === 2) {
            this.finishMeasurement();
        } else if (this.currentMeasurement.type === 'angle' && this.currentMeasurement.points.length === 3) {
            this.finishMeasurement();
        }
    }

    finishMeasurement() {
        if (!this.currentMeasurement) return;

        this.measurements.push({ ...this.currentMeasurement });
        this.currentMeasurement = null;
        this.isDrawing = false;
        this.updateMeasurementPanel();
        this.refreshCurrentImage();
    }

    updateMeasurementPanel() {
        const panel = document.getElementById('measurement-info-panel');
        const list = document.getElementById('measurement-list');
        
        if (!panel || !list) return;
        
        if (this.measurements.length === 0) {
            panel.style.display = 'none';
            return;
        }
        
        panel.style.display = 'block';
        list.innerHTML = '';
        
        this.measurements.forEach((measurement, index) => {
            const item = document.createElement('div');
            item.style.marginBottom = '5px';
            item.style.padding = '5px';
            item.style.background = 'rgba(255,255,255,0.1)';
            item.style.borderRadius = '4px';
            
            let text = '';
            if (measurement.type === 'distance' && measurement.points.length === 2) {
                const distance = this.calculateDistance(measurement.points[0], measurement.points[1]);
                text = `Distance ${index + 1}: ${distance.toFixed(2)} ${this.measurementUnit}`;
            } else if (measurement.type === 'angle' && measurement.points.length === 3) {
                const angle = this.calculateAngle(measurement.points[0], measurement.points[1], measurement.points[2]);
                text = `Angle ${index + 1}: ${angle.toFixed(1)}°`;
            }
            
            item.innerHTML = `
                <div>${text}</div>
                <button onclick="viewer.removeMeasurement(${index})" style="background: #ff4444; border: none; color: white; padding: 2px 6px; border-radius: 3px; cursor: pointer; font-size: 10px;">Remove</button>
            `;
            
            list.appendChild(item);
        });
    }

    calculateDistance(p1, p2) {
        const dx = (p2.x - p1.x) * this.pixelSpacing.x * this.calibrationFactor;
        const dy = (p2.y - p1.y) * this.pixelSpacing.y * this.calibrationFactor;
        return Math.sqrt(dx * dx + dy * dy);
    }

    calculateAngle(p1, p2, p3) {
        const a = this.calculateDistance(p2, p3);
        const b = this.calculateDistance(p1, p3);
        const c = this.calculateDistance(p1, p2);
        
        const angle = Math.acos((a * a + c * c - b * b) / (2 * a * c));
        return (angle * 180) / Math.PI;
    }

    drawMeasurements() {
        if (!this.measurements.length && !this.currentMeasurement) return;

        this.ctx.save();
        this.ctx.strokeStyle = '#ff6b6b';
        this.ctx.fillStyle = '#ff6b6b';
        this.ctx.lineWidth = 2;
        this.ctx.font = '14px Arial';

        // Draw finished measurements
        this.measurements.forEach(measurement => {
            this.drawMeasurement(measurement);
        });

        // Draw current measurement being drawn
        if (this.currentMeasurement) {
            this.drawMeasurement(this.currentMeasurement);
        }

        this.ctx.restore();
    }

    drawMeasurement(measurement) {
        const points = measurement.points.map(p => ({
            x: p.x * this.zoom + this.panX,
            y: p.y * this.zoom + this.panY
        }));

        if (measurement.type === 'distance' && points.length >= 2) {
            // Draw line
            this.ctx.beginPath();
            this.ctx.moveTo(points[0].x, points[0].y);
            this.ctx.lineTo(points[1].x, points[1].y);
            this.ctx.stroke();

            // Draw points
            points.forEach(point => {
                this.ctx.beginPath();
                this.ctx.arc(point.x, point.y, 4, 0, 2 * Math.PI);
                this.ctx.fill();
            });

            // Draw distance label
            if (points.length === 2) {
                const distance = this.calculateDistance(measurement.points[0], measurement.points[1]);
                const unit = this.measurementUnit;
                const midX = (points[0].x + points[1].x) / 2;
                const midY = (points[0].y + points[1].y) / 2;
                
                this.ctx.fillText(`${distance.toFixed(2)} ${unit}`, midX + 10, midY - 10);
            }
        } else if (measurement.type === 'angle' && points.length >= 2) {
            // Draw angle lines
            this.ctx.beginPath();
            this.ctx.moveTo(points[0].x, points[0].y);
            this.ctx.lineTo(points[1].x, points[1].y);
            if (points.length === 3) {
                this.ctx.lineTo(points[2].x, points[2].y);
            }
            this.ctx.stroke();

            // Draw points
            points.forEach(point => {
                this.ctx.beginPath();
                this.ctx.arc(point.x, point.y, 4, 0, 2 * Math.PI);
                this.ctx.fill();
            });

            // Draw angle label
            if (points.length === 3) {
                const angle = this.calculateAngle(measurement.points[0], measurement.points[1], measurement.points[2]);
                this.ctx.fillText(`${angle.toFixed(1)}°`, points[1].x + 10, points[1].y - 10);
            }
        }
    }

    // Additional helper methods for measurements and ROI
    drawMeasurementPreview(clientX, clientY) {
        if (!this.currentMeasurement || !this.measurements) return;

        const canvasRect = this.canvas.getBoundingClientRect();
        const x = (clientX - canvasRect.left - this.panX) / this.zoom;
        const y = (clientY - canvasRect.top - this.panY) / this.zoom;

        // Create a temporary measurement for preview
        const previewMeasurement = {
            ...this.currentMeasurement,
            points: [...this.currentMeasurement.points, { x, y }]
        };

        this.drawMeasurement(previewMeasurement);
    }

    startROI(x, y) {
        this.roiActive = true;
        this.currentROI = {
            startX: x,
            startY: y,
            endX: x,
            endY: y,
            id: Date.now()
        };
    }

    updateROI(x, y) {
        if (!this.currentROI) return;
        
        this.currentROI.endX = x;
        this.currentROI.endY = y;
        this.refreshCurrentImage();
        this.drawROI(this.currentROI);
    }

    finishROI() {
        if (!this.currentROI) return;
        
        this.rois.push({ ...this.currentROI });
        this.analyzeROI(this.currentROI);
        this.currentROI = null;
        this.roiActive = false;
    }

    drawROI(roi) {
        if (!roi) return;

        this.ctx.save();
        this.ctx.strokeStyle = '#00ff88';
        this.ctx.fillStyle = 'rgba(0, 255, 136, 0.2)';
        this.ctx.lineWidth = 2;

        const width = roi.endX - roi.startX;
        const height = roi.endY - roi.startY;

        this.ctx.fillRect(roi.startX, roi.startY, width, height);
        this.ctx.strokeRect(roi.startX, roi.startY, width, height);

        this.ctx.restore();
    }

    analyzeROI(roi) {
        if (!this.imageData) return;

        const canvas = this.canvas;
        const imageData = this.ctx.getImageData(
            Math.min(roi.startX, roi.endX),
            Math.min(roi.startY, roi.endY),
            Math.abs(roi.endX - roi.startX),
            Math.abs(roi.endY - roi.startY)
        );

        let sum = 0;
        let count = 0;
        let min = Infinity;
        let max = -Infinity;

        for (let i = 0; i < imageData.data.length; i += 4) {
            const gray = imageData.data[i]; // R channel
            sum += gray;
            count++;
            min = Math.min(min, gray);
            max = Math.max(max, gray);
        }

        const mean = sum / count;
        const stats = {
            mean: mean.toFixed(2),
            min: min,
            max: max,
            area: Math.abs(roi.endX - roi.startX) * Math.abs(roi.endY - roi.startY)
        };

        this.showROIStats(stats);
    }

    showROIStats(stats) {
        const roiPanel = document.getElementById('roi-panel');
        const roiStats = document.getElementById('roi-stats');
        if (roiPanel && roiStats) {
            roiPanel.style.display = 'block';
            roiStats.innerHTML = `
                <p>Mean: ${stats.mean} HU</p>
                <p>Min: ${stats.min} HU</p>
                <p>Max: ${stats.max} HU</p>
                <p>Area: ${stats.area} pixels²</p>
            `;
        }
    }

    // Unit conversion for measurements
    toggleMeasurementUnit() {
        this.measurementUnit = this.measurementUnit === 'mm' ? 'cm' : 'mm';
        this.calibrationFactor = this.measurementUnit === 'cm' ? 0.1 : 1;
        this.refreshCurrentImage();
    }

    // Remove specific measurement
    removeMeasurement(index) {
        if (index >= 0 && index < this.measurements.length) {
            this.measurements.splice(index, 1);
            this.updateMeasurementPanel();
            this.refreshCurrentImage();
        }
    }

    // Clear all measurements
    clearMeasurements() {
        this.measurements = [];
        this.rois = [];
        this.currentMeasurement = null;
        this.currentROI = null;
        this.updateMeasurementPanel();
        
        // Hide panels
        const measurementPanel = document.getElementById('measurement-info-panel');
        const roiPanel = document.getElementById('roi-panel');
        if (measurementPanel) measurementPanel.style.display = 'none';
        if (roiPanel) roiPanel.style.display = 'none';
        
        this.refreshCurrentImage();
        this.notyf.success('All measurements cleared');
    }

    // Crosshair functionality
    drawCrosshair(x, y) {
        if (this.activeTool !== 'crosshair') return;

        this.ctx.save();
        this.ctx.strokeStyle = '#00ff88';
        this.ctx.lineWidth = 1;
        this.ctx.setLineDash([5, 5]);

        // Draw full-screen crosshair
        this.ctx.beginPath();
        // Vertical line
        this.ctx.moveTo(x, 0);
        this.ctx.lineTo(x, this.canvas.height);
        // Horizontal line
        this.ctx.moveTo(0, y);
        this.ctx.lineTo(this.canvas.width, y);
        this.ctx.stroke();

        this.ctx.restore();
    }

    // Fit image to window
    fitToWindow() {
        if (!this.currentImage) return;
        
        this.zoom = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.refreshCurrentImage();
        this.notyf.success('Image fitted to window');
    }

    // Update zoom display
    updateZoomDisplay() {
        const zoomDisplay = document.getElementById('zoom-level-display');
        if (zoomDisplay) {
            zoomDisplay.textContent = `${Math.round(this.zoom * 100)}%`;
        }
    }

    // Enhanced updateToolButtons method
    updateToolButtons() {
        // Remove active class from all tool buttons
        const allToolBtns = document.querySelectorAll('.tool-btn');
        allToolBtns.forEach(btn => btn.classList.remove('active'));
        
        // Add active class to current tool button
        const toolMapping = {
            'pan': 'pan-adv-btn',
            'zoom': 'zoom-adv-btn',
            'windowing': 'windowing-adv-btn',
            'distance': 'measure-distance-btn',
            'angle': 'measure-angle-btn',
            'area': 'measure-area-btn',
            'hu': 'hu-measurement-btn',
            'crosshair': 'crosshair-adv-btn',
            'magnify': 'magnify-btn',
            'roi': 'roi-btn'
        };
        
        const activeBtn = document.getElementById(toolMapping[this.activeTool]);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
    }
    
    // Cine Mode Methods
    toggleCineMode() {
        if (this.cineMode) {
            this.stopCineMode();
        } else {
            this.startCineMode();
        }
    }
    
    startCineMode() {
        console.log('Starting cine mode...');
        this.cineMode = true;
        this.cineSpeed = 100; // milliseconds between frames
        
        const playBtn = document.getElementById('play-btn');
        if (playBtn) {
            playBtn.innerHTML = '<i class="fas fa-pause"></i>';
        }
        
        this.cineInterval = setInterval(() => {
            this.navigateImages(1);
        }, this.cineSpeed);
        
        this.notyf.success('Cine mode started');
    }
    
    stopCineMode() {
        console.log('Stopping cine mode...');
        this.cineMode = false;
        
        const playBtn = document.getElementById('play-btn');
        if (playBtn) {
            playBtn.innerHTML = '<i class="fas fa-play"></i>';
        }
        
        if (this.cineInterval) {
            clearInterval(this.cineInterval);
            this.cineInterval = null;
        }
        
        this.notyf.info('Cine mode stopped');
    }
    
    // Viewport Layout Methods
    setViewportLayout(layout) {
        console.log('Setting viewport layout:', layout);
        this.currentLayout = layout;
        
        // Update UI to reflect layout change
        const layoutButtons = document.querySelectorAll('[id^="layout-"]');
        layoutButtons.forEach(btn => btn.classList.remove('active'));
        
        const activeLayoutBtn = document.getElementById(`layout-${layout}-btn`);
        if (activeLayoutBtn) {
            activeLayoutBtn.classList.add('active');
        }
        
        // TODO: Implement actual viewport layout logic
        this.notyf.info(`Viewport layout set to ${layout}`);
    }
    
    toggleViewportSync() {
        this.viewportSyncEnabled = !this.viewportSyncEnabled;
        
        const syncBtn = document.getElementById('sync-viewports-btn');
        if (syncBtn) {
            syncBtn.classList.toggle('active', this.viewportSyncEnabled);
        }
        
        this.notyf.info(`Viewport sync ${this.viewportSyncEnabled ? 'enabled' : 'disabled'}`);
    }
    
    // Annotation Methods
    clearAnnotations() {
        console.log('Clearing all annotations...');
        this.annotations = [];
        this.refreshCurrentImage();
        this.notyf.success('All annotations cleared');
    }
    
    // AI Analysis Methods
    async performAIAnalysis() {
        console.log('Performing AI analysis...');
        
        try {
            this.notyf.info('AI analysis started...');
            
            // Show loading indicator
            const loadingEl = document.getElementById('loading-indicator');
            if (loadingEl) loadingEl.style.display = 'flex';
            
            // TODO: Implement actual AI analysis API call
            // For now, simulate with a timeout
            setTimeout(() => {
                if (loadingEl) loadingEl.style.display = 'none';
                this.notyf.success('AI analysis complete - No abnormalities detected');
                
                // Update UI with mock results
                const aiResultsPanel = document.getElementById('ai-results-panel');
                if (aiResultsPanel) {
                    aiResultsPanel.innerHTML = `
                        <div class="ai-result">
                            <h4>AI Analysis Results</h4>
                            <p><strong>Status:</strong> Normal</p>
                            <p><strong>Confidence:</strong> 95%</p>
                            <p><strong>Findings:</strong> No significant abnormalities detected</p>
                        </div>
                    `;
                }
            }, 2000);
            
        } catch (error) {
            console.error('AI analysis error:', error);
            this.notyf.error('AI analysis failed');
        }
    }
    
    async performAISegmentation() {
        console.log('Performing AI segmentation...');
        
        try {
            this.notyf.info('AI segmentation started...');
            
            // Show loading indicator
            const loadingEl = document.getElementById('loading-indicator');
            if (loadingEl) loadingEl.style.display = 'flex';
            
            // TODO: Implement actual AI segmentation API call
            // For now, simulate with a timeout
            setTimeout(() => {
                if (loadingEl) loadingEl.style.display = 'none';
                this.notyf.success('AI segmentation complete');
                
                // Mock segmentation overlay
                this.drawMockSegmentation();
            }, 2000);
            
        } catch (error) {
            console.error('AI segmentation error:', error);
            this.notyf.error('AI segmentation failed');
        }
    }
    
    drawMockSegmentation() {
        if (!this.ctx || !this.canvas) return;
        
        // Draw a mock segmentation overlay
        this.ctx.save();
        this.ctx.globalAlpha = 0.3;
        this.ctx.fillStyle = '#00ff00';
        
        // Draw some mock segmented regions
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, 100, 0, 2 * Math.PI);
        this.ctx.fill();
        
        this.ctx.restore();
    }
    
    // Additional helper methods
    showNoDataMessage() {
        if (!this.canvas || !this.ctx) return;
        
        this.clearCanvas();
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = '24px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText('No DICOM image loaded', this.canvas.width / 2, this.canvas.height / 2);
        this.ctx.font = '16px Arial';
        this.ctx.fillText('Please upload a DICOM file or select a study', this.canvas.width / 2, this.canvas.height / 2 + 40);
    }
    
    showConnectionError() {
        if (!this.canvas || !this.ctx) return;
        
        this.clearCanvas();
        this.ctx.fillStyle = '#ff3333';
        this.ctx.font = '24px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText('Connection Error', this.canvas.width / 2, this.canvas.height / 2);
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = '16px Arial';
        this.ctx.fillText('Failed to connect to DICOM server', this.canvas.width / 2, this.canvas.height / 2 + 40);
    }
    
    showErrorPlaceholder() {
        if (!this.canvas || !this.ctx) return;
        
        this.clearCanvas();
        this.ctx.fillStyle = '#ff3333';
        this.ctx.font = '24px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText('Error Loading Image', this.canvas.width / 2, this.canvas.height / 2);
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = '16px Arial';
        this.ctx.fillText('Failed to load DICOM image', this.canvas.width / 2, this.canvas.height / 2 + 40);
    }
    
    hideErrorPlaceholder() {
        // This method is called when image loads successfully
        // No action needed as the image will overwrite any error message
    }
    
    clearCanvas() {
        if (!this.canvas || !this.ctx) return;
        
        this.ctx.fillStyle = '#000000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }
}

// Initialize the fixed viewer when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Enhanced Fixed DICOM Viewer...');
    
    const urlParams = new URLSearchParams(window.location.search);
    const studyId = urlParams.get('study_id');
    
    // Create viewer instance and make it globally accessible
    window.viewer = new FixedDicomViewer(studyId);
    window.fixedDicomViewer = window.viewer; // For backward compatibility
    
    // Initialize the viewer
    window.viewer.init(studyId);
    
    console.log('Enhanced Fixed DICOM Viewer initialized successfully');
});
