// static/js/dicom_viewer.js

class DicomViewer {
    constructor() {
        this.canvas = document.getElementById('dicom-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // State variables
        this.currentStudy = null;
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
        this.currentEllipse = null;
        this.draggedAnnotation = null;

        // Measurement unit (mm or cm)
        this.measurementUnit = 'mm';
        this.isDragging = false;
        this.dragStart = null;
        
        // Window presets
        this.windowPresets = {
            'lung': { ww: 1500, wl: -600 },
            'bone': { ww: 2000, wl: 300 },
            'soft': { ww: 400, wl: 40 },
            'brain': { ww: 100, wl: 50 }
        };
        
        this.init();
    }
    
    init() {
        this.setupCanvas();
        this.setupEventListeners();
        this.loadBackendStudies();
        this.loadAIAnalysisTypes();
        this.load3DReconstructionTypes();
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

        // Measurement unit selector
        document.getElementById('measurement-unit').addEventListener('change', (e) => {
            this.measurementUnit = e.target.value;
            this.updateMeasurementsList();
        });

        // Annotation controls
        document.getElementById('annotation-size').addEventListener('input', (e) => {
            const size = e.target.value;
            document.getElementById('modal-size-value').textContent = size + 'px';
        });

        // AI Analysis
        document.getElementById('run-ai-analysis').addEventListener('click', () => {
            this.runAIAnalysis();
        });

        // 3D Reconstruction
        document.getElementById('run-3d-reconstruction').addEventListener('click', () => {
            this.run3DReconstruction();
        });

        // Modal close buttons
        document.querySelectorAll('.modal-close, .ai-chat-close, .3d-panel-close').forEach(btn => {
            btn.addEventListener('click', () => {
                this.closeAllModals();
            });
        });

        // Annotation modal
        document.getElementById('save-annotation').addEventListener('click', () => {
            this.saveAnnotationFromModal();
        });

        // Mouse events
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        
        // Upload modal
        this.setupUploadModal();
    }
    
    setupUploadModal() {
        const uploadBtn = document.getElementById('load-dicom-btn');
        const modal = document.getElementById('upload-modal');
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        
        uploadBtn.addEventListener('click', () => {
            this.showUploadModal();
        });
        
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            this.uploadFiles(files);
        });
        
        fileInput.addEventListener('change', (e) => {
            this.uploadFiles(e.target.files);
        });
    }
    
    showUploadModal() {
        document.getElementById('upload-modal').style.display = 'block';
    }
    
    async uploadFiles(files) {
        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }
        
        const progressBar = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const progressDiv = document.getElementById('upload-progress');
        
        progressDiv.style.display = 'block';
        progressBar.style.width = '0%';
        progressText.textContent = 'Uploading...';
        
        try {
            const response = await fetch('/viewer/api/upload/', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                progressBar.style.width = '100%';
                progressText.textContent = 'Upload complete!';
                
                setTimeout(() => {
                    document.getElementById('upload-modal').style.display = 'none';
                    progressDiv.style.display = 'none';
                    this.loadBackendStudies();
                }, 1000);
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            progressText.textContent = 'Upload failed: ' + error.message;
            console.error('Upload error:', error);
        }
    }
    
    async loadBackendStudies() {
        try {
            const response = await fetch('/viewer/api/studies/');
            const studies = await response.json();
            
            const select = document.getElementById('backend-studies');
            select.innerHTML = '<option value="">Select DICOM from System</option>';
            
            studies.forEach(study => {
                const option = document.createElement('option');
                option.value = study.id;
                option.textContent = `${study.patient_name} - ${study.study_date} (${study.modality})`;
                select.appendChild(option);
            });
            
            select.addEventListener('change', (e) => {
                if (e.target.value) {
                    this.loadStudy(e.target.value);
                }
            });
        } catch (error) {
            console.error('Error loading studies:', error);
        }
    }
    
    async loadStudy(studyId) {
        try {
            const response = await fetch(`/viewer/api/studies/${studyId}/images/`);
            const data = await response.json();
            
            this.currentStudy = studyId;
            this.currentImages = data.images;
            this.currentImageIndex = 0;
            
            // Update patient info
            this.updatePatientInfo();
            
            // Update slice slider
            const sliceSlider = document.getElementById('slice-slider');
            sliceSlider.max = this.currentImages.length - 1;
            sliceSlider.value = 0;
            
            // Load first image
            if (this.currentImages.length > 0) {
                this.loadCurrentImage();
            }
        } catch (error) {
            console.error('Error loading study:', error);
        }
    }
    
    async loadCurrentImage() {
        if (!this.currentImages.length) return;
        
        const imageId = this.currentImages[this.currentImageIndex].id;
        
        try {
            const response = await fetch(`/viewer/api/images/${imageId}/?ww=${this.windowWidth}&wl=${this.windowLevel}&inverted=${this.inverted}`);
            const data = await response.json();
            
            this.currentImage = data;
            this.updateDisplay();
            this.updateSliders();
            this.loadMeasurements();
            this.loadAnnotations();
        } catch (error) {
            console.error('Error loading image:', error);
        }
    }
    
    updatePatientInfo() {
        if (this.currentImages.length > 0) {
            const image = this.currentImages[this.currentImageIndex];
            document.getElementById('patient-info').textContent = 
                `Patient: ${image.patient_name || 'Unknown'} | Study Date: ${image.study_date || 'Unknown'} | Modality: ${image.modality || 'Unknown'}`;
        }
    }
    
    updateSliders() {
        if (!this.currentImage) return;
        
        const metadata = this.currentImage.metadata;
        
        // Update window/level sliders
        if (metadata.window_width) {
            document.getElementById('ww-slider').value = metadata.window_width;
            document.getElementById('ww-value').textContent = metadata.window_width;
            this.windowWidth = metadata.window_width;
        }
        
        if (metadata.window_center) {
            document.getElementById('wl-slider').value = metadata.window_center;
            document.getElementById('wl-value').textContent = metadata.window_center;
            this.windowLevel = metadata.window_center;
        }
        
        // Update info panel
        document.getElementById('info-dimensions').textContent = `${metadata.rows} x ${metadata.columns}`;
        document.getElementById('info-pixel-spacing').textContent = 
            metadata.pixel_spacing_x && metadata.pixel_spacing_y ? 
            `${metadata.pixel_spacing_x} x ${metadata.pixel_spacing_y} mm` : 'Not available';
        document.getElementById('info-series').textContent = this.currentImages[this.currentImageIndex].series_number || 'Unknown';
        document.getElementById('info-institution').textContent = 'Medical Center';
    }
    
    updateDisplay() {
        if (!this.currentImage) return;
        
        const img = new Image();
        img.onload = () => {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            
            // Apply zoom and pan
            this.ctx.save();
            this.ctx.translate(this.panX, this.panY);
            this.ctx.scale(this.zoomFactor, this.zoomFactor);
            
            // Draw image
            this.ctx.drawImage(img, 0, 0);
            
            // Draw overlays
            this.drawMeasurements();
            this.drawAnnotations();
            
            if (this.crosshair) {
                this.drawCrosshair();
            }
            
            this.ctx.restore();
            
            this.updateOverlayLabels();
        };
        img.src = this.currentImage.image_data;
    }
    
    drawMeasurements() {
        this.measurements.forEach(measurement => {
            this.ctx.strokeStyle = '#00FF00';
            this.ctx.lineWidth = 2;
            this.ctx.setLineDash([5, 5]);
            
            if (measurement.type === 'line') {
                const coords = measurement.coordinates;
                this.ctx.beginPath();
                this.ctx.moveTo(coords.x1, coords.y1);
                this.ctx.lineTo(coords.x2, coords.y2);
                this.ctx.stroke();
                
                // Draw measurement text
                this.ctx.fillStyle = '#00FF00';
                this.ctx.font = '12px Arial';
                const midX = (coords.x1 + coords.x2) / 2;
                const midY = (coords.y1 + coords.y2) / 2;
                this.ctx.fillText(`${measurement.value} ${measurement.unit}`, midX, midY - 5);
            } else if (measurement.type === 'ellipse') {
                const coords = measurement.coordinates;
                this.ctx.beginPath();
                this.ctx.ellipse(coords.center_x, coords.center_y, coords.radius_x, coords.radius_y, 0, 0, 2 * Math.PI);
                this.ctx.stroke();
                
                // Draw HU value
                this.ctx.fillStyle = '#00FF00';
                this.ctx.font = '12px Arial';
                this.ctx.fillText(`${measurement.hounsfield_units.toFixed(1)} HU`, coords.center_x, coords.center_y);
            }
            
            this.ctx.setLineDash([]);
        });
    }
    
    drawAnnotations() {
        this.annotations.forEach(annotation => {
            this.ctx.fillStyle = annotation.color;
            this.ctx.font = `${annotation.font_size}px Arial`;
            this.ctx.fillText(annotation.text, annotation.x, annotation.y);
        });
    }
    
    drawCrosshair() {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        
        this.ctx.strokeStyle = '#FF0000';
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
    
    updateOverlayLabels() {
        document.getElementById('wl-info').innerHTML = 
            `WW: ${this.windowWidth}<br>WL: ${this.windowLevel}<br>Slice: ${this.currentImageIndex + 1}/${this.currentImages.length}`;
        document.getElementById('zoom-info').textContent = `Zoom: ${Math.round(this.zoomFactor * 100)}%`;
    }
    
    handleToolClick(tool) {
        // Remove active class from all buttons
        document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
        
        // Add active class to clicked button
        event.target.closest('.tool-btn').classList.add('active');
        
        this.activeTool = tool;
        
        switch (tool) {
            case 'crosshair':
                this.crosshair = !this.crosshair;
                document.getElementById('crosshair').style.display = this.crosshair ? 'block' : 'none';
                break;
            case 'invert':
                this.inverted = !this.inverted;
                this.loadCurrentImage();
                break;
            case 'reset':
                this.resetView();
                break;
            case 'ai':
                this.showAIChat();
                break;
            case '3d':
                this.show3DPanel();
                break;
        }
    }
    
    applyPreset(preset) {
        const presetData = this.windowPresets[preset];
        if (presetData) {
            this.windowWidth = presetData.ww;
            this.windowLevel = presetData.wl;
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
        this.inverted = false;
        this.crosshair = false;
        
        document.getElementById('zoom-slider').value = 100;
        document.getElementById('zoom-value').textContent = '100%';
        document.getElementById('crosshair').style.display = 'none';
        
        this.updateDisplay();
    }
    
    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.activeTool === 'measure') {
            this.startMeasurement(x, y);
        } else if (this.activeTool === 'ellipse') {
            this.startEllipse(x, y);
        } else if (this.activeTool === 'annotate') {
            this.startAnnotation(x, y);
        } else if (this.activeTool === 'pan') {
            this.isDragging = true;
            this.dragStart = { x, y };
        } else if (this.activeTool === 'windowing') {
            this.isDragging = true;
            this.dragStart = { x, y };
        }
        
        // Check for annotation dragging
        this.checkAnnotationDrag(x, y);
    }
    
    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.activeTool === 'measure' && this.currentMeasurement) {
            this.updateMeasurement(x, y);
        } else if (this.activeTool === 'ellipse' && this.currentEllipse) {
            this.updateEllipse(x, y);
        } else if (this.activeTool === 'pan' && this.isDragging) {
            const deltaX = x - this.dragStart.x;
            const deltaY = y - this.dragStart.y;
            this.panX += deltaX;
            this.panY += deltaY;
            this.dragStart = { x, y };
            this.updateDisplay();
        } else if (this.activeTool === 'windowing' && this.isDragging) {
            const deltaY = y - this.dragStart.y;
            this.windowLevel += deltaY * 2;
            this.windowLevel = Math.max(-1000, Math.min(1000, this.windowLevel));
            this.dragStart = { x, y };
            document.getElementById('wl-slider').value = this.windowLevel;
            document.getElementById('wl-value').textContent = this.windowLevel;
            this.loadCurrentImage();
        }
        
        // Handle annotation dragging
        if (this.draggedAnnotation) {
            this.draggedAnnotation.x = x;
            this.draggedAnnotation.y = y;
            this.updateDisplay();
        }
    }
    
    onMouseUp(e) {
        if (this.activeTool === 'measure' && this.currentMeasurement) {
            this.finishMeasurement();
        } else if (this.activeTool === 'ellipse' && this.currentEllipse) {
            this.finishEllipse();
        } else if (this.activeTool === 'annotate' && this.currentAnnotation) {
            this.finishAnnotation();
        }
        
        this.isDragging = false;
        this.draggedAnnotation = null;
    }
    
    onWheel(e) {
        e.preventDefault();
        
        if (this.activeTool === 'zoom') {
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomFactor *= delta;
            this.zoomFactor = Math.max(0.25, Math.min(5.0, this.zoomFactor));
            
            document.getElementById('zoom-slider').value = this.zoomFactor * 100;
            document.getElementById('zoom-value').textContent = Math.round(this.zoomFactor * 100) + '%';
            this.updateDisplay();
        }
    }
    
    imageToCanvasCoords(imageX, imageY) {
        return {
            x: (imageX - this.panX) / this.zoomFactor,
            y: (imageY - this.panY) / this.zoomFactor
        };
    }
    
    canvasToImageCoords(canvasX, canvasY) {
        return {
            x: canvasX * this.zoomFactor + this.panX,
            y: canvasY * this.zoomFactor + this.panY
        };
    }
    
    startMeasurement(x, y) {
        this.currentMeasurement = {
            type: 'line',
            coordinates: { x1: x, y1: y, x2: x, y2: y },
            value: 0,
            unit: this.measurementUnit
        };
    }
    
    updateMeasurement(x, y) {
        if (this.currentMeasurement) {
            this.currentMeasurement.coordinates.x2 = x;
            this.currentMeasurement.coordinates.y2 = y;
            
            // Calculate distance
            const dx = x - this.currentMeasurement.coordinates.x1;
            const dy = y - this.currentMeasurement.coordinates.y1;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            // Convert to selected unit
            let value = distance;
            if (this.measurementUnit === 'cm') {
                value = distance / 10; // Assuming 1 pixel = 1mm
            }
            
            this.currentMeasurement.value = value;
            this.updateDisplay();
        }
    }
    
    async finishMeasurement() {
        if (this.currentMeasurement && this.currentImage) {
            const imageId = this.currentImages[this.currentImageIndex].id;
            
            try {
                const response = await fetch('/viewer/api/measurements/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken(),
                    },
                    body: JSON.stringify({
                        image_id: imageId,
                        type: this.currentMeasurement.type,
                        coordinates: this.currentMeasurement.coordinates,
                        value: this.currentMeasurement.value,
                        unit: this.currentMeasurement.unit
                    })
                });
                
                const result = await response.json();
                this.measurements.push(result);
                this.updateMeasurementsList();
            } catch (error) {
                console.error('Error saving measurement:', error);
            }
        }
        
        this.currentMeasurement = null;
    }
    
    startEllipse(x, y) {
        this.currentEllipse = {
            center_x: x,
            center_y: y,
            radius_x: 0,
            radius_y: 0
        };
    }
    
    updateEllipse(x, y) {
        if (this.currentEllipse) {
            this.currentEllipse.radius_x = Math.abs(x - this.currentEllipse.center_x);
            this.currentEllipse.radius_y = Math.abs(y - this.currentEllipse.center_y);
            this.updateDisplay();
        }
    }
    
    async finishEllipse() {
        if (this.currentEllipse && this.currentImage) {
            const imageId = this.currentImages[this.currentImageIndex].id;
            
            try {
                const response = await fetch('/viewer/api/measure-hu/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken(),
                    },
                    body: JSON.stringify({
                        image_id: imageId,
                        center_x: this.currentEllipse.center_x,
                        center_y: this.currentEllipse.center_y,
                        radius_x: this.currentEllipse.radius_x,
                        radius_y: this.currentEllipse.radius_y
                    })
                });
                
                const result = await response.json();
                this.measurements.push({
                    type: 'ellipse',
                    coordinates: this.currentEllipse,
                    value: result.mean_hu,
                    unit: 'HU',
                    hounsfield_units: result.mean_hu
                });
                this.updateMeasurementsList();
            } catch (error) {
                console.error('Error measuring HU:', error);
            }
        }
        
        this.currentEllipse = null;
    }
    
    startAnnotation(x, y) {
        this.currentAnnotation = { x, y };
        this.showAnnotationModal(x, y);
    }
    
    finishAnnotation() {
        this.currentAnnotation = null;
    }
    
    showAnnotationModal(x, y) {
        const modal = document.getElementById('annotation-modal');
        modal.style.display = 'block';
        
        // Store coordinates for later use
        modal.dataset.x = x;
        modal.dataset.y = y;
    }
    
    async saveAnnotationFromModal() {
        const modal = document.getElementById('annotation-modal');
        const text = document.getElementById('modal-annotation-text').value;
        const color = document.getElementById('modal-annotation-color').value;
        const size = document.getElementById('modal-annotation-size').value;
        const x = parseInt(modal.dataset.x);
        const y = parseInt(modal.dataset.y);
        
        if (!text.trim()) {
            alert('Please enter annotation text');
            return;
        }
        
        if (this.currentImage) {
            const imageId = this.currentImages[this.currentImageIndex].id;
            
            try {
                const response = await fetch('/viewer/api/annotations/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken(),
                    },
                    body: JSON.stringify({
                        image_id: imageId,
                        x: x,
                        y: y,
                        text: text,
                        color: color,
                        font_size: parseInt(size)
                    })
                });
                
                const result = await response.json();
                this.annotations.push(result);
                this.updateAnnotationsList();
                this.updateDisplay();
            } catch (error) {
                console.error('Error saving annotation:', error);
            }
        }
        
        this.closeAnnotationModal();
    }
    
    closeAnnotationModal() {
        document.getElementById('annotation-modal').style.display = 'none';
        document.getElementById('modal-annotation-text').value = '';
    }
    
    checkAnnotationDrag(x, y) {
        // Check if clicked on an annotation for dragging
        for (let i = this.annotations.length - 1; i >= 0; i--) {
            const annotation = this.annotations[i];
            const distance = Math.sqrt((x - annotation.x) ** 2 + (y - annotation.y) ** 2);
            
            if (distance < 20) { // Click tolerance
                this.draggedAnnotation = annotation;
                break;
            }
        }
    }
    
    async loadMeasurements() {
        if (!this.currentImage) return;
        
        const imageId = this.currentImages[this.currentImageIndex].id;
        
        try {
            const response = await fetch(`/viewer/api/images/${imageId}/measurements/`);
            const data = await response.json();
            this.measurements = data.measurements || [];
            this.updateMeasurementsList();
        } catch (error) {
            console.error('Error loading measurements:', error);
        }
    }
    
    async loadAnnotations() {
        if (!this.currentImage) return;
        
        const imageId = this.currentImages[this.currentImageIndex].id;
        
        try {
            const response = await fetch(`/viewer/api/images/${imageId}/annotations/`);
            const data = await response.json();
            this.annotations = data.annotations || [];
            this.updateAnnotationsList();
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
            item.innerHTML = `
                <span>${measurement.type}: ${measurement.value.toFixed(2)} ${measurement.unit}</span>
                ${measurement.hounsfield_units ? `<span>(${measurement.hounsfield_units.toFixed(1)} HU)</span>` : ''}
                <button onclick="viewer.removeMeasurement(${index})" class="remove-btn">&times;</button>
            `;
            list.appendChild(item);
        });
    }
    
    updateAnnotationsList() {
        const list = document.getElementById('annotations-list');
        list.innerHTML = '';
        
        this.annotations.forEach((annotation, index) => {
            const item = document.createElement('div');
            item.className = 'annotation-item';
            item.innerHTML = `
                <span style="color: ${annotation.color};">${annotation.text}</span>
                <button onclick="viewer.removeAnnotation(${index})" class="remove-btn">&times;</button>
            `;
            list.appendChild(item);
        });
    }
    
    removeMeasurement(index) {
        this.measurements.splice(index, 1);
        this.updateMeasurementsList();
        this.updateDisplay();
    }
    
    removeAnnotation(index) {
        this.annotations.splice(index, 1);
        this.updateAnnotationsList();
        this.updateDisplay();
    }
    
    async clearMeasurements() {
        if (!this.currentImage) return;
        
        const imageId = this.currentImages[this.currentImageIndex].id;
        
        try {
            await fetch(`/viewer/api/images/${imageId}/measurements/clear/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                }
            });
            
            this.measurements = [];
            this.updateMeasurementsList();
            this.updateDisplay();
        } catch (error) {
            console.error('Error clearing measurements:', error);
        }
    }
    
    // AI Analysis Methods
    async loadAIAnalysisTypes() {
        try {
            const response = await fetch('/viewer/api/ai-analysis-types/');
            const data = await response.json();
            
            const select = document.getElementById('ai-analysis-type');
            select.innerHTML = '<option value="">Select AI Analysis Type</option>';
            
            data.ai_types.forEach(type => {
                const option = document.createElement('option');
                option.value = type.id;
                option.textContent = type.name;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading AI analysis types:', error);
        }
    }
    
    showAIChat() {
        document.getElementById('ai-chat-window').style.display = 'block';
    }
    
    async runAIAnalysis() {
        const analysisType = document.getElementById('ai-analysis-type').value;
        if (!analysisType) {
            alert('Please select an AI analysis type');
            return;
        }
        
        const chatContent = document.getElementById('ai-chat-content');
        chatContent.innerHTML += `
            <div class="ai-message">
                <strong>User:</strong> Running ${analysisType} analysis...
            </div>
        `;
        
        // Simulate AI analysis (replace with actual AI integration)
        setTimeout(() => {
            const results = this.simulateAIAnalysis(analysisType);
            chatContent.innerHTML += `
                <div class="ai-message">
                    <strong>AI Assistant:</strong> Analysis complete!<br>
                    <strong>Results:</strong><br>
                    ${results}
                </div>
            `;
            chatContent.scrollTop = chatContent.scrollHeight;
        }, 2000);
    }
    
    simulateAIAnalysis(type) {
        const results = {
            'lung_nodule': 'No suspicious nodules detected. Normal lung parenchyma.',
            'brain_lesion': 'No significant brain lesions identified. Normal brain tissue.',
            'bone_fracture': 'No fractures detected. Normal bone structure.',
            'tumor_segmentation': 'No suspicious masses identified. Normal tissue appearance.'
        };
        
        return results[type] || 'Analysis completed with no significant findings.';
    }
    
    // 3D Reconstruction Methods
    async load3DReconstructionTypes() {
        try {
            const response = await fetch('/viewer/api/3d-reconstruction-types/');
            const data = await response.json();
            
            const select = document.getElementById('3d-reconstruction-type');
            select.innerHTML = '<option value="">Select Reconstruction Type</option>';
            
            data.reconstruction_types.forEach(type => {
                const option = document.createElement('option');
                option.value = type.id;
                option.textContent = type.name;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading 3D reconstruction types:', error);
        }
    }
    
    show3DPanel() {
        document.getElementById('3d-panel').style.display = 'block';
    }
    
    async run3DReconstruction() {
        const reconstructionType = document.getElementById('3d-reconstruction-type').value;
        if (!reconstructionType) {
            alert('Please select a reconstruction type');
            return;
        }
        
        const statusDiv = document.getElementById('3d-status');
        statusDiv.innerHTML = '<p>Generating 3D reconstruction...</p>';
        
        // Simulate 3D reconstruction (replace with actual 3D processing)
        setTimeout(() => {
            statusDiv.innerHTML = `
                <p>3D reconstruction complete!</p>
                <p>Type: ${reconstructionType}</p>
                <p>Status: Ready for export</p>
            `;
        }, 3000);
    }
    
    closeAllModals() {
        document.getElementById('upload-modal').style.display = 'none';
        document.getElementById('annotation-modal').style.display = 'none';
        document.getElementById('ai-chat-window').style.display = 'none';
        document.getElementById('3d-panel').style.display = 'none';
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
    }
    
    redraw() {
        this.updateDisplay();
    }
}

// Initialize viewer when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.viewer = new DicomViewer();
});

// Global functions for template access
function closeAnnotationModal() {
    if (window.viewer) {
        window.viewer.closeAnnotationModal();
    }
}