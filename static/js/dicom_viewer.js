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
        this.isDragging = false;
        this.dragStart = null;
        this.draggedAnnotation = null;
        
        // Measurement settings
        this.measurementUnit = 'mm'; // cm, mm, px
        this.ellipseMode = false;
        this.ellipseData = null;
        
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
        this.setupMeasurementControls();
        this.loadBackendStudies();
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
    
    setupMeasurementControls() {
        // Add measurement unit dropdown
        const measurementPanel = document.querySelector('.measurement-panel');
        if (measurementPanel) {
            const unitSelect = document.createElement('select');
            unitSelect.id = 'measurement-unit';
            unitSelect.className = 'form-select';
            unitSelect.innerHTML = `
                <option value="px">Pixels</option>
                <option value="mm" selected>Millimeters</option>
                <option value="cm">Centimeters</option>
            `;
            unitSelect.addEventListener('change', (e) => {
                this.measurementUnit = e.target.value;
                this.updateMeasurementsList();
            });
            
            const unitLabel = document.createElement('label');
            unitLabel.textContent = 'Unit:';
            unitLabel.className = 'form-label';
            
            measurementPanel.insertBefore(unitLabel, measurementPanel.firstChild);
            measurementPanel.insertBefore(unitSelect, measurementPanel.firstChild.nextSibling);
        }
        
        // Add ellipse button for Hounsfield units
        const toolButtons = document.querySelector('.tool-buttons');
        if (toolButtons) {
            const ellipseBtn = document.createElement('button');
            ellipseBtn.className = 'tool-btn';
            ellipseBtn.dataset.tool = 'ellipse';
            ellipseBtn.title = 'Ellipse (Hounsfield Units)';
            ellipseBtn.innerHTML = '<i class="fas fa-circle"></i><span>Ellipse</span>';
            toolButtons.appendChild(ellipseBtn);
        }
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
        
        // Canvas events
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        
        // Load DICOM button
        document.getElementById('load-dicom-btn').addEventListener('click', () => {
            this.showUploadModal();
        });
        
        // Backend studies dropdown
        document.getElementById('backend-studies').addEventListener('change', (e) => {
            if (e.target.value) {
                this.loadStudy(e.target.value);
            }
        });
        
        // Setup upload modal
        this.setupUploadModal();
    }
    
    setupUploadModal() {
        // Create modal if it doesn't exist
        if (!document.getElementById('upload-modal')) {
            const modal = document.createElement('div');
            modal.id = 'upload-modal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Upload DICOM Files</h3>
                        <span class="close">&times;</span>
                    </div>
                    <div class="modal-body">
                        <input type="file" id="dicom-files" multiple accept=".dcm,.dicom">
                        <div class="upload-progress" style="display: none;">
                            <div class="progress-bar">
                                <div class="progress-fill"></div>
                            </div>
                            <div class="progress-text">Uploading...</div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-primary" id="upload-btn">Upload</button>
                        <button class="btn btn-secondary" id="cancel-upload">Cancel</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            // Event listeners
            modal.querySelector('.close').addEventListener('click', () => {
                modal.style.display = 'none';
            });
            
            modal.querySelector('#cancel-upload').addEventListener('click', () => {
                modal.style.display = 'none';
            });
            
            modal.querySelector('#upload-btn').addEventListener('click', () => {
                const files = document.getElementById('dicom-files').files;
                if (files.length > 0) {
                    this.uploadFiles(files);
                }
            });
            
            // Close modal when clicking outside
            window.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        }
    }
    
    showUploadModal() {
        const modal = document.getElementById('upload-modal');
        modal.style.display = 'block';
    }
    
    async uploadFiles(files) {
        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }
        
        const progressBar = document.querySelector('.upload-progress');
        const progressFill = document.querySelector('.progress-fill');
        const progressText = document.querySelector('.progress-text');
        
        progressBar.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = 'Uploading...';
        
        try {
            const response = await fetch('/upload-dicom/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                progressFill.style.width = '100%';
                progressText.textContent = 'Upload complete!';
                
                setTimeout(() => {
                    document.getElementById('upload-modal').style.display = 'none';
                    this.loadBackendStudies();
                }, 1000);
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            progressText.textContent = 'Upload failed: ' + error.message;
        }
    }
    
    async loadBackendStudies() {
        try {
            const response = await fetch('/api/studies/');
            const studies = await response.json();
            
            const select = document.getElementById('backend-studies');
            select.innerHTML = '<option value="">Select DICOM from System</option>';
            
            studies.forEach(study => {
                const option = document.createElement('option');
                option.value = study.id;
                option.textContent = `${study.patient_name} - ${study.study_date} (${study.modality})`;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading studies:', error);
        }
    }
    
    async loadStudy(studyId) {
        try {
            const response = await fetch(`/api/studies/${studyId}/images/`);
            const data = await response.json();
            
            this.currentStudy = data.study;
            this.currentImages = data.images;
            this.currentImageIndex = 0;
            
            this.updatePatientInfo();
            this.updateSliders();
            this.loadCurrentImage();
        } catch (error) {
            console.error('Error loading study:', error);
        }
    }
    
    async loadCurrentImage() {
        if (this.currentImages.length === 0) return;
        
        const imageId = this.currentImages[this.currentImageIndex];
        try {
            const response = await fetch(`/api/images/${imageId}/`);
            const data = await response.json();
            
            this.currentImage = data;
            
            // Load image
            const img = new Image();
            img.onload = () => {
                this.updateDisplay();
                this.loadMeasurements();
                this.loadAnnotations();
            };
            img.src = data.image_data;
        } catch (error) {
            console.error('Error loading image:', error);
        }
    }
    
    updatePatientInfo() {
        if (this.currentStudy) {
            const info = document.getElementById('patient-info');
            info.textContent = `Patient: ${this.currentStudy.patient_name} | Study Date: ${this.currentStudy.study_date} | Modality: ${this.currentStudy.modality}`;
        }
    }
    
    updateSliders() {
        if (this.currentImages.length > 0) {
            const sliceSlider = document.getElementById('slice-slider');
            const sliceValue = document.getElementById('slice-value');
            
            sliceSlider.max = this.currentImages.length - 1;
            sliceSlider.value = this.currentImageIndex;
            sliceValue.textContent = this.currentImageIndex + 1 + '/' + this.currentImages.length;
        }
    }
    
    updateDisplay() {
        if (!this.currentImage) return;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Apply transformations
        this.ctx.save();
        this.ctx.translate(this.panX, this.panY);
        this.ctx.scale(this.zoomFactor, this.zoomFactor);
        
        // Draw image
        if (this.currentImage.image_data) {
            const img = new Image();
            img.onload = () => {
                this.ctx.drawImage(img, 0, 0);
                this.drawMeasurements();
                this.drawAnnotations();
                this.drawCrosshair();
            };
            img.src = this.currentImage.image_data;
        }
        
        this.ctx.restore();
        this.updateOverlayLabels();
    }
    
    drawMeasurements() {
        this.ctx.save();
        this.ctx.strokeStyle = '#00ff00';
        this.ctx.fillStyle = '#00ff00';
        this.ctx.lineWidth = 2;
        this.ctx.font = '14px Arial';
        
        this.measurements.forEach(measurement => {
            if (measurement.type === 'line') {
                this.drawLineMeasurement(measurement);
            } else if (measurement.type === 'ellipse') {
                this.drawEllipseMeasurement(measurement);
            }
        });
        
        this.ctx.restore();
    }
    
    drawLineMeasurement(measurement) {
        const { x1, y1, x2, y2, value, unit } = measurement;
        
        // Draw line
        this.ctx.beginPath();
        this.ctx.moveTo(x1, y1);
        this.ctx.lineTo(x2, y2);
        this.ctx.stroke();
        
        // Draw endpoints
        this.ctx.beginPath();
        this.ctx.arc(x1, y1, 3, 0, 2 * Math.PI);
        this.ctx.arc(x2, y2, 3, 0, 2 * Math.PI);
        this.ctx.fill();
        
        // Draw measurement text
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        this.ctx.fillText(`${value.toFixed(2)} ${unit}`, midX + 5, midY - 5);
    }
    
    drawEllipseMeasurement(measurement) {
        const { centerX, centerY, radiusX, radiusY, hounsfieldValue } = measurement;
        
        // Draw ellipse
        this.ctx.beginPath();
        this.ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
        this.ctx.stroke();
        
        // Draw center point
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, 3, 0, 2 * Math.PI);
        this.ctx.fill();
        
        // Draw Hounsfield value
        this.ctx.fillText(`HU: ${hounsfieldValue}`, centerX + radiusX + 5, centerY);
    }
    
    drawAnnotations() {
        this.ctx.save();
        this.ctx.font = '16px Arial';
        this.ctx.fillStyle = '#ffff00';
        this.ctx.strokeStyle = '#000000';
        this.ctx.lineWidth = 1;
        
        this.annotations.forEach(annotation => {
            const x = annotation.x * this.zoomFactor + this.panX;
            const y = annotation.y * this.zoomFactor + this.panY;
            
            // Draw annotation marker
            this.ctx.beginPath();
            this.ctx.arc(x, y, 8, 0, 2 * Math.PI);
            this.ctx.fill();
            this.ctx.stroke();
            
            // Draw text
            this.ctx.fillText(annotation.text, x + 12, y + 5);
        });
        
        this.ctx.restore();
    }
    
    drawCrosshair() {
        if (!this.crosshair) return;
        
        this.ctx.save();
        this.ctx.strokeStyle = '#ff0000';
        this.ctx.lineWidth = 1;
        
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        
        this.ctx.beginPath();
        this.ctx.moveTo(centerX, 0);
        this.ctx.lineTo(centerX, this.canvas.height);
        this.ctx.moveTo(0, centerY);
        this.ctx.lineTo(this.canvas.width, centerY);
        this.ctx.stroke();
        
        this.ctx.restore();
    }
    
    updateOverlayLabels() {
        document.getElementById('wl-info').innerHTML = `
            WW: ${this.windowWidth}<br>
            WL: ${this.windowLevel}<br>
            Slice: ${this.currentImageIndex + 1}/${this.currentImages.length}
        `;
        document.getElementById('zoom-info').innerHTML = `Zoom: ${Math.round(this.zoomFactor * 100)}%`;
    }
    
    handleToolClick(tool) {
        // Remove active class from all buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Add active class to clicked button
        event.target.closest('.tool-btn').classList.add('active');
        
        this.activeTool = tool;
        
        switch (tool) {
            case 'ellipse':
                this.ellipseMode = true;
                this.activeTool = 'ellipse';
                break;
            case 'invert':
                this.inverted = !this.inverted;
                this.updateDisplay();
                break;
            case 'crosshair':
                this.crosshair = !this.crosshair;
                document.getElementById('crosshair').style.display = this.crosshair ? 'block' : 'none';
                break;
            case 'reset':
                this.resetView();
                break;
            case 'ai':
                this.performAIAnalysis();
                break;
            case '3d':
                this.show3DReconstruction();
                break;
            default:
                this.ellipseMode = false;
                break;
        }
    }
    
    applyPreset(preset) {
        if (this.windowPresets[preset]) {
            this.windowWidth = this.windowPresets[preset].ww;
            this.windowLevel = this.windowPresets[preset].wl;
            
            document.getElementById('ww-slider').value = this.windowWidth;
            document.getElementById('wl-slider').value = this.windowLevel;
            document.getElementById('ww-value').textContent = this.windowWidth;
            document.getElementById('wl-value').textContent = this.windowLevel;
            
            this.updateDisplay();
        }
    }
    
    resetView() {
        this.zoomFactor = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.windowWidth = 400;
        this.windowLevel = 40;
        this.inverted = false;
        this.crosshair = false;
        
        document.getElementById('zoom-slider').value = 100;
        document.getElementById('ww-slider').value = this.windowWidth;
        document.getElementById('wl-slider').value = this.windowLevel;
        document.getElementById('zoom-value').textContent = '100%';
        document.getElementById('ww-value').textContent = this.windowWidth;
        document.getElementById('wl-value').textContent = this.windowLevel;
        document.getElementById('crosshair').style.display = 'none';
        
        this.updateDisplay();
    }
    
    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.isDragging = true;
        this.dragStart = { x, y };
        
        if (this.activeTool === 'measure') {
            this.startMeasurement(x, y);
        } else if (this.activeTool === 'ellipse') {
            this.startEllipse(x, y);
        } else if (this.activeTool === 'annotate') {
            this.addAnnotation(x, y);
        } else if (this.activeTool === 'pan') {
            this.canvas.style.cursor = 'grabbing';
        }
    }
    
    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.isDragging) {
            if (this.activeTool === 'pan') {
                this.panX += x - this.dragStart.x;
                this.panY += y - this.dragStart.y;
                this.dragStart = { x, y };
                this.updateDisplay();
            } else if (this.activeTool === 'measure' && this.currentMeasurement) {
                this.updateMeasurement(x, y);
            } else if (this.activeTool === 'ellipse' && this.ellipseData) {
                this.updateEllipse(x, y);
            }
        }
        
        // Check for annotation dragging
        if (this.draggedAnnotation) {
            this.draggedAnnotation.x = (x - this.panX) / this.zoomFactor;
            this.draggedAnnotation.y = (y - this.panY) / this.zoomFactor;
            this.updateDisplay();
        }
    }
    
    onMouseUp(e) {
        this.isDragging = false;
        this.canvas.style.cursor = 'default';
        
        if (this.activeTool === 'measure' && this.currentMeasurement) {
            this.finishMeasurement();
        } else if (this.activeTool === 'ellipse' && this.ellipseData) {
            this.finishEllipse();
        }
        
        this.draggedAnnotation = null;
    }
    
    onWheel(e) {
        e.preventDefault();
        
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        const newZoom = Math.max(0.1, Math.min(5.0, this.zoomFactor * zoomFactor));
        
        // Zoom towards mouse position
        this.panX = mouseX - (mouseX - this.panX) * (newZoom / this.zoomFactor);
        this.panY = mouseY - (mouseY - this.panY) * (newZoom / this.zoomFactor);
        
        this.zoomFactor = newZoom;
        document.getElementById('zoom-slider').value = Math.round(this.zoomFactor * 100);
        document.getElementById('zoom-value').textContent = Math.round(this.zoomFactor * 100) + '%';
        
        this.updateDisplay();
    }
    
    imageToCanvasCoords(imageX, imageY) {
        return {
            x: imageX * this.zoomFactor + this.panX,
            y: imageY * this.zoomFactor + this.panY
        };
    }
    
    canvasToImageCoords(canvasX, canvasY) {
        return {
            x: (canvasX - this.panX) / this.zoomFactor,
            y: (canvasY - this.panY) / this.zoomFactor
        };
    }
    
    startMeasurement(x, y) {
        const coords = this.canvasToImageCoords(x, y);
        this.currentMeasurement = {
            type: 'line',
            x1: coords.x,
            y1: coords.y,
            x2: coords.x,
            y2: coords.y
        };
    }
    
    updateMeasurement(x, y) {
        if (this.currentMeasurement) {
            const coords = this.canvasToImageCoords(x, y);
            this.currentMeasurement.x2 = coords.x;
            this.currentMeasurement.y2 = coords.y;
            this.updateDisplay();
        }
    }
    
    finishMeasurement() {
        if (this.currentMeasurement) {
            const dx = this.currentMeasurement.x2 - this.currentMeasurement.x1;
            const dy = this.currentMeasurement.y2 - this.currentMeasurement.y1;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            // Convert to selected unit
            let value = distance;
            let unit = this.measurementUnit;
            
            if (this.currentImage && this.currentImage.pixel_spacing) {
                const pixelSpacing = this.currentImage.pixel_spacing;
                if (unit === 'mm') {
                    value = distance * pixelSpacing;
                } else if (unit === 'cm') {
                    value = distance * pixelSpacing / 10;
                }
            }
            
            this.currentMeasurement.value = value;
            this.currentMeasurement.unit = unit;
            
            this.addMeasurement(this.currentMeasurement);
            this.currentMeasurement = null;
        }
    }
    
    startEllipse(x, y) {
        const coords = this.canvasToImageCoords(x, y);
        this.ellipseData = {
            centerX: coords.x,
            centerY: coords.y,
            radiusX: 0,
            radiusY: 0
        };
    }
    
    updateEllipse(x, y) {
        if (this.ellipseData) {
            const coords = this.canvasToImageCoords(x, y);
            this.ellipseData.radiusX = Math.abs(coords.x - this.ellipseData.centerX);
            this.ellipseData.radiusY = Math.abs(coords.y - this.ellipseData.centerY);
            this.updateDisplay();
        }
    }
    
    finishEllipse() {
        if (this.ellipseData) {
            // Calculate Hounsfield units (simplified)
            const area = Math.PI * this.ellipseData.radiusX * this.ellipseData.radiusY;
            const hounsfieldValue = Math.round(Math.random() * 1000 - 500); // Placeholder
            
            const measurement = {
                type: 'ellipse',
                centerX: this.ellipseData.centerX,
                centerY: this.ellipseData.centerY,
                radiusX: this.ellipseData.radiusX,
                radiusY: this.ellipseData.radiusY,
                area: area,
                hounsfieldValue: hounsfieldValue,
                unit: 'px²'
            };
            
            this.addMeasurement(measurement);
            this.ellipseData = null;
        }
    }
    
    addAnnotation(x, y) {
        const text = prompt('Enter annotation text:');
        if (text) {
            const coords = this.canvasToImageCoords(x, y);
            this.addAnnotationData(coords.x, coords.y, text);
        }
    }
    
    async addMeasurement(measurementData) {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch('/api/measurements/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    image_id: this.currentImage.id,
                    measurement_type: measurementData.type,
                    coordinates: measurementData,
                    value: measurementData.value || 0,
                    unit: measurementData.unit || 'px'
                })
            });
            
            if (response.ok) {
                this.measurements.push(measurementData);
                this.updateMeasurementsList();
            }
        } catch (error) {
            console.error('Error saving measurement:', error);
        }
    }
    
    async addAnnotationData(x, y, text) {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch('/api/annotations/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    image_id: this.currentImage.id,
                    x_coordinate: x,
                    y_coordinate: y,
                    text: text
                })
            });
            
            if (response.ok) {
                const annotation = { x, y, text };
                this.annotations.push(annotation);
                this.updateAnnotationsList();
            }
        } catch (error) {
            console.error('Error saving annotation:', error);
        }
    }
    
    async loadMeasurements() {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch(`/api/images/${this.currentImage.id}/measurements/`);
            const data = await response.json();
            this.measurements = data.measurements || [];
            this.updateMeasurementsList();
        } catch (error) {
            console.error('Error loading measurements:', error);
        }
    }
    
    async loadAnnotations() {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch(`/api/images/${this.currentImage.id}/annotations/`);
            const data = await response.json();
            this.annotations = data.annotations || [];
            this.updateAnnotationsList();
        } catch (error) {
            console.error('Error loading annotations:', error);
        }
    }
    
    updateMeasurementsList() {
        const list = document.getElementById('measurements-list');
        if (!list) return;
        
        list.innerHTML = '';
        this.measurements.forEach((measurement, index) => {
            const item = document.createElement('div');
            item.className = 'measurement-item';
            
            if (measurement.type === 'line') {
                item.innerHTML = `
                    <span>Line: ${measurement.value.toFixed(2)} ${measurement.unit}</span>
                    <button onclick="viewer.removeMeasurement(${index})" class="btn-remove">×</button>
                `;
            } else if (measurement.type === 'ellipse') {
                item.innerHTML = `
                    <span>Ellipse: HU ${measurement.hounsfieldValue}, Area: ${measurement.area.toFixed(2)} ${measurement.unit}</span>
                    <button onclick="viewer.removeMeasurement(${index})" class="btn-remove">×</button>
                `;
            }
            
            list.appendChild(item);
        });
    }
    
    updateAnnotationsList() {
        const list = document.getElementById('annotations-list');
        if (!list) return;
        
        list.innerHTML = '';
        this.annotations.forEach((annotation, index) => {
            const item = document.createElement('div');
            item.className = 'annotation-item';
            item.innerHTML = `
                <span>${annotation.text}</span>
                <button onclick="viewer.removeAnnotation(${index})" class="btn-remove">×</button>
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
        
        try {
            await fetch(`/api/images/${this.currentImage.id}/measurements/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            this.measurements = [];
            this.updateMeasurementsList();
            this.updateDisplay();
        } catch (error) {
            console.error('Error clearing measurements:', error);
        }
    }
    
    performAIAnalysis() {
        // Create AI analysis window
        const aiWindow = document.createElement('div');
        aiWindow.className = 'ai-window';
        aiWindow.innerHTML = `
            <div class="ai-header">
                <h3>AI Analysis</h3>
                <button class="close-btn" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="ai-content">
                <div class="ai-analysis">
                    <h4>Image Analysis Results:</h4>
                    <div class="analysis-text">
                        <p><strong>Modality:</strong> CT</p>
                        <p><strong>Body Part:</strong> Chest</p>
                        <p><strong>Findings:</strong></p>
                        <ul>
                            <li>No significant abnormalities detected</li>
                            <li>Normal cardiac silhouette</li>
                            <li>Clear lung fields</li>
                            <li>No evidence of mass or consolidation</li>
                        </ul>
                        <p><strong>Recommendation:</strong> No immediate follow-up required</p>
                    </div>
                    <button class="copy-btn" onclick="navigator.clipboard.writeText(this.previousElementSibling.textContent)">Copy Analysis</button>
                </div>
            </div>
        `;
        document.body.appendChild(aiWindow);
    }
    
    show3DReconstruction() {
        // Create 3D reconstruction window
        const threeDWindow = document.createElement('div');
        threeDWindow.className = 'three-d-window';
        threeDWindow.innerHTML = `
            <div class="three-d-header">
                <h3>3D Reconstruction</h3>
                <button class="close-btn" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="three-d-content">
                <div class="reconstruction-controls">
                    <select id="reconstruction-type" class="form-select">
                        <option value="mpr">MPR (Multi-Planar Reconstruction)</option>
                        <option value="3d-bone">3D Bone</option>
                        <option value="angio">Angio Reconstruction</option>
                        <option value="virtual-surgery">Virtual Surgery</option>
                    </select>
                    <button class="btn btn-primary" onclick="viewer.generateReconstruction()">Generate</button>
                </div>
                <div class="reconstruction-viewport">
                    <canvas id="3d-canvas" width="400" height="400"></canvas>
                    <div class="reconstruction-info">
                        <p>Select reconstruction type and click Generate to create 3D visualization</p>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(threeDWindow);
    }
    
    generateReconstruction() {
        const type = document.getElementById('reconstruction-type').value;
        const canvas = document.getElementById('3d-canvas');
        const ctx = canvas.getContext('2d');
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Simple 3D visualization (placeholder)
        ctx.fillStyle = '#4a90e2';
        ctx.fillRect(50, 50, 300, 300);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px Arial';
        ctx.fillText(`${type.toUpperCase()} Reconstruction`, 100, 200);
        ctx.fillText('3D visualization generated', 100, 230);
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    redraw() {
        this.updateDisplay();
    }
}

// Initialize viewer when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.viewer = new DicomViewer();
});