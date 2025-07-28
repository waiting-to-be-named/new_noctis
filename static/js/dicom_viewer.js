// static/js/dicom_viewer.js

class DicomViewer {
    constructor() {
        this.canvas = document.getElementById('dicom-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // State variables
        this.currentStudy = null;
        this.currentSeries = null;
        this.currentImages = [];
        this.currentImageIndex = 0;
        this.currentImage = null;
        
        // Display parameters
        this.windowWidth = 400;
        this.windowLevel = 40;
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
        
        // Window presets
        this.windowPresets = {
            'lung': { ww: 1500, wl: -600 },
            'bone': { ww: 2000, wl: 300 },
            'soft': { ww: 400, wl: 40 },
            'brain': { ww: 100, wl: 50 }
        };
        
        // Notifications
        this.notificationCheckInterval = null;
        
        this.init();
    }
    
    init() {
        this.setupCanvas();
        this.setupEventListeners();
        this.loadBackendStudies();
        this.setupNotifications();
        this.setupMeasurementUnitSelector();
        this.setup3DControls();
        this.setupAIPanel();
    }
    
    setupCanvas() {
        // Set canvas size
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    resizeCanvas() {
        const viewport = document.querySelector('.viewport');
        this.canvas.width = viewport.clientWidth;
        this.canvas.height = viewport.clientHeight;
        this.redraw();
    }
    
    setupEventListeners() {
        // Tool buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tool = btn.dataset.tool;
                this.handleToolClick(tool);
            });
        });
        
        // Sliders
        document.getElementById('ww-slider').addEventListener('input', (e) => {
            this.windowWidth = parseInt(e.target.value);
            document.getElementById('ww-value').textContent = this.windowWidth;
            this.updateDisplay();
        });
        
        document.getElementById('wl-slider').addEventListener('input', (e) => {
            this.windowLevel = parseInt(e.target.value);
            document.getElementById('wl-value').textContent = this.windowLevel;
            this.updateDisplay();
        });
        
        document.getElementById('slice-slider').addEventListener('input', (e) => {
            this.currentImageIndex = parseInt(e.target.value);
            document.getElementById('slice-value').textContent = this.currentImageIndex + 1;
            this.loadCurrentImage();
        });
        
        document.getElementById('zoom-slider').addEventListener('input', (e) => {
            this.zoomFactor = e.target.value / 100;
            document.getElementById('zoom-value').textContent = e.target.value + '%';
            this.updateDisplay();
        });
        
        // Preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const preset = btn.dataset.preset;
                this.applyPreset(preset);
            });
        });
        
        // Load DICOM button
        document.getElementById('load-dicom-btn').addEventListener('click', () => {
            this.showUploadModal();
        });
        
        // Load from system (worklist)
        document.getElementById('backend-studies').addEventListener('change', (e) => {
            if (e.target.value === 'worklist') {
                window.location.href = '/worklist/';
            } else if (e.target.value) {
                this.loadStudy(e.target.value);
            }
        });
        
        // Clear measurements
        document.getElementById('clear-measurements').addEventListener('click', () => {
            this.clearMeasurements();
        });
        
        // Canvas mouse events
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        this.canvas.addEventListener('dblclick', (e) => this.onDoubleClick(e));
        
        // Upload modal events
        this.setupUploadModal();
    }
    
    setupUploadModal() {
        const modal = document.getElementById('upload-modal');
        const closeBtn = modal.querySelector('.modal-close');
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
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
    
    showUploadModal() {
        document.getElementById('upload-modal').style.display = 'flex';
    }
    
    async uploadFiles(files) {
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });
        
        const progressDiv = document.getElementById('upload-progress');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        progressDiv.style.display = 'block';
        progressFill.style.width = '0%';
        
        try {
            const response = await fetch('/api/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            progressFill.style.width = '100%';
            
            if (response.ok) {
                const result = await response.json();
                progressText.textContent = 'Upload complete!';
                
                setTimeout(() => {
                    document.getElementById('upload-modal').style.display = 'none';
                    progressDiv.style.display = 'none';
                    
                    if (result.study_id) {
                        this.loadStudy(result.study_id);
                    }
                }, 1000);
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            progressText.textContent = 'Upload failed: ' + error.message;
            console.error('Upload error:', error);
        }
    }
    
    async loadBackendStudies() {
        try {
            const response = await fetch('/api/studies/');
            const studies = await response.json();
            
            const select = document.getElementById('backend-studies');
            select.innerHTML = `
                <option value="">Select DICOM from System</option>
                <option value="worklist">📋 Open Worklist</option>
                <option disabled>──────────────</option>
            `;
            
            studies.forEach(study => {
                const option = document.createElement('option');
                option.value = study.id;
                option.textContent = `${study.patient_name} - ${study.study_date} (${study.modality})`;
                select.appendChild(option);
            });
            
            // Update: Event listener is already set up in setupEventListeners()
            
        } catch (error) {
            console.error('Error loading studies:', error);
        }
    }
    
    async loadStudy(studyId) {
        try {
            const response = await fetch(`/api/studies/${studyId}/images/`);
            const data = await response.json();
            
            this.currentStudy = data.study;
            this.currentSeries = data.series || null;
            this.currentImages = data.images;
            this.currentImageIndex = 0;
            
            // Update UI
            this.updatePatientInfo();
            this.updateSliders();
            this.loadCurrentImage();
            
        } catch (error) {
            console.error('Error loading study:', error);
        }
    }
    
    async loadCurrentImage() {
        if (!this.currentImages.length) return;
        
        const imageData = this.currentImages[this.currentImageIndex];
        
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
                    this.updateDisplay();
                    this.loadMeasurements();
                    this.loadAnnotations();
                };
                img.src = data.image_data;
            }
            
        } catch (error) {
            console.error('Error loading image:', error);
        }
    }
    
    updatePatientInfo() {
        if (!this.currentStudy) return;
        
        const patientInfo = document.getElementById('patient-info');
        patientInfo.textContent = `Patient: ${this.currentStudy.patient_name} | Study Date: ${this.currentStudy.study_date} | Modality: ${this.currentStudy.modality}`;
        
        // Update image info
        const currentImageData = this.currentImages[this.currentImageIndex];
        if (currentImageData) {
            document.getElementById('info-dimensions').textContent = `${currentImageData.columns}x${currentImageData.rows}`;
            document.getElementById('info-pixel-spacing').textContent = 
                `${currentImageData.pixel_spacing_x || 'Unknown'}\\${currentImageData.pixel_spacing_y || 'Unknown'}`;
            document.getElementById('info-series').textContent = currentImageData.series_description || 'Unknown';
            document.getElementById('info-institution').textContent = this.currentStudy.institution_name || 'Unknown';
        }
    }
    
    updateSliders() {
        if (!this.currentImages.length) return;
        
        const sliceSlider = document.getElementById('slice-slider');
        sliceSlider.max = this.currentImages.length - 1;
        sliceSlider.value = this.currentImageIndex;
        
        // Update initial window/level from first image
        const firstImage = this.currentImages[0];
        if (firstImage.window_width && firstImage.window_center) {
            this.windowWidth = firstImage.window_width;
            this.windowLevel = firstImage.window_center;
            
            document.getElementById('ww-slider').value = this.windowWidth;
            document.getElementById('wl-slider').value = this.windowLevel;
            document.getElementById('ww-value').textContent = this.windowWidth;
            document.getElementById('wl-value').textContent = this.windowLevel;
        }
    }
    
    updateDisplay() {
        if (!this.currentImage) return;
        
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
        if (this.showAIHighlights) {
            this.drawAIHighlights();
        }
        
        // Update overlay labels
        this.updateOverlayLabels();
    }
    
    drawMeasurements() {
        if (!this.currentImage) return;
        
        this.ctx.strokeStyle = 'red';
        this.ctx.lineWidth = 2;
        this.ctx.fillStyle = 'red';
        this.ctx.font = '12px Arial';
        
        this.measurements.forEach(measurement => {
            const coords = measurement.coordinates;
            if (measurement.type === 'ellipse' && measurement.coordinates) {
                const c = Array.isArray(measurement.coordinates) ? measurement.coordinates[0] : measurement.coordinates;
                const start = this.imageToCanvasCoords(c.x0, c.y0);
                const end = this.imageToCanvasCoords(c.x1, c.y1);
                const width = end.x - start.x;
                const height = end.y - start.y;
                const centerX = start.x + width / 2;
                const centerY = start.y + height / 2;

                this.ctx.save();
                this.ctx.strokeStyle = 'lime';
                this.ctx.setLineDash([4, 4]);
                this.ctx.beginPath();
                this.ctx.ellipse(centerX, centerY, Math.abs(width) / 2, Math.abs(height) / 2, 0, 0, Math.PI * 2);
                this.ctx.stroke();
                this.ctx.restore();

                // Display HU value
                const text = `${measurement.value.toFixed(1)} HU`;
                const textMetrics = this.ctx.measureText(text);
                this.ctx.fillStyle = 'rgba(0,0,0,0.7)';
                this.ctx.fillRect(centerX - textMetrics.width/2 - 4, centerY - 8, textMetrics.width + 8, 16);
                this.ctx.fillStyle = 'lime';
                this.ctx.fillText(text, centerX - textMetrics.width/2, centerY + 4);
            } else if (measurement.type === 'volume' && coords && coords.length >= 3) {
                // Draw volume contour
                this.ctx.strokeStyle = 'blue';
                this.ctx.fillStyle = 'rgba(0, 0, 255, 0.2)';
                this.ctx.lineWidth = 2;
                
                this.ctx.beginPath();
                const firstPoint = this.imageToCanvasCoords(coords[0].x, coords[0].y);
                this.ctx.moveTo(firstPoint.x, firstPoint.y);
                
                for (let i = 1; i < coords.length; i++) {
                    const point = this.imageToCanvasCoords(coords[i].x, coords[i].y);
                    this.ctx.lineTo(point.x, point.y);
                }
                this.ctx.closePath();
                this.ctx.fill();
                this.ctx.stroke();
                
                // Calculate centroid for text placement
                let centroidX = 0, centroidY = 0;
                coords.forEach(point => {
                    const canvasPoint = this.imageToCanvasCoords(point.x, point.y);
                    centroidX += canvasPoint.x;
                    centroidY += canvasPoint.y;
                });
                centroidX /= coords.length;
                centroidY /= coords.length;
                
                // Draw volume text
                const text = `${measurement.value.toFixed(2)} ${measurement.unit}`;
                const textMetrics = this.ctx.measureText(text);
                this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                this.ctx.fillRect(centroidX - textMetrics.width/2 - 4, centroidY - 8, textMetrics.width + 8, 16);
                this.ctx.fillStyle = 'blue';
                this.ctx.fillText(text, centroidX - textMetrics.width/2, centroidY + 4);
            } else if (coords && coords.length >= 2) {
                // existing line measurement drawing
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
        if (this.currentEllipse) {
            const start = this.imageToCanvasCoords(this.currentEllipse.start.x, this.currentEllipse.start.y);
            const end = this.imageToCanvasCoords(this.currentEllipse.end.x, this.currentEllipse.end.y);
            const width = end.x - start.x;
            const height = end.y - start.y;
            const centerX = start.x + width / 2;
            const centerY = start.y + height / 2;
            this.ctx.setLineDash([5,5]);
            this.ctx.strokeStyle = 'yellow';
            this.ctx.beginPath();
            this.ctx.ellipse(centerX, centerY, Math.abs(width)/2, Math.abs(height)/2, 0, 0, Math.PI*2);
            this.ctx.stroke();
            this.ctx.setLineDash([]);
        }
        
        // Draw current volume contour being created
        if (this.volumeContour && this.volumeContour.length > 0) {
            this.ctx.strokeStyle = 'orange';
            this.ctx.fillStyle = 'orange';
            this.ctx.lineWidth = 2;
            
            // Draw lines between points
            if (this.volumeContour.length > 1) {
                this.ctx.setLineDash([3, 3]);
                this.ctx.beginPath();
                const firstPoint = this.imageToCanvasCoords(this.volumeContour[0].x, this.volumeContour[0].y);
                this.ctx.moveTo(firstPoint.x, firstPoint.y);
                
                for (let i = 1; i < this.volumeContour.length; i++) {
                    const point = this.imageToCanvasCoords(this.volumeContour[i].x, this.volumeContour[i].y);
                    this.ctx.lineTo(point.x, point.y);
                }
                this.ctx.stroke();
                this.ctx.setLineDash([]);
            }
            
            // Draw points
            this.volumeContour.forEach((point, index) => {
                const canvasPoint = this.imageToCanvasCoords(point.x, point.y);
                this.ctx.beginPath();
                this.ctx.arc(canvasPoint.x, canvasPoint.y, 4, 0, Math.PI * 2);
                this.ctx.fill();
                
                // Number the points
                this.ctx.fillStyle = 'white';
                this.ctx.font = '10px Arial';
                this.ctx.fillText(index + 1, canvasPoint.x - 3, canvasPoint.y + 3);
                this.ctx.fillStyle = 'orange';
            });
            
            // Show instruction text
            if (this.volumeContour.length >= 3) {
                this.ctx.fillStyle = 'orange';
                this.ctx.font = '14px Arial';
                this.ctx.fillText('Click near first point to close contour', 10, 30);
            }
        }
    }
    
    drawAnnotations() {
        if (!this.currentImage) return;
        
        this.annotations.forEach((annotation, index) => {
            const pos = this.imageToCanvasCoords(annotation.x, annotation.y);
            
            // Set font size and color from annotation properties
            const fontSize = annotation.font_size || 14;
            const color = annotation.color || '#FFFF00';
            
            this.ctx.font = `${fontSize * this.zoomFactor}px Arial`;
            
            // Measure text for background
            const textMetrics = this.ctx.measureText(annotation.text);
            const padding = 4;
            const textHeight = fontSize * this.zoomFactor;
            
            // Check if this annotation is selected
            const isSelected = this.selectedAnnotation === index;
            
            // Draw background
            this.ctx.fillStyle = isSelected ? 'rgba(100, 100, 100, 0.9)' : 'rgba(0, 0, 0, 0.8)';
            this.ctx.fillRect(
                pos.x - padding, 
                pos.y - textHeight - padding, 
                textMetrics.width + padding * 2, 
                textHeight + padding * 2
            );
            
            // Draw border if selected
            if (isSelected) {
                this.ctx.strokeStyle = 'white';
                this.ctx.strokeRect(
                    pos.x - padding, 
                    pos.y - textHeight - padding, 
                    textMetrics.width + padding * 2, 
                    textHeight + padding * 2
                );
            }
            
            // Draw text
            this.ctx.fillStyle = color;
            this.ctx.fillText(annotation.text, pos.x, pos.y - padding);
        });
    }
    
    drawAIHighlights() {
        if (!this.aiAnalysisResults || !this.showAIHighlights) return;
        
        this.ctx.save();
        this.ctx.strokeStyle = '#FF0080';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([5, 5]);
        
        this.aiAnalysisResults.highlighted_regions.forEach(region => {
            const topLeft = this.imageToCanvasCoords(
                region.x - region.width / 2, 
                region.y - region.height / 2
            );
            const bottomRight = this.imageToCanvasCoords(
                region.x + region.width / 2, 
                region.y + region.height / 2
            );
            
            const width = bottomRight.x - topLeft.x;
            const height = bottomRight.y - topLeft.y;
            
            // Draw highlight rectangle
            this.ctx.strokeRect(topLeft.x, topLeft.y, width, height);
            
            // Draw label
            this.ctx.fillStyle = 'rgba(255, 0, 128, 0.8)';
            const label = `${region.label} (${(region.confidence * 100).toFixed(0)}%)`;
            const labelMetrics = this.ctx.measureText(label);
            
            this.ctx.fillRect(
                topLeft.x, 
                topLeft.y - 20, 
                labelMetrics.width + 8, 
                20
            );
            
            this.ctx.fillStyle = 'white';
            this.ctx.font = '12px Arial';
            this.ctx.fillText(label, topLeft.x + 4, topLeft.y - 6);
        });
        
        this.ctx.restore();
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
        
        wlInfo.innerHTML = `WW: ${Math.round(this.windowWidth)}<br>WL: ${Math.round(this.windowLevel)}<br>Slice: ${this.currentImageIndex + 1}/${this.currentImages.length}`;
        zoomInfo.textContent = `Zoom: ${Math.round(this.zoomFactor * 100)}%`;
    }
    
    // Event Handlers
    handleToolClick(tool) {
        // Reset current measurement/annotation states
        this.currentMeasurement = null;
        this.currentEllipse = null;
        this.selectedAnnotation = null;
        this.isEditingAnnotation = false;
        this.volumeTool = false;
        this.volumeContour = [];
        this.currentContour = null;
        
        // Remove active class from all buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Add active class to clicked button
        const clickedBtn = document.querySelector(`[data-tool="${tool}"]`);
        if (clickedBtn) {
            clickedBtn.classList.add('active');
        }
        
        switch(tool) {
            case 'windowing':
            case 'zoom':
            case 'pan':
            case 'measure':
            case 'ellipse':
            case 'annotate':
                this.activeTool = tool;
                break;
            case 'volume':
                this.activeTool = tool;
                this.volumeTool = true;
                alert('Volume measurement: Click to create a closed contour around the region to measure volume.');
                break;
            case 'crosshair':
                this.crosshair = !this.crosshair;
                this.updateDisplay();
                break;
            case 'invert':
                this.inverted = !this.inverted;
                this.updateDisplay();
                break;
            case 'reset':
                this.resetView();
                break;
            case 'ai':
                this.performAIAnalysis();
                break;
            case '3d':
                this.toggle3DOptions();
                break;
        }
        
        // Change cursor based on tool
        switch(tool) {
            case 'windowing':
                this.canvas.style.cursor = 'default';
                break;
            case 'pan':
                this.canvas.style.cursor = 'move';
                break;
            case 'zoom':
                this.canvas.style.cursor = 'zoom-in';
                break;
            case 'measure':
            case 'ellipse':
            case 'volume':
                this.canvas.style.cursor = 'crosshair';
                break;
            case 'annotate':
                this.canvas.style.cursor = 'text';
                break;
        }
    }
    
    applyPreset(preset) {
        const presetValues = this.windowPresets[preset];
        if (presetValues) {
            this.windowWidth = presetValues.ww;
            this.windowLevel = presetValues.wl;
            
            document.getElementById('ww-slider').value = this.windowWidth;
            document.getElementById('wl-slider').value = this.windowLevel;
            document.getElementById('ww-value').textContent = this.windowWidth;
            document.getElementById('wl-value').textContent = this.windowLevel;
            
            this.loadCurrentImage();
        }
    }
    
    resetView() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        
        document.getElementById('zoom-slider').value = 100;
        document.getElementById('zoom-value').textContent = '100%';
        
        this.updateDisplay();
    }
    
    // Mouse Events
    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.isDragging = true;
        this.dragStart = { x, y };
        
        if (this.activeTool === 'measure') {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.currentMeasurement = {
                start: imageCoords,
                end: imageCoords
            };
        } else if (this.activeTool === 'ellipse') {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.currentEllipse = {
                start: imageCoords,
                end: imageCoords
            };
        } else if (this.activeTool === 'volume') {
            const imageCoords = this.canvasToImageCoords(x, y);
            
            // Add point to volume contour
            this.volumeContour.push(imageCoords);
            
            // Check if we should close the contour (double-click or close to start)
            if (this.volumeContour.length > 2) {
                const firstPoint = this.volumeContour[0];
                const distance = Math.sqrt(
                    Math.pow(imageCoords.x - firstPoint.x, 2) + 
                    Math.pow(imageCoords.y - firstPoint.y, 2)
                );
                
                if (distance < 10) { // Close contour if clicking near start
                    this.calculateVolume();
                    return;
                }
            }
            
            this.updateDisplay();
        } else if (this.activeTool === 'annotate') {
            // Check if clicking on existing annotation
            const clickedAnnotation = this.getAnnotationAt(x, y);
            if (clickedAnnotation !== null) {
                this.selectedAnnotation = clickedAnnotation;
                this.isEditingAnnotation = true;
            } else {
                // Create new annotation
                const text = prompt('Enter annotation text:');
                if (text) {
                    const imageCoords = this.canvasToImageCoords(x, y);
                    const fontSize = parseInt(prompt('Font size (default: 14):', '14')) || 14;
                    const color = prompt('Color (hex, default: #FFFF00):', '#FFFF00') || '#FFFF00';
                    this.addAnnotation(imageCoords.x, imageCoords.y, text, fontSize, color);
                }
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
        
        if (this.activeTool === 'annotate' && this.isEditingAnnotation && this.selectedAnnotation !== null) {
            // Drag annotation
            const annotation = this.annotations[this.selectedAnnotation];
            if (annotation) {
                const imageCoords = this.canvasToImageCoords(x, y);
                annotation.x = imageCoords.x;
                annotation.y = imageCoords.y;
                this.updateDisplay();
            }
        } else if (this.activeTool === 'pan') {
            this.panX += dx;
            this.panY += dy;
            this.dragStart = { x, y };
            this.updateDisplay();
        } else if (this.activeTool === 'zoom') {
            const zoomDelta = 1 + dy * 0.01;
            this.zoomFactor = Math.max(0.1, Math.min(5.0, this.zoomFactor * zoomDelta));
            
            const zoomPercent = Math.round(this.zoomFactor * 100);
            document.getElementById('zoom-slider').value = zoomPercent;
            document.getElementById('zoom-value').textContent = zoomPercent + '%';
            
            this.dragStart = { x, y };
            this.updateDisplay();
        } else if (this.activeTool === 'windowing') {
            this.windowWidth = Math.max(1, this.windowWidth + dx * 2);
            this.windowLevel = Math.max(-1000, Math.min(1000, this.windowLevel + dy * 2));
            
            document.getElementById('ww-slider').value = Math.round(this.windowWidth);
            document.getElementById('wl-slider').value = Math.round(this.windowLevel);
            document.getElementById('ww-value').textContent = Math.round(this.windowWidth);
            document.getElementById('wl-value').textContent = Math.round(this.windowLevel);
            
            this.dragStart = { x, y };
            this.loadCurrentImage();
        } else if (this.activeTool === 'measure' && this.currentMeasurement) {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.currentMeasurement.end = imageCoords;
            this.updateDisplay();
        } else if (this.activeTool === 'ellipse' && this.currentEllipse) {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.currentEllipse.end = imageCoords;
            this.updateDisplay();
        }
    }
    
    onMouseUp(e) {
        if (this.activeTool === 'measure' && this.currentMeasurement) {
            const start = this.currentMeasurement.start;
            const end = this.currentMeasurement.end;
            
            // Calculate distance
            const dx = end.x - start.x;
            const dy = end.y - start.y;
            const pixelDistance = Math.sqrt(dx * dx + dy * dy);
            
            // Convert to selected unit
            let value = pixelDistance;
            let unit = this.measurementUnit;
            
            if (this.currentImage && (unit === 'mm' || unit === 'cm')) {
                const pixelSpacingX = this.currentImage.pixel_spacing_x || 1.0;
                const pixelSpacingY = this.currentImage.pixel_spacing_y || 1.0;
                
                const realDx = dx * pixelSpacingX;
                const realDy = dy * pixelSpacingY;
                const distanceMm = Math.sqrt(realDx * realDx + realDy * realDy);
                
                value = unit === 'cm' ? distanceMm / 10.0 : distanceMm;
            }
            
            // Save measurement
            this.saveMeasurement({
                type: 'line',
                coordinates: [
                    { x: start.x, y: start.y },
                    { x: end.x, y: end.y }
                ],
                value: value,
                unit: unit
            });
            
            this.currentMeasurement = null;
        } else if (this.activeTool === 'ellipse' && this.currentEllipse) {
            const start = this.currentEllipse.start;
            const end = this.currentEllipse.end;
            
            // Save ellipse measurement for HU calculation
            this.saveEllipseMeasurement({
                x0: start.x,
                y0: start.y,
                x1: end.x,
                y1: end.y
            });
            
            this.currentEllipse = null;
        }
        
        this.isDragging = false;
        this.dragStart = null;
        this.isEditingAnnotation = false;
        this.selectedAnnotation = null;
    }
    
    onWheel(e) {
        e.preventDefault();
        
        if (e.ctrlKey) {
            // Zoom
            const zoomDelta = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomFactor = Math.max(0.1, Math.min(5.0, this.zoomFactor * zoomDelta));
            
            const zoomPercent = Math.round(this.zoomFactor * 100);
            document.getElementById('zoom-slider').value = zoomPercent;
            document.getElementById('zoom-value').textContent = zoomPercent + '%';
            
            this.updateDisplay();
        } else {
            // Slice navigation
            const direction = e.deltaY > 0 ? 1 : -1;
            const newIndex = this.currentImageIndex + direction;
            
            if (newIndex >= 0 && newIndex < this.currentImages.length) {
                this.currentImageIndex = newIndex;
                document.getElementById('slice-slider').value = newIndex;
                document.getElementById('slice-value').textContent = newIndex + 1;
                this.loadCurrentImage();
            }
        }
    }
    
    onDoubleClick(e) {
        if (this.activeTool === 'annotate') {
            const text = prompt('Enter annotation text:');
            if (text) {
                const imageCoords = this.canvasToImageCoords(e.clientX, e.clientY);
                this.addAnnotation(imageCoords.x, imageCoords.y, text);
            }
        }
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
            value = distance * avgSpacing; // in mm
            unit = 'mm';
        }

        // Apply unit preference
        if (this.measurementUnit === 'cm') {
            value = value / 10.0;
            unit = 'cm';
        } else if (this.measurementUnit === 'mm') {
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
            }
        } catch (error) {
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
            }
        } catch (error) {
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
        list.innerHTML = '';
        
        this.measurements.forEach((measurement, index) => {
            const item = document.createElement('div');
            item.className = 'measurement-item';
            let displayText;
            let typeText;
            
            switch(measurement.type) {
                case 'ellipse':
                    typeText = 'HU Analysis';
                    displayText = `${measurement.value.toFixed(1)} HU`;
                    if (measurement.hounsfield_min !== undefined) {
                        displayText += ` (${measurement.hounsfield_min.toFixed(1)} - ${measurement.hounsfield_max.toFixed(1)})`;
                    }
                    if (measurement.notes) {
                        displayText += ` - ${measurement.notes}`;
                    }
                    break;
                case 'volume':
                    typeText = 'Volume';
                    displayText = `${measurement.value.toFixed(2)} ${measurement.unit}`;
                    break;
                case 'line':
                    typeText = 'Distance';
                    displayText = `${measurement.value.toFixed(1)} ${measurement.unit}`;
                    break;
                case 'area':
                    typeText = 'Area';
                    displayText = `${measurement.value.toFixed(2)} ${measurement.unit}`;
                    break;
                case 'angle':
                    typeText = 'Angle';
                    displayText = `${measurement.value.toFixed(1)}°`;
                    break;
                default:
                    typeText = 'Measurement';
                    displayText = `${measurement.value.toFixed(1)} ${measurement.unit}`;
            }
            
            item.innerHTML = `<strong>${typeText} ${index + 1}:</strong> ${displayText}`;
            
            // Add click handler to highlight measurement
            item.addEventListener('click', () => {
                // Remove highlighting from all measurements
                document.querySelectorAll('.measurement-item').forEach(m => m.classList.remove('highlighted'));
                // Highlight this measurement
                item.classList.add('highlighted');
                // TODO: Could add highlighting on canvas as well
            });
            
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
            }
        } catch (error) {
            console.error('Error clearing measurements:', error);
        }
    }
    
    async     addEllipseHU(ellipseData) {
        if (!this.currentImage) return;
        const payload = {
            image_id: this.currentImage.id,
            x0: ellipseData.start.x,
            y0: ellipseData.start.y,
            x1: ellipseData.end.x,
            y1: ellipseData.end.y
        };
        try {
            const response = await fetch('/api/measurements/hu/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(payload)
            });
            if (response.ok) {
                const result = await response.json();
                const measurement = {
                    image_id: this.currentImage.id,
                    type: 'ellipse',
                    coordinates: [payload], // store bounding box
                    value: result.mean_hu,
                    unit: 'HU',
                    notes: `Min: ${result.min_hu.toFixed(1)} Max: ${result.max_hu.toFixed(1)}`
                };
                this.measurements.push(measurement);
                this.updateMeasurementsList();
                this.updateDisplay();
            }
        } catch (error) {
            console.error('Error measuring HU:', error);
        }
    }
    
    calculateVolume() {
        if (this.volumeContour.length < 3) {
            alert('Need at least 3 points to calculate volume');
            return;
        }
        
        // Calculate area using shoelace formula
        let area = 0;
        const n = this.volumeContour.length;
        
        for (let i = 0; i < n; i++) {
            const j = (i + 1) % n;
            area += this.volumeContour[i].x * this.volumeContour[j].y;
            area -= this.volumeContour[j].x * this.volumeContour[i].y;
        }
        area = Math.abs(area) / 2;
        
        // Convert to real-world units
        let volume = area;
        let unit = 'px²';
        
        if (this.currentImage) {
            const pixelSpacingX = this.currentImage.pixel_spacing_x || 1.0;
            const pixelSpacingY = this.currentImage.pixel_spacing_y || 1.0;
            const sliceThickness = this.currentImage.slice_thickness || 1.0;
            
            if (pixelSpacingX && pixelSpacingY) {
                const realArea = area * pixelSpacingX * pixelSpacingY; // mm²
                volume = realArea * sliceThickness; // mm³
                
                unit = this.measurementUnit === 'cm' ? 'cm³' : 'mm³';
                if (unit === 'cm³') {
                    volume = volume / 1000; // Convert mm³ to cm³
                }
            }
        }
        
        // Save volume measurement
        this.saveMeasurement({
            type: 'volume',
            coordinates: this.volumeContour.slice(), // Copy array
            value: volume,
            unit: unit,
            area: area
        });
        
        // Reset volume contour
        this.volumeContour = [];
        this.updateDisplay();
        
        // Show result
        alert(`Volume calculated: ${volume.toFixed(2)} ${unit}`);
    }
    
    // Utility functions
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    getCSRFToken() {
        return this.getCookie('csrftoken');
    }
    
    redraw() {
        if (this.currentImage) {
            this.updateDisplay();
        }
    }

    performAIAnalysis() {
        if (!this.currentImage) {
            alert('Please load an image first');
            return;
        }
        
        const aiPanel = document.getElementById('ai-panel');
        aiPanel.style.display = 'block';
        
        const resultsDiv = document.getElementById('ai-results');
        resultsDiv.innerHTML = '<div class="loading">Performing AI analysis...</div>';
        
        fetch(`/api/images/${this.currentImage.id}/ai-analysis/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            this.aiAnalysisResults = data;
            this.showAIHighlights = true;
            this.displayAIResults(data);
            this.redraw();
        })
        .catch(error => {
            resultsDiv.innerHTML = '<div class="error">Error performing AI analysis</div>';
            console.error('AI analysis error:', error);
        });
    }
    
    displayAIResults(results) {
        const resultsDiv = document.getElementById('ai-results');
        resultsDiv.innerHTML = `
            <div class="ai-summary">
                <h4>Analysis Summary</h4>
                <p>${results.summary}</p>
                <p>Confidence: ${(results.confidence_score * 100).toFixed(1)}%</p>
            </div>
            <div class="ai-findings">
                <h4>Findings</h4>
                <ul>
                    ${results.findings.map(f => `
                        <li>
                            <strong>${f.type}</strong> at (${f.location.x}, ${f.location.y})
                            <br>Size: ${f.size}px, Confidence: ${(f.confidence * 100).toFixed(1)}%
                        </li>
                    `).join('')}
                </ul>
            </div>
            <div class="ai-actions">
                <button onclick="viewer.copyAIResults()">Copy Results</button>
                <button onclick="viewer.toggleAIHighlights()">Toggle Highlights</button>
            </div>
        `;
    }
    
    copyAIResults() {
        if (!this.aiAnalysisResults) return;
        
        const text = `AI Analysis Results\n\n${this.aiAnalysisResults.summary}\n\nFindings:\n${
            this.aiAnalysisResults.findings.map(f => 
                `- ${f.type} at (${f.location.x}, ${f.location.y}), Size: ${f.size}px, Confidence: ${(f.confidence * 100).toFixed(1)}%`
            ).join('\n')
        }`;
        
        navigator.clipboard.writeText(text).then(() => {
            alert('Results copied to clipboard');
        });
    }
    
    toggleAIHighlights() {
        this.showAIHighlights = !this.showAIHighlights;
        this.redraw();
    }
    
    toggle3DOptions() {
        const options3D = document.getElementById('3d-options');
        this.is3DEnabled = !this.is3DEnabled;
        options3D.style.display = this.is3DEnabled ? 'block' : 'none';
    }
    
    apply3DReconstruction() {
        if (!this.currentSeries) {
            alert('Please load a series first');
            return;
        }
        
        const modal = this.create3DModal();
        document.body.appendChild(modal);
        
        fetch(`/api/series/${this.currentSeries.id}/3d-reconstruction/?type=${this.reconstructionType}`)
            .then(response => response.json())
            .then(data => {
                this.display3DReconstruction(data, modal);
            })
            .catch(error => {
                modal.querySelector('.modal-content').innerHTML = '<div class="error">Error loading 3D reconstruction</div>';
                console.error('3D reconstruction error:', error);
            });
    }
    
    create3DModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-3d';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>3D Reconstruction - ${this.reconstructionType.replace('_', ' ').toUpperCase()}</h2>
                    <button class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="loading">Loading 3D reconstruction...</div>
                </div>
            </div>
        `;
        
        modal.querySelector('.close-btn').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        return modal;
    }
    
    display3DReconstruction(data, modal) {
        const body = modal.querySelector('.modal-body');
        
        switch(data.type) {
            case 'mpr':
                body.innerHTML = `
                    <div class="mpr-viewer">
                        <h3>Multi-Planar Reconstruction</h3>
                        <div class="mpr-planes">
                            <div class="plane">
                                <h4>Axial</h4>
                                <div class="plane-info">Slices: ${data.planes.axial.slice_count}</div>
                            </div>
                            <div class="plane">
                                <h4>Coronal</h4>
                                <div class="plane-info">Slices: ${data.planes.coronal.slice_count}</div>
                            </div>
                            <div class="plane">
                                <h4>Sagittal</h4>
                                <div class="plane-info">Slices: ${data.planes.sagittal.slice_count}</div>
                            </div>
                        </div>
                    </div>
                `;
                break;
            case '3d_bone':
                body.innerHTML = `
                    <div class="bone-3d">
                        <h3>3D Bone Reconstruction</h3>
                        <div class="mesh-info">
                            <p>Vertices: ${data.mesh_data.vertices}</p>
                            <p>Faces: ${data.mesh_data.faces}</p>
                            <p>Threshold: ${data.mesh_data.threshold} HU</p>
                        </div>
                        <div class="render-placeholder">
                            [3D Bone Rendering Placeholder]
                        </div>
                    </div>
                `;
                break;
            case 'angio':
                body.innerHTML = `
                    <div class="angio-3d">
                        <h3>Angiography Reconstruction</h3>
                        <div class="vessel-info">
                            <p>Main vessels: ${data.vessel_tree.main_vessels}</p>
                            <p>Branches: ${data.vessel_tree.branches}</p>
                        </div>
                        <div class="render-placeholder">
                            [Angio 3D Rendering Placeholder]
                        </div>
                    </div>
                `;
                break;
            case 'virtual_surgery':
                body.innerHTML = `
                    <div class="virtual-surgery">
                        <h3>Virtual Surgery Planning</h3>
                        <div class="tools-info">
                            <p>Available tools: ${data.tools.join(', ')}</p>
                            <p>Anatomical structures: ${data.anatomical_structures.join(', ')}</p>
                        </div>
                        <div class="surgery-placeholder">
                            [Virtual Surgery Interface Placeholder]
                        </div>
                    </div>
                `;
                break;
        }
    }

    getAnnotationAt(canvasX, canvasY) {
        for (let i = this.annotations.length - 1; i >= 0; i--) {
            const annotation = this.annotations[i];
            const pos = this.imageToCanvasCoords(annotation.x, annotation.y);
            
            const fontSize = (annotation.font_size || 14) * this.zoomFactor;
            const textMetrics = this.ctx.measureText(annotation.text);
            const padding = 4;
            
            // Check if click is within annotation bounds
            if (canvasX >= pos.x - padding && 
                canvasX <= pos.x + textMetrics.width + padding &&
                canvasY >= pos.y - fontSize - padding &&
                canvasY <= pos.y + padding) {
                return i;
            }
        }
        return null;
    }
    
    saveMeasurement(measurement) {
        if (!this.currentImage) return;
        
        const data = {
            image_id: this.currentImage.id,
            measurement_type: measurement.type,
            coordinates: measurement.coordinates || measurement,
            value: measurement.value,
            unit: measurement.unit || this.measurementUnit
        };
        
        fetch('/api/measurements/save/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.measurements.push({
                    id: data.measurement_id,
                    type: measurement.type,
                    coordinates: measurement.coordinates,
                    value: data.value || measurement.value,
                    unit: data.unit || measurement.unit
                });
                this.updateDisplay();
            }
        })
        .catch(error => console.error('Error saving measurement:', error));
    }
    
    saveEllipseMeasurement(coords) {
        if (!this.currentImage) return;
        
        const data = {
            image_id: this.currentImage.id,
            measurement_type: 'ellipse',
            coordinates: coords,
            value: 0, // Will be calculated server-side
            unit: 'HU'
        };
        
        fetch('/api/measurements/save/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.measurements.push({
                    id: data.measurement_id,
                    type: 'ellipse',
                    coordinates: coords,
                    value: data.hounsfield_mean || 0,
                    unit: 'HU',
                    hounsfield_min: data.hounsfield_min,
                    hounsfield_max: data.hounsfield_max,
                    hounsfield_std: data.hounsfield_std
                });
                this.updateDisplay();
                
                // Show HU values in alert
                if (data.hounsfield_mean !== undefined) {
                    alert(`Hounsfield Unit Measurements:\n\nMean: ${data.hounsfield_mean.toFixed(1)} HU\nMin: ${data.hounsfield_min.toFixed(1)} HU\nMax: ${data.hounsfield_max.toFixed(1)} HU\nStd Dev: ${data.hounsfield_std.toFixed(1)} HU`);
                }
            }
        })
        .catch(error => console.error('Error saving ellipse measurement:', error));
    }
    
    addAnnotation(x, y, text, fontSize = 14, color = '#FFFF00') {
        if (!this.currentImage) return;
        
        const data = {
            image_id: this.currentImage.id,
            x: x,
            y: y,
            text: text,
            font_size: fontSize,
            color: color
        };
        
        fetch('/api/annotations/save/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.annotations.push({
                    id: data.annotation_id,
                    x: x,
                    y: y,
                    text: text,
                    font_size: fontSize,
                    color: color
                });
                this.updateDisplay();
            }
        })
        .catch(error => console.error('Error saving annotation:', error));
    }
}

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new DicomViewer();
});