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
        this.currentMeasurementType = 'line';
        this.currentUnit = 'px';
        
        // Enhanced measurement features
        this.ellipseData = null;
        this.hounsfieldData = null;
        
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
        
        // Clear measurements
        document.getElementById('clear-measurements').addEventListener('click', () => {
            this.clearMeasurements();
        });
        
        // Measurement unit selector
        document.getElementById('measurement-unit').addEventListener('change', (e) => {
            this.currentUnit = e.target.value;
            this.updateMeasurementsList();
        });
        
        // AI Analysis
        document.getElementById('run-ai-analysis').addEventListener('click', () => {
            this.runAIAnalysis();
        });
        
        document.getElementById('copy-ai-results').addEventListener('click', () => {
            this.copyAIResults();
        });
        
        // 3D Reconstruction
        document.getElementById('create-3d-reconstruction').addEventListener('click', () => {
            this.create3DReconstruction();
        });
        
        // Canvas mouse events
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        
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
            select.innerHTML = '<option value="">Select DICOM from System</option>';
            
            studies.forEach(study => {
                const option = document.createElement('option');
                option.value = study.id;
                option.textContent = `${study.patient_name} - ${study.study_date} (${study.modality})`;
                select.appendChild(option);
            });
            
            select.addEventListener('change', (e) => {
                if (e.target.value) {
                    this.loadStudy(parseInt(e.target.value));
                }
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
            if (coords.length >= 2) {
                if (measurement.type === 'ellipse') {
                    this.drawEllipseMeasurement(measurement);
                } else {
                    this.drawLineMeasurement(measurement);
                }
            }
        });
        
        // Draw current measurement being created
        if (this.currentMeasurement) {
            if (this.currentMeasurementType === 'ellipse') {
                this.drawCurrentEllipse();
            } else {
                this.drawCurrentLineMeasurement();
            }
        }
    }
    
    drawLineMeasurement(measurement) {
        const coords = measurement.coordinates;
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
    
    drawEllipseMeasurement(measurement) {
        const coords = measurement.coordinates;
        const center = this.imageToCanvasCoords(coords[0].x, coords[0].y);
        const radiusX = coords[1].x - coords[0].x;
        const radiusY = coords[1].y - coords[0].y;
        
        this.ctx.beginPath();
        this.ctx.ellipse(center.x, center.y, radiusX, radiusY, 0, 0, 2 * Math.PI);
        this.ctx.stroke();
        
        // Draw area text
        const area = Math.PI * radiusX * radiusY;
        const text = `Area: ${area.toFixed(1)} ${measurement.unit}²`;
        
        const textMetrics = this.ctx.measureText(text);
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        this.ctx.fillRect(center.x - textMetrics.width/2 - 4, center.y - 8, textMetrics.width + 8, 16);
        
        this.ctx.fillStyle = 'red';
        this.ctx.fillText(text, center.x - textMetrics.width/2, center.y + 4);
    }
    
    drawCurrentLineMeasurement() {
        if (!this.currentMeasurement) return;
        
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
    
    drawCurrentEllipse() {
        if (!this.currentMeasurement) return;
        
        const start = this.imageToCanvasCoords(this.currentMeasurement.start.x, this.currentMeasurement.start.y);
        const end = this.imageToCanvasCoords(this.currentMeasurement.end.x, this.currentMeasurement.end.y);
        
        const centerX = (start.x + end.x) / 2;
        const centerY = (start.y + end.y) / 2;
        const radiusX = Math.abs(end.x - start.x) / 2;
        const radiusY = Math.abs(end.y - start.y) / 2;
        
        this.ctx.setLineDash([5, 5]);
        this.ctx.strokeStyle = 'yellow';
        this.ctx.beginPath();
        this.ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
        this.ctx.stroke();
        this.ctx.setLineDash([]);
    }
    
    drawAnnotations() {
        if (!this.currentImage) return;
        
        this.ctx.fillStyle = 'yellow';
        this.ctx.font = '12px Arial';
        
        this.annotations.forEach(annotation => {
            const pos = this.imageToCanvasCoords(annotation.x, annotation.y);
            
            // Background for text
            const textMetrics = this.ctx.measureText(annotation.text);
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
            this.ctx.fillRect(pos.x - 2, pos.y - 14, textMetrics.width + 4, 16);
            
            this.ctx.fillStyle = 'yellow';
            this.ctx.fillText(annotation.text, pos.x, pos.y);
        });
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
        console.log('Tool activated:', tool);
        
        if (tool === 'reset') {
            this.resetView();
        } else if (tool === 'invert') {
            this.inverted = !this.inverted;
            this.loadCurrentImage();
        } else if (tool === 'crosshair') {
            this.crosshair = !this.crosshair;
            this.updateDisplay();
        } else if (tool === 'ai') {
            this.showAISection();
        } else if (tool === '3d') {
            this.show3DSection();
        } else if (tool === 'ellipse') {
            this.currentMeasurementType = 'ellipse';
            this.activeTool = 'measure';
        } else if (tool === 'hounsfield') {
            this.currentMeasurementType = 'hounsfield';
            this.activeTool = 'measure';
        } else {
            this.activeTool = tool;
            this.currentMeasurementType = 'line';
        }
        
        // Update button states
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        if (!['reset', 'invert', 'crosshair', 'ai', '3d'].includes(tool)) {
            document.querySelector(`[data-tool="${tool}"]`).classList.add('active');
        }
    }
    
    showAISection() {
        const aiSection = document.getElementById('ai-section');
        const threeDSection = document.getElementById('3d-section');
        
        aiSection.style.display = 'block';
        threeDSection.style.display = 'none';
    }
    
    show3DSection() {
        const aiSection = document.getElementById('ai-section');
        const threeDSection = document.getElementById('3d-section');
        
        aiSection.style.display = 'none';
        threeDSection.style.display = 'block';
    }
    
    async runAIAnalysis() {
        if (!this.currentImage) return;
        
        const analysisType = document.getElementById('ai-analysis-type').value;
        
        try {
            const response = await fetch(`/api/images/${this.currentImage.id}/ai-analysis/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ analysis_type: analysisType })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayAIResults(data.analysis);
            } else {
                throw new Error('AI analysis failed');
            }
        } catch (error) {
            console.error('AI analysis error:', error);
            alert('AI analysis failed. Please try again.');
        }
    }
    
    displayAIResults(analysis) {
        document.getElementById('ai-confidence-score').textContent = `${analysis.confidence_score}%`;
        document.getElementById('ai-findings-text').textContent = analysis.findings;
        document.getElementById('ai-results').style.display = 'block';
        
        // Highlight regions on image
        this.highlightAIRegions(analysis.highlighted_regions);
    }
    
    highlightAIRegions(regions) {
        if (!this.currentImage) return;
        
        this.ctx.strokeStyle = 'rgba(0, 255, 0, 0.8)';
        this.ctx.lineWidth = 3;
        this.ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
        
        regions.forEach(region => {
            const x = this.imageToCanvasCoords(region.x, region.y).x;
            const y = this.imageToCanvasCoords(region.x, region.y).y;
            const width = region.width * this.zoomFactor;
            const height = region.height * this.zoomFactor;
            
            this.ctx.fillRect(x, y, width, height);
            this.ctx.strokeRect(x, y, width, height);
        });
    }
    
    copyAIResults() {
        const findings = document.getElementById('ai-findings-text').textContent;
        const confidence = document.getElementById('ai-confidence-score').textContent;
        
        const text = `AI Analysis Results:\nConfidence: ${confidence}\nFindings: ${findings}`;
        
        navigator.clipboard.writeText(text).then(() => {
            alert('AI results copied to clipboard!');
        }).catch(() => {
            alert('Failed to copy results');
        });
    }
    
    async create3DReconstruction() {
        if (!this.currentStudy) return;
        
        const reconstructionType = document.getElementById('3d-reconstruction-type').value;
        
        try {
            const response = await fetch(`/api/studies/${this.currentStudy.id}/reconstruction/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ 
                    type: reconstructionType,
                    settings: {}
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.display3DResults(data.reconstruction);
            } else {
                throw new Error('3D reconstruction failed');
            }
        } catch (error) {
            console.error('3D reconstruction error:', error);
            alert('3D reconstruction failed. Please try again.');
        }
    }
    
    display3DResults(reconstruction) {
        document.getElementById('3d-status-text').textContent = reconstruction.status;
        document.getElementById('3d-preview-container').innerHTML = `
            <div style="background: #444; padding: 20px; border-radius: 4px; text-align: center;">
                <i class="fas fa-cube" style="font-size: 48px; color: #0078d4;"></i>
                <p>${reconstruction.type} reconstruction completed</p>
                <p>Preview available at: ${reconstruction.preview_url}</p>
            </div>
        `;
        document.getElementById('3d-results').style.display = 'block';
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
        } else if (this.activeTool === 'annotate') {
            const text = prompt('Enter annotation text:');
            if (text) {
                const imageCoords = this.canvasToImageCoords(x, y);
                this.addAnnotation(imageCoords.x, imageCoords.y, text);
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
        
        if (this.activeTool === 'pan') {
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
        }
    }
    
    onMouseUp(e) {
        if (this.activeTool === 'measure' && this.currentMeasurement) {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const imageCoords = this.canvasToImageCoords(x, y);
            
            this.currentMeasurement.end = imageCoords;
            this.addMeasurement(this.currentMeasurement);
            this.currentMeasurement = null;
        }
        
        this.isDragging = false;
        this.dragStart = null;
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
        let value = 0;
        let unit = this.currentUnit;
        
        if (this.currentMeasurementType === 'ellipse') {
            // Calculate ellipse area
            const radiusX = Math.abs(measurementData.end.x - measurementData.start.x) / 2;
            const radiusY = Math.abs(measurementData.end.y - measurementData.start.y) / 2;
            value = Math.PI * radiusX * radiusY;
        } else if (this.currentMeasurementType === 'hounsfield') {
            // Get Hounsfield units at the point
            value = this.getHounsfieldValue(measurementData.start.x, measurementData.start.y);
            unit = 'hu';
        } else {
            // Line measurement
            const distance = Math.sqrt(
                Math.pow(measurementData.end.x - measurementData.start.x, 2) +
                Math.pow(measurementData.end.y - measurementData.start.y, 2)
            );
            value = distance;
        }
        
        // Convert to different units if needed
        if (unit === 'mm' || unit === 'cm') {
            const metadata = this.currentImage.metadata;
            if (metadata.pixel_spacing_x && metadata.pixel_spacing_y) {
                const avgSpacing = (metadata.pixel_spacing_x + metadata.pixel_spacing_y) / 2;
                if (unit === 'mm') {
                    value = value * avgSpacing;
                } else if (unit === 'cm') {
                    value = value * avgSpacing * 10;
                }
            }
        }
        
        const measurement = {
            image_id: this.currentImage.id,
            type: this.currentMeasurementType,
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
    
    getHounsfieldValue(x, y) {
        // Simulate Hounsfield unit calculation
        // In a real implementation, this would read the actual pixel values from the DICOM
        return Math.floor(Math.random() * 2000) - 1000; // Random HU value between -1000 and 1000
    }
    
    async addAnnotation(x, y, text) {
        const annotation = {
            image_id: this.currentImage.id,
            x: x,
            y: y,
            text: text,
            font_size: 12,
            is_draggable: true
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
            
            let displayValue = measurement.value;
            let displayUnit = measurement.unit;
            
            // Convert to current unit if needed
            if (this.currentUnit !== measurement.unit) {
                if (this.currentUnit === 'mm' && measurement.unit === 'px') {
                    const metadata = this.currentImage.metadata;
                    if (metadata.pixel_spacing_x && metadata.pixel_spacing_y) {
                        const avgSpacing = (metadata.pixel_spacing_x + metadata.pixel_spacing_y) / 2;
                        displayValue = measurement.value * avgSpacing;
                        displayUnit = 'mm';
                    }
                } else if (this.currentUnit === 'cm' && measurement.unit === 'px') {
                    const metadata = this.currentImage.metadata;
                    if (metadata.pixel_spacing_x && metadata.pixel_spacing_y) {
                        const avgSpacing = (metadata.pixel_spacing_x + metadata.pixel_spacing_y) / 2;
                        displayValue = measurement.value * avgSpacing * 10;
                        displayUnit = 'cm';
                    }
                }
            }
            
            item.textContent = `${measurement.type.charAt(0).toUpperCase() + measurement.type.slice(1)} ${index + 1}: ${displayValue.toFixed(1)} ${displayUnit}`;
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
    
    // Utility functions
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    redraw() {
        if (this.currentImage) {
            this.updateDisplay();
        }
    }
}

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new DicomViewer();
});