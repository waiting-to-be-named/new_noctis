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
        this.selectedAnnotation = null;
        this.isDragging = false;
        this.dragStart = null;
        
        // Measurement settings
        this.measurementUnit = 'mm'; // mm, cm, px
        
        // Window presets
        this.windowPresets = {
            'lung': { ww: 1500, wl: -600 },
            'bone': { ww: 2000, wl: 300 },
            'soft': { ww: 400, wl: 40 },
            'brain': { ww: 100, wl: 50 }
        };
        
        // AI analysis results
        this.aiResults = null;
        this.showAiHighlights = false;
        
        this.init();
    }
    
    init() {
        this.setupCanvas();
        this.setupEventListeners();
        this.loadBackendStudies();
        this.setupNotifications();
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
        
        // Measurement unit dropdown
        const unitDropdown = document.getElementById('measurement-unit');
        if (unitDropdown) {
            unitDropdown.addEventListener('change', (e) => {
                this.measurementUnit = e.target.value;
            });
        }
        
        // 3D reconstruction dropdown
        const reconstructionDropdown = document.getElementById('3d-reconstruction-type');
        if (reconstructionDropdown) {
            reconstructionDropdown.addEventListener('change', (e) => {
                if (e.target.value) {
                    this.trigger3DReconstruction(e.target.value);
                }
            });
        }
        
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
        
        // Canvas mouse events
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        
        // Upload modal events
        this.setupUploadModal();
        
        // AI analysis button
        const aiBtn = document.getElementById('ai-analysis-btn');
        if (aiBtn) {
            aiBtn.addEventListener('click', () => this.triggerAIAnalysis());
        }
        
        // Show/hide AI highlights
        const aiHighlightsBtn = document.getElementById('toggle-ai-highlights');
        if (aiHighlightsBtn) {
            aiHighlightsBtn.addEventListener('click', () => {
                this.showAiHighlights = !this.showAiHighlights;
                this.updateDisplay();
            });
        }
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
    
    setupNotifications() {
        // Check for notifications periodically
        setInterval(() => {
            this.checkNotifications();
        }, 30000); // Check every 30 seconds
    }
    
    async checkNotifications() {
        try {
            const response = await fetch('/api/notifications/');
            if (response.ok) {
                const notifications = await response.json();
                this.displayNotifications(notifications);
            }
        } catch (error) {
            console.error('Error checking notifications:', error);
        }
    }
    
    displayNotifications(notifications) {
        const notificationArea = document.getElementById('notification-area');
        if (!notificationArea || notifications.length === 0) return;
        
        // Clear existing notifications
        notificationArea.innerHTML = '';
        
        notifications.forEach(notification => {
            const notificationEl = document.createElement('div');
            notificationEl.className = 'notification-item';
            notificationEl.innerHTML = `
                <div class="notification-header">
                    <strong>${notification.title}</strong>
                    <button onclick="markNotificationRead(${notification.id})" class="close-notification">×</button>
                </div>
                <div class="notification-message">${notification.message}</div>
                <div class="notification-time">${new Date(notification.created_at).toLocaleString()}</div>
            `;
            notificationArea.appendChild(notificationEl);
        });
        
        // Show notification area
        notificationArea.style.display = 'block';
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
            select.innerHTML = '<option value="">Load DICOM from System</option>';
            
            studies.forEach(study => {
                const option = document.createElement('option');
                option.value = study.id;
                option.textContent = `${study.patient_name} - ${study.study_date} (${study.modality})`;
                select.appendChild(option);
            });
            
            select.addEventListener('change', (e) => {
                if (e.target.value) {
                    // Redirect to worklist instead of loading directly
                    window.location.href = '/worklist/';
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
        this.drawAIHighlights();
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
            
            if (measurement.measurement_type === 'ellipse' || measurement.measurement_type === 'hounsfield') {
                // Draw ellipse
                if (coords.length >= 2) {
                    const start = this.imageToCanvasCoords(coords[0].x, coords[0].y);
                    const end = this.imageToCanvasCoords(coords[1].x, coords[1].y);
                    
                    const centerX = (start.x + end.x) / 2;
                    const centerY = (start.y + end.y) / 2;
                    const radiusX = Math.abs(end.x - start.x) / 2;
                    const radiusY = Math.abs(end.y - start.y) / 2;
                    
                    this.ctx.beginPath();
                    this.ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
                    this.ctx.stroke();
                    
                    // Draw measurement text
                    let text = `${measurement.value.toFixed(1)} ${measurement.unit}`;
                    if (measurement.unit === 'hu') {
                        text = `HU: ${measurement.value.toFixed(0)}`;
                    }
                    
                    // Background for text
                    const textMetrics = this.ctx.measureText(text);
                    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                    this.ctx.fillRect(centerX - textMetrics.width/2 - 4, centerY - 8, textMetrics.width + 8, 16);
                    
                    this.ctx.fillStyle = 'red';
                    this.ctx.fillText(text, centerX - textMetrics.width/2, centerY + 4);
                }
            } else {
                // Draw line measurement
                if (coords.length >= 2) {
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
            }
        });
        
        // Draw current measurement being created
        if (this.currentMeasurement) {
            const start = this.imageToCanvasCoords(this.currentMeasurement.start.x, this.currentMeasurement.start.y);
            const end = this.imageToCanvasCoords(this.currentMeasurement.end.x, this.currentMeasurement.end.y);
            
            this.ctx.setLineDash([5, 5]);
            this.ctx.strokeStyle = 'yellow';
            
            if (this.activeTool === 'ellipse') {
                // Draw ellipse preview
                const centerX = (start.x + end.x) / 2;
                const centerY = (start.y + end.y) / 2;
                const radiusX = Math.abs(end.x - start.x) / 2;
                const radiusY = Math.abs(end.y - start.y) / 2;
                
                this.ctx.beginPath();
                this.ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
                this.ctx.stroke();
            } else {
                // Draw line preview
                this.ctx.beginPath();
                this.ctx.moveTo(start.x, start.y);
                this.ctx.lineTo(end.x, end.y);
                this.ctx.stroke();
            }
            this.ctx.setLineDash([]);
        }
    }
    
    drawAnnotations() {
        if (!this.currentImage) return;
        
        this.annotations.forEach(annotation => {
            const pos = this.imageToCanvasCoords(annotation.x_coordinate, annotation.y_coordinate);
            
            // Set font size
            this.ctx.font = `${annotation.font_size || 12}px Arial`;
            
            // Background for text
            const textMetrics = this.ctx.measureText(annotation.text);
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
            this.ctx.fillRect(pos.x - 2, pos.y - annotation.font_size - 2, textMetrics.width + 4, annotation.font_size + 4);
            
            // Text
            this.ctx.fillStyle = annotation.is_draggable ? 'yellow' : 'white';
            this.ctx.fillText(annotation.text, pos.x, pos.y);
            
            // Draw resize handle if selected
            if (this.selectedAnnotation && this.selectedAnnotation.id === annotation.id) {
                this.ctx.strokeStyle = 'blue';
                this.ctx.lineWidth = 1;
                this.ctx.strokeRect(pos.x - 5, pos.y - annotation.font_size - 5, textMetrics.width + 10, annotation.font_size + 10);
            }
        });
    }
    
    drawAIHighlights() {
        if (!this.showAiHighlights || !this.aiResults || !this.aiResults.highlighted_regions) return;
        
        this.ctx.strokeStyle = 'lime';
        this.ctx.lineWidth = 3;
        this.ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
        
        this.aiResults.highlighted_regions.forEach(region => {
            const topLeft = this.imageToCanvasCoords(region.x, region.y);
            const bottomRight = this.imageToCanvasCoords(region.x + region.width, region.y + region.height);
            
            const width = bottomRight.x - topLeft.x;
            const height = bottomRight.y - topLeft.y;
            
            // Draw filled rectangle
            this.ctx.fillRect(topLeft.x, topLeft.y, width, height);
            
            // Draw border
            this.ctx.strokeRect(topLeft.x, topLeft.y, width, height);
            
            // Draw label
            this.ctx.fillStyle = 'lime';
            this.ctx.font = '12px Arial';
            this.ctx.fillText('AI: Anomaly Detected', topLeft.x, topLeft.y - 5);
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
            this.triggerAIAnalysis();
        } else if (tool === '3d') {
            this.show3DReconstructionModal();
        } else {
            this.activeTool = tool;
        }
        
        // Update button states
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        if (!['reset', 'invert', 'crosshair', 'ai', '3d'].includes(tool)) {
            document.querySelector(`[data-tool="${tool}"]`).classList.add('active');
        }
    }
    
    show3DReconstructionModal() {
        const modal = document.getElementById('3d-reconstruction-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }
    
    async trigger3DReconstruction(type) {
        if (!this.currentStudy) {
            alert('No study loaded');
            return;
        }
        
        try {
            const response = await fetch(`/api/studies/${this.currentStudy.id}/3d-reconstruction/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ type: type, settings: {} })
            });
            
            if (response.ok) {
                const result = await response.json();
                alert(`3D ${type} reconstruction initiated`);
                // TODO: Handle 3D reconstruction display
            } else {
                throw new Error('3D reconstruction failed');
            }
        } catch (error) {
            console.error('3D reconstruction error:', error);
            alert('Error: ' + error.message);
        }
    }
    
    async triggerAIAnalysis() {
        if (!this.currentImage) {
            alert('No image loaded');
            return;
        }
        
        try {
            const response = await fetch(`/api/images/${this.currentImage.id}/ai-analysis/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ type: 'anomaly_detection' })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.aiResults = result;
                this.showAiHighlights = true;
                this.updateDisplay();
                this.showAIResultsPanel(result);
            } else {
                throw new Error('AI analysis failed');
            }
        } catch (error) {
            console.error('AI analysis error:', error);
            alert('Error: ' + error.message);
        }
    }
    
    showAIResultsPanel(results) {
        const panel = document.getElementById('ai-results-panel');
        if (!panel) return;
        
        panel.innerHTML = `
            <div class="ai-results-header">
                <h3>AI Analysis Results</h3>
                <button onclick="this.parentElement.parentElement.style.display='none'">×</button>
            </div>
            <div class="ai-results-content">
                <p><strong>Confidence:</strong> ${(results.confidence_score * 100).toFixed(1)}%</p>
                <p><strong>Status:</strong> ${results.status}</p>
                <div class="ai-findings">
                    <strong>Findings:</strong>
                    <ul>
                        ${results.results.findings.map(finding => `<li>${finding}</li>`).join('')}
                    </ul>
                </div>
                <button onclick="copyAIResults('${JSON.stringify(results).replace(/"/g, '&quot;')}')">Copy Results</button>
            </div>
        `;
        panel.style.display = 'block';
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
        
        // Check if clicking on annotation for dragging
        if (this.activeTool === 'annotate') {
            const clickedAnnotation = this.getAnnotationAtPosition(x, y);
            if (clickedAnnotation && clickedAnnotation.is_draggable) {
                this.selectedAnnotation = clickedAnnotation;
                return;
            }
        }
        
        if (this.activeTool === 'measure' || this.activeTool === 'ellipse') {
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
        
        // Handle annotation dragging
        if (this.selectedAnnotation && this.selectedAnnotation.is_draggable) {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.updateAnnotationPosition(this.selectedAnnotation.id, imageCoords.x, imageCoords.y);
            this.updateDisplay();
            return;
        }
        
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
        } else if ((this.activeTool === 'measure' || this.activeTool === 'ellipse') && this.currentMeasurement) {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.currentMeasurement.end = imageCoords;
            this.updateDisplay();
        }
    }
    
    onMouseUp(e) {
        if ((this.activeTool === 'measure' || this.activeTool === 'ellipse') && this.currentMeasurement) {
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
    
    getAnnotationAtPosition(canvasX, canvasY) {
        for (let annotation of this.annotations) {
            const pos = this.imageToCanvasCoords(annotation.x_coordinate, annotation.y_coordinate);
            const fontSize = annotation.font_size || 12;
            
            // Simple bounding box check
            const textMetrics = this.ctx.measureText(annotation.text);
            if (canvasX >= pos.x - 5 && canvasX <= pos.x + textMetrics.width + 5 &&
                canvasY >= pos.y - fontSize - 5 && canvasY <= pos.y + 5) {
                return annotation;
            }
        }
        return null;
    }
    
    async updateAnnotationPosition(annotationId, x, y) {
        try {
            const response = await fetch(`/api/annotations/${annotationId}/update/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ x: x, y: y })
            });
            
            if (response.ok) {
                // Update local annotation
                const annotation = this.annotations.find(a => a.id === annotationId);
                if (annotation) {
                    annotation.x_coordinate = x;
                    annotation.y_coordinate = y;
                }
            }
        } catch (error) {
            console.error('Error updating annotation position:', error);
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
        let measurementType = this.activeTool === 'ellipse' ? 'ellipse' : 'line';
        let distance, value, unit;
        
        if (measurementType === 'ellipse') {
            // Calculate ellipse area or HU
            const width = Math.abs(measurementData.end.x - measurementData.start.x);
            const height = Math.abs(measurementData.end.y - measurementData.start.y);
            
            // Check if this is for Hounsfield units
            if (this.measurementUnit === 'hu') {
                measurementType = 'hounsfield';
                unit = 'hu';
                value = 0; // Will be calculated on backend
            } else {
                // Calculate area
                const area = Math.PI * (width / 2) * (height / 2);
                value = area;
                unit = this.measurementUnit === 'px' ? 'px²' : this.measurementUnit + '²';
                
                // Convert to real units if pixel spacing available
                const metadata = this.currentImage.metadata;
                if (metadata.pixel_spacing_x && metadata.pixel_spacing_y && this.measurementUnit !== 'px') {
                    const avgSpacing = (metadata.pixel_spacing_x + metadata.pixel_spacing_y) / 2;
                    if (this.measurementUnit === 'mm') {
                        value = area * avgSpacing * avgSpacing;
                    } else if (this.measurementUnit === 'cm') {
                        value = area * avgSpacing * avgSpacing / 100;
                    }
                }
            }
        } else {
            // Line measurement
            distance = Math.sqrt(
                Math.pow(measurementData.end.x - measurementData.start.x, 2) +
                Math.pow(measurementData.end.y - measurementData.start.y, 2)
            );
            
            unit = this.measurementUnit;
            value = distance;
            
            // Convert to real units if pixel spacing available
            const metadata = this.currentImage.metadata;
            if (metadata.pixel_spacing_x && metadata.pixel_spacing_y && this.measurementUnit !== 'px') {
                const avgSpacing = (metadata.pixel_spacing_x + metadata.pixel_spacing_y) / 2;
                if (this.measurementUnit === 'mm') {
                    value = distance * avgSpacing;
                } else if (this.measurementUnit === 'cm') {
                    value = distance * avgSpacing / 10;
                }
            }
        }
        
        const measurement = {
            image_id: this.currentImage.id,
            type: measurementType,
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
                const result = await response.json();
                // Update measurement with server-calculated value (for HU)
                measurement.value = result.value || measurement.value;
                measurement.unit = result.unit || measurement.unit;
                
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
                const result = await response.json();
                annotation.id = result.annotation_id;
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
            
            let displayText = `${measurement.measurement_type}: ${measurement.value.toFixed(1)} ${measurement.unit}`;
            if (measurement.unit === 'hu') {
                displayText = `Hounsfield Units: ${measurement.value.toFixed(0)} HU`;
            }
            
            item.textContent = displayText;
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

// Global functions for UI interactions
function copyAIResults(resultsJson) {
    const results = JSON.parse(resultsJson.replace(/&quot;/g, '"'));
    const text = `AI Analysis Results:
Confidence: ${(results.confidence_score * 100).toFixed(1)}%
Status: ${results.status}
Findings: ${results.results.findings.join(', ')}`;
    
    navigator.clipboard.writeText(text).then(() => {
        alert('AI results copied to clipboard');
    });
}

function markNotificationRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        }
    }).then(() => {
        // Remove notification from display
        const notificationEl = event.target.closest('.notification-item');
        if (notificationEl) {
            notificationEl.remove();
        }
    });
}

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dicomViewer = new DicomViewer();
});