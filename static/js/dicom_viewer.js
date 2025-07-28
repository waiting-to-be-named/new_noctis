// Enhanced DICOM Viewer JavaScript
class DicomViewer {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.currentImageData = null;
        this.currentTool = 'zoom';
        this.measurements = [];
        this.annotations = [];
        this.isDrawing = false;
        this.startX = 0;
        this.startY = 0;
        this.zoom = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        this.measurementUnit = 'mm'; // Default unit
        this.pixelSpacing = { x: 1, y: 1 }; // Default pixel spacing
        this.hounsfield = null;
        this.studyId = null;
        this.seriesId = null;
        this.selectedAnnotation = null;
        this.isDraggingAnnotation = false;
        
        // 3D Visualization
        this.current3DMode = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        
        // AI Chat
        this.aiChat = new AIChat();
        
        this.init();
    }

    init() {
        this.setupCanvas();
        this.setupEventListeners();
        this.setupToolbar();
        this.setupMeasurementUnits();
        this.setup3DVisualization();
        this.setupNotifications();
        this.loadStudyData();
    }

    setupCanvas() {
        this.canvas = document.getElementById('dicom-canvas');
        if (!this.canvas) return;
        
        this.ctx = this.canvas.getContext('2d');
        this.resizeCanvas();
        
        // Setup canvas event listeners
        this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
        this.canvas.addEventListener('wheel', this.handleWheel.bind(this));
        this.canvas.addEventListener('contextmenu', e => e.preventDefault());
    }

    setupEventListeners() {
        // Tool selection
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.selectTool(e.target.dataset.tool);
            });
        });

        // 3D Mode selection
        document.getElementById('3d-mode-select')?.addEventListener('change', (e) => {
            this.switch3DMode(e.target.value);
        });

        // Measurement unit selection
        document.getElementById('measurement-unit')?.addEventListener('change', (e) => {
            this.measurementUnit = e.target.value;
            this.updateMeasurementDisplays();
        });

        // Window resize
        window.addEventListener('resize', () => this.resizeCanvas());
        
        // File upload
        document.getElementById('dicom-upload')?.addEventListener('change', this.handleFileUpload.bind(this));
        
        // AI Chat toggle
        document.getElementById('ai-chat-toggle')?.addEventListener('click', () => {
            this.aiChat.toggle();
        });
    }

    setupToolbar() {
        const toolbar = document.querySelector('.toolbar');
        if (!toolbar) return;

        // Add measurement unit dropdown
        const measurementGroup = document.createElement('div');
        measurementGroup.className = 'tool-group';
        measurementGroup.innerHTML = `
            <label for="measurement-unit">Unit:</label>
            <select id="measurement-unit" class="unit-select">
                <option value="mm">mm</option>
                <option value="cm">cm</option>
                <option value="px">pixels</option>
            </select>
        `;
        toolbar.appendChild(measurementGroup);

        // Add 3D visualization controls
        const viz3DGroup = document.createElement('div');
        viz3DGroup.className = 'tool-group';
        viz3DGroup.innerHTML = `
            <label for="3d-mode-select">3D Mode:</label>
            <select id="3d-mode-select" class="mode-select">
                <option value="">Select Mode</option>
                <option value="mpr">MPR</option>
                <option value="3d-bone">3D Bone</option>
                <option value="angio">Angio Reconstruction</option>
                <option value="virtual-surgery">Virtual Surgery</option>
            </select>
        `;
        toolbar.appendChild(viz3DGroup);
    }

    setupMeasurementUnits() {
        // Initialize measurement unit dropdown
        const unitSelect = document.getElementById('measurement-unit');
        if (unitSelect) {
            unitSelect.value = this.measurementUnit;
        }
    }

    setup3DVisualization() {
        const viewport3D = document.getElementById('viewport-3d');
        if (!viewport3D) return;

        // Initialize Three.js if available
        if (typeof THREE !== 'undefined') {
            this.scene = new THREE.Scene();
            this.camera = new THREE.PerspectiveCamera(75, viewport3D.clientWidth / viewport3D.clientHeight, 0.1, 1000);
            this.renderer = new THREE.WebGLRenderer({ antialias: true });
            this.renderer.setSize(viewport3D.clientWidth, viewport3D.clientHeight);
            this.renderer.setClearColor(0x000000);
            viewport3D.appendChild(this.renderer.domElement);
        }
    }

    setupNotifications() {
        // Check for new uploads if user is radiologist/admin
        if (this.isRadiologistOrAdmin()) {
            setInterval(() => {
                this.checkForNewUploads();
            }, 30000); // Check every 30 seconds
        }
    }

    selectTool(tool) {
        this.currentTool = tool;
        
        // Update UI
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tool="${tool}"]`)?.classList.add('active');
        
        // Update cursor
        this.updateCursor();
    }

    updateCursor() {
        if (!this.canvas) return;
        
        switch(this.currentTool) {
            case 'zoom':
                this.canvas.style.cursor = 'zoom-in';
                break;
            case 'pan':
                this.canvas.style.cursor = 'move';
                break;
            case 'measure':
                this.canvas.style.cursor = 'crosshair';
                break;
            case 'ellipse':
                this.canvas.style.cursor = 'crosshair';
                break;
            case 'annotate':
                this.canvas.style.cursor = 'text';
                break;
            default:
                this.canvas.style.cursor = 'default';
        }
    }

    handleMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.startX = x;
        this.startY = y;
        this.isDrawing = true;

        // Check if clicking on existing annotation
        const annotation = this.getAnnotationAt(x, y);
        if (annotation && this.currentTool === 'annotate') {
            this.selectedAnnotation = annotation;
            this.isDraggingAnnotation = true;
            return;
        }

        switch(this.currentTool) {
            case 'measure':
                this.startMeasurement(x, y);
                break;
            case 'ellipse':
                this.startEllipse(x, y);
                break;
            case 'annotate':
                this.addAnnotation(x, y);
                break;
        }
    }

    handleMouseMove(e) {
        if (!this.isDrawing) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (this.isDraggingAnnotation && this.selectedAnnotation) {
            this.selectedAnnotation.x = x;
            this.selectedAnnotation.y = y;
            this.redraw();
            return;
        }

        switch(this.currentTool) {
            case 'pan':
                this.pan(x - this.startX, y - this.startY);
                this.startX = x;
                this.startY = y;
                break;
            case 'measure':
                this.updateMeasurement(x, y);
                break;
            case 'ellipse':
                this.updateEllipse(x, y);
                break;
        }
    }

    handleMouseUp(e) {
        this.isDrawing = false;
        this.isDraggingAnnotation = false;
        this.selectedAnnotation = null;

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        switch(this.currentTool) {
            case 'measure':
                this.finalizeMeasurement(x, y);
                break;
            case 'ellipse':
                this.finalizeEllipse(x, y);
                break;
        }
    }

    handleWheel(e) {
        e.preventDefault();
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        this.zoomAt(x, y, delta);
    }

    startMeasurement(x, y) {
        this.currentMeasurement = {
            startX: x,
            startY: y,
            endX: x,
            endY: y,
            type: 'line'
        };
    }

    updateMeasurement(x, y) {
        if (this.currentMeasurement) {
            this.currentMeasurement.endX = x;
            this.currentMeasurement.endY = y;
            this.redraw();
        }
    }

    finalizeMeasurement(x, y) {
        if (this.currentMeasurement) {
            this.currentMeasurement.endX = x;
            this.currentMeasurement.endY = y;
            
            // Calculate distance
            const distance = this.calculateDistance(
                this.currentMeasurement.startX,
                this.currentMeasurement.startY,
                this.currentMeasurement.endX,
                this.currentMeasurement.endY
            );
            
            this.currentMeasurement.distance = distance;
            this.currentMeasurement.unit = this.measurementUnit;
            this.measurements.push(this.currentMeasurement);
            this.currentMeasurement = null;
            
            this.redraw();
            this.updateMeasurementList();
        }
    }

    startEllipse(x, y) {
        this.currentEllipse = {
            centerX: x,
            centerY: y,
            radiusX: 0,
            radiusY: 0,
            type: 'ellipse'
        };
    }

    updateEllipse(x, y) {
        if (this.currentEllipse) {
            this.currentEllipse.radiusX = Math.abs(x - this.currentEllipse.centerX);
            this.currentEllipse.radiusY = Math.abs(y - this.currentEllipse.centerY);
            this.redraw();
        }
    }

    finalizeEllipse(x, y) {
        if (this.currentEllipse) {
            this.currentEllipse.radiusX = Math.abs(x - this.currentEllipse.centerX);
            this.currentEllipse.radiusY = Math.abs(y - this.currentEllipse.centerY);
            
            // Calculate Hounsfield units within ellipse
            const hounsfieldStats = this.calculateHounsfieldInEllipse(this.currentEllipse);
            this.currentEllipse.hounsfield = hounsfieldStats;
            
            this.measurements.push(this.currentEllipse);
            this.currentEllipse = null;
            
            this.redraw();
            this.updateMeasurementList();
        }
    }

    addAnnotation(x, y) {
        const text = prompt('Enter annotation text:');
        if (text) {
            const annotation = {
                x: x,
                y: y,
                text: text,
                type: 'annotation',
                fontSize: 16,
                color: '#FFD700'
            };
            this.annotations.push(annotation);
            this.redraw();
        }
    }

    getAnnotationAt(x, y) {
        for (let annotation of this.annotations) {
            const distance = Math.sqrt(
                Math.pow(x - annotation.x, 2) + Math.pow(y - annotation.y, 2)
            );
            if (distance < 20) { // 20px tolerance
                return annotation;
            }
        }
        return null;
    }

    calculateDistance(x1, y1, x2, y2) {
        const pixelDistance = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
        
        let realDistance;
        switch(this.measurementUnit) {
            case 'mm':
                realDistance = pixelDistance * this.pixelSpacing.x;
                break;
            case 'cm':
                realDistance = (pixelDistance * this.pixelSpacing.x) / 10;
                break;
            case 'px':
            default:
                realDistance = pixelDistance;
                break;
        }
        
        return realDistance;
    }

    calculateHounsfieldInEllipse(ellipse) {
        if (!this.currentImageData) return null;
        
        // This is a simplified calculation
        // In a real implementation, you'd need access to the raw DICOM data
        const centerX = Math.floor(ellipse.centerX);
        const centerY = Math.floor(ellipse.centerY);
        
        // Sample points within ellipse
        let sum = 0;
        let count = 0;
        let min = Infinity;
        let max = -Infinity;
        
        for (let x = centerX - ellipse.radiusX; x <= centerX + ellipse.radiusX; x++) {
            for (let y = centerY - ellipse.radiusY; y <= centerY + ellipse.radiusY; y++) {
                // Check if point is inside ellipse
                const dx = (x - centerX) / ellipse.radiusX;
                const dy = (y - centerY) / ellipse.radiusY;
                
                if (dx * dx + dy * dy <= 1) {
                    // Get pixel value (this would need to be actual Hounsfield units)
                    const pixelIndex = (y * this.canvas.width + x) * 4;
                    if (pixelIndex < this.currentImageData.data.length) {
                        const value = this.currentImageData.data[pixelIndex]; // Simplified
                        sum += value;
                        count++;
                        min = Math.min(min, value);
                        max = Math.max(max, value);
                    }
                }
            }
        }
        
        return {
            mean: count > 0 ? sum / count : 0,
            min: min === Infinity ? 0 : min,
            max: max === -Infinity ? 0 : max,
            count: count
        };
    }

    switch3DMode(mode) {
        this.current3DMode = mode;
        
        if (!mode) {
            this.hide3DViewport();
            return;
        }
        
        this.show3DViewport();
        
        switch(mode) {
            case 'mpr':
                this.initMPR();
                break;
            case '3d-bone':
                this.init3DBone();
                break;
            case 'angio':
                this.initAngio();
                break;
            case 'virtual-surgery':
                this.initVirtualSurgery();
                break;
        }
    }

    show3DViewport() {
        const viewport3D = document.getElementById('viewport-3d');
        if (viewport3D) {
            viewport3D.style.display = 'block';
        }
    }

    hide3DViewport() {
        const viewport3D = document.getElementById('viewport-3d');
        if (viewport3D) {
            viewport3D.style.display = 'none';
        }
    }

    initMPR() {
        // Multi-planar reconstruction implementation
        console.log('Initializing MPR view...');
        // This would integrate with a proper MPR library
    }

    init3DBone() {
        // 3D bone visualization implementation
        console.log('Initializing 3D Bone view...');
        // This would use volume rendering techniques
    }

    initAngio() {
        // Angiography reconstruction implementation
        console.log('Initializing Angio reconstruction...');
        // This would use MIP (Maximum Intensity Projection) techniques
    }

    initVirtualSurgery() {
        // Virtual surgery implementation with AI
        console.log('Initializing Virtual Surgery mode...');
        this.aiChat.openSurgeryMode();
        // This would enable AI-assisted surgical planning
    }

    pan(deltaX, deltaY) {
        this.offsetX += deltaX;
        this.offsetY += deltaY;
        this.redraw();
    }

    zoomAt(x, y, factor) {
        const oldZoom = this.zoom;
        this.zoom *= factor;
        this.zoom = Math.max(0.1, Math.min(10, this.zoom));
        
        const zoomChange = this.zoom / oldZoom;
        this.offsetX = x - (x - this.offsetX) * zoomChange;
        this.offsetY = y - (y - this.offsetY) * zoomChange;
        
        this.redraw();
    }

    redraw() {
        if (!this.ctx || !this.currentImageData) return;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw image
        this.ctx.save();
        this.ctx.translate(this.offsetX, this.offsetY);
        this.ctx.scale(this.zoom, this.zoom);
        this.ctx.putImageData(this.currentImageData, 0, 0);
        this.ctx.restore();
        
        // Draw measurements
        this.drawMeasurements();
        
        // Draw annotations
        this.drawAnnotations();
        
        // Draw current measurement/ellipse
        if (this.currentMeasurement) {
            this.drawCurrentMeasurement();
        }
        if (this.currentEllipse) {
            this.drawCurrentEllipse();
        }
    }

    drawMeasurements() {
        this.ctx.save();
        this.ctx.strokeStyle = '#FF0000';
        this.ctx.fillStyle = '#FF0000';
        this.ctx.lineWidth = 2;
        this.ctx.font = '14px Arial';
        
        for (let measurement of this.measurements) {
            if (measurement.type === 'line') {
                this.ctx.beginPath();
                this.ctx.moveTo(measurement.startX, measurement.startY);
                this.ctx.lineTo(measurement.endX, measurement.endY);
                this.ctx.stroke();
                
                // Draw distance label
                const midX = (measurement.startX + measurement.endX) / 2;
                const midY = (measurement.startY + measurement.endY) / 2;
                const distance = measurement.distance.toFixed(2);
                this.ctx.fillText(`${distance} ${measurement.unit}`, midX + 5, midY - 5);
                
            } else if (measurement.type === 'ellipse') {
                this.ctx.beginPath();
                this.ctx.ellipse(
                    measurement.centerX,
                    measurement.centerY,
                    measurement.radiusX,
                    measurement.radiusY,
                    0, 0, 2 * Math.PI
                );
                this.ctx.stroke();
                
                // Draw Hounsfield info
                if (measurement.hounsfield) {
                    const hf = measurement.hounsfield;
                    const text = `HU: ${hf.mean.toFixed(1)} (${hf.min}-${hf.max})`;
                    this.ctx.fillText(text, measurement.centerX + 5, measurement.centerY + 5);
                }
            }
        }
        
        this.ctx.restore();
    }

    drawAnnotations() {
        this.ctx.save();
        
        for (let annotation of this.annotations) {
            this.ctx.fillStyle = annotation.color || '#FFD700';
            this.ctx.font = `${annotation.fontSize || 16}px Arial`;
            
            // Draw background for better readability
            const metrics = this.ctx.measureText(annotation.text);
            const bgWidth = metrics.width + 10;
            const bgHeight = annotation.fontSize + 10;
            
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            this.ctx.fillRect(annotation.x - 5, annotation.y - annotation.fontSize - 5, bgWidth, bgHeight);
            
            // Draw text
            this.ctx.fillStyle = annotation.color || '#FFD700';
            this.ctx.fillText(annotation.text, annotation.x, annotation.y);
            
            // Draw selection indicator if selected
            if (this.selectedAnnotation === annotation) {
                this.ctx.strokeStyle = '#00FF00';
                this.ctx.lineWidth = 2;
                this.ctx.strokeRect(annotation.x - 5, annotation.y - annotation.fontSize - 5, bgWidth, bgHeight);
            }
        }
        
        this.ctx.restore();
    }

    drawCurrentMeasurement() {
        if (!this.currentMeasurement) return;
        
        this.ctx.save();
        this.ctx.strokeStyle = '#FFFF00';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([5, 5]);
        
        this.ctx.beginPath();
        this.ctx.moveTo(this.currentMeasurement.startX, this.currentMeasurement.startY);
        this.ctx.lineTo(this.currentMeasurement.endX, this.currentMeasurement.endY);
        this.ctx.stroke();
        
        this.ctx.restore();
    }

    drawCurrentEllipse() {
        if (!this.currentEllipse) return;
        
        this.ctx.save();
        this.ctx.strokeStyle = '#FFFF00';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([5, 5]);
        
        this.ctx.beginPath();
        this.ctx.ellipse(
            this.currentEllipse.centerX,
            this.currentEllipse.centerY,
            this.currentEllipse.radiusX,
            this.currentEllipse.radiusY,
            0, 0, 2 * Math.PI
        );
        this.ctx.stroke();
        
        this.ctx.restore();
    }

    updateMeasurementDisplays() {
        // Update all existing measurements to new unit
        for (let measurement of this.measurements) {
            if (measurement.type === 'line') {
                const pixelDistance = Math.sqrt(
                    Math.pow(measurement.endX - measurement.startX, 2) + 
                    Math.pow(measurement.endY - measurement.startY, 2)
                );
                measurement.distance = this.convertPixelsToUnit(pixelDistance);
                measurement.unit = this.measurementUnit;
            }
        }
        this.redraw();
        this.updateMeasurementList();
    }

    convertPixelsToUnit(pixels) {
        switch(this.measurementUnit) {
            case 'mm':
                return pixels * this.pixelSpacing.x;
            case 'cm':
                return (pixels * this.pixelSpacing.x) / 10;
            case 'px':
            default:
                return pixels;
        }
    }

    updateMeasurementList() {
        const measurementList = document.getElementById('measurement-list');
        if (!measurementList) return;
        
        measurementList.innerHTML = '';
        
        this.measurements.forEach((measurement, index) => {
            const item = document.createElement('div');
            item.className = 'measurement-item';
            
            if (measurement.type === 'line') {
                item.innerHTML = `
                    <span class="measurement-type">Distance</span>
                    <span class="measurement-value">${measurement.distance.toFixed(2)} ${measurement.unit}</span>
                    <button onclick="dicomViewer.removeMeasurement(${index})" class="remove-btn">×</button>
                `;
            } else if (measurement.type === 'ellipse') {
                const hf = measurement.hounsfield;
                item.innerHTML = `
                    <span class="measurement-type">ROI (Ellipse)</span>
                    <span class="measurement-value">HU: ${hf ? hf.mean.toFixed(1) : 'N/A'}</span>
                    <span class="measurement-details">Min: ${hf ? hf.min.toFixed(1) : 'N/A'} Max: ${hf ? hf.max.toFixed(1) : 'N/A'}</span>
                    <button onclick="dicomViewer.removeMeasurement(${index})" class="remove-btn">×</button>
                `;
            }
            
            measurementList.appendChild(item);
        });
    }

    removeMeasurement(index) {
        this.measurements.splice(index, 1);
        this.redraw();
        this.updateMeasurementList();
    }

    handleFileUpload(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Show loading
        this.showNotification('Loading DICOM file...', 'info');
        
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                this.loadDicomFile(event.target.result);
            } catch (error) {
                this.showNotification('Error loading DICOM file: ' + error.message, 'error');
            }
        };
        reader.readAsArrayBuffer(file);
    }

    loadDicomFile(arrayBuffer) {
        // This would use a DICOM parsing library like cornerstone.js or dicom-parser
        // For now, we'll simulate loading
        console.log('Loading DICOM file...');
        this.showNotification('DICOM file loaded successfully', 'success');
    }

    loadStudyData() {
        const urlParams = new URLSearchParams(window.location.search);
        this.studyId = urlParams.get('study_id');
        this.seriesId = urlParams.get('series_id');
        
        if (this.studyId) {
            this.fetchStudyImages();
        }
    }

    fetchStudyImages() {
        fetch(`/api/studies/${this.studyId}/images/`)
            .then(response => response.json())
            .then(data => {
                this.loadImages(data);
            })
            .catch(error => {
                console.error('Error loading study images:', error);
                this.showNotification('Error loading study images', 'error');
            });
    }

    loadImages(imageData) {
        // Load and display images
        console.log('Loading images:', imageData);
    }

    resizeCanvas() {
        if (!this.canvas) return;
        
        const container = this.canvas.parentElement;
        this.canvas.width = container.clientWidth;
        this.canvas.height = container.clientHeight;
        
        this.redraw();
    }

    isRadiologistOrAdmin() {
        const userRole = document.body.dataset.userRole;
        return userRole === 'radiologist' || userRole === 'admin';
    }

    checkForNewUploads() {
        fetch('/api/check-new-uploads/')
            .then(response => response.json())
            .then(data => {
                if (data.new_uploads && data.new_uploads.length > 0) {
                    this.showNewUploadNotifications(data.new_uploads);
                }
            })
            .catch(error => {
                console.error('Error checking for new uploads:', error);
            });
    }

    showNewUploadNotifications(uploads) {
        uploads.forEach(upload => {
            this.showNotification(
                `New upload from ${upload.facility}: ${upload.patient_name}`,
                'info',
                () => {
                    window.open(`/worklist/?study_id=${upload.study_id}`, '_blank');
                }
            );
        });
    }

    showNotification(message, type = 'info', action = null) {
        const notificationArea = document.getElementById('notification-area');
        if (!notificationArea) return;
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                ${action ? '<button class="notification-action">View</button>' : ''}
                <button class="notification-close">×</button>
            </div>
        `;
        
        // Add event listeners
        if (action) {
            notification.querySelector('.notification-action').addEventListener('click', action);
        }
        
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        notificationArea.appendChild(notification);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 10000);
    }
}

// AI Chat functionality
class AIChat {
    constructor() {
        this.isOpen = false;
        this.chatHistory = [];
        this.surgeryMode = false;
    }

    toggle() {
        this.isOpen = !this.isOpen;
        const chatPanel = document.getElementById('ai-chat-panel');
        if (chatPanel) {
            chatPanel.style.display = this.isOpen ? 'flex' : 'none';
        }
    }

    openSurgeryMode() {
        this.surgeryMode = true;
        this.isOpen = true;
        const chatPanel = document.getElementById('ai-chat-panel');
        if (chatPanel) {
            chatPanel.style.display = 'flex';
            chatPanel.classList.add('surgery-mode');
        }
        this.sendMessage('Virtual surgery mode activated. I can help analyze anatomy and suggest surgical approaches.');
    }

    sendMessage(message, isUser = false) {
        const chatMessages = document.getElementById('ai-chat-messages');
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user' : 'ai'}`;
        messageDiv.innerHTML = `
            <div class="message-content">${message}</div>
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        if (isUser) {
            // Simulate AI response
            setTimeout(() => {
                this.generateAIResponse(message);
            }, 1000);
        }
    }

    generateAIResponse(userMessage) {
        let response = "I'm analyzing the image data. ";
        
        if (this.surgeryMode) {
            response += "Based on the anatomical structures visible, I recommend careful consideration of the vascular architecture in this region.";
        } else {
            response += "I can help you with image analysis, measurement interpretation, and diagnostic suggestions.";
        }
        
        this.sendMessage(response, false);
    }
}

// Worklist functionality
class WorklistManager {
    constructor() {
        this.currentFacility = null;
        this.patients = [];
        this.selectedPatient = null;
        this.init();
    }

    init() {
        this.loadPatients();
        this.setupEventListeners();
        this.setupSearch();
    }

    setupEventListeners() {
        // Patient row clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.patient-row')) {
                this.selectPatient(e.target.closest('.patient-row'));
            }
        });
        
        // View button clicks
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-view')) {
                const patientId = e.target.dataset.patientId;
                this.viewPatient(patientId);
            }
        });
        
        // Print button clicks
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-print')) {
                const patientId = e.target.dataset.patientId;
                this.printReport(patientId);
            }
        });
    }

    setupSearch() {
        const searchInput = document.getElementById('patient-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterPatients(e.target.value);
            });
        }
    }

    loadPatients() {
        fetch('/api/worklist/patients/')
            .then(response => response.json())
            .then(data => {
                this.patients = data.patients;
                this.renderPatients();
            })
            .catch(error => {
                console.error('Error loading patients:', error);
            });
    }

    renderPatients() {
        const tbody = document.getElementById('patients-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        this.patients.forEach(patient => {
            const row = this.createPatientRow(patient);
            tbody.appendChild(row);
        });
    }

    createPatientRow(patient) {
        const row = document.createElement('tr');
        row.className = 'patient-row';
        row.dataset.patientId = patient.id;
        
        row.innerHTML = `
            <td>${patient.patient_id}</td>
            <td>${patient.name}</td>
            <td>${patient.birth_date}</td>
            <td>${patient.gender}</td>
            <td>${patient.study_date}</td>
            <td>${patient.modality}</td>
            <td><span class="status ${patient.status}">${patient.status}</span></td>
            <td>
                <button class="btn btn-view" data-patient-id="${patient.id}">
                    <i class="fas fa-eye"></i> View
                </button>
                ${this.canPrintReport() ? `
                    <button class="btn btn-print" data-patient-id="${patient.id}">
                        <i class="fas fa-print"></i> Print
                    </button>
                ` : ''}
            </td>
        `;
        
        return row;
    }

    selectPatient(row) {
        // Remove previous selection
        document.querySelectorAll('.patient-row').forEach(r => {
            r.classList.remove('selected');
        });
        
        // Add selection to clicked row
        row.classList.add('selected');
        
        const patientId = row.dataset.patientId;
        this.selectedPatient = this.patients.find(p => p.id == patientId);
        
        // Show patient details
        this.showPatientDetails(this.selectedPatient);
    }

    showPatientDetails(patient) {
        const detailsPanel = document.getElementById('patient-details');
        if (!detailsPanel) return;
        
        detailsPanel.style.display = 'block';
        detailsPanel.innerHTML = `
            <h3>Patient Details</h3>
            <div class="detail-group">
                <label>Patient ID:</label>
                <span>${patient.patient_id}</span>
            </div>
            <div class="detail-group">
                <label>Name:</label>
                <span>${patient.name}</span>
            </div>
            <div class="detail-group">
                <label>Birth Date:</label>
                <span>${patient.birth_date}</span>
            </div>
            <div class="detail-group">
                <label>Study Date:</label>
                <span>${patient.study_date}</span>
            </div>
            <div class="detail-group">
                <label>Clinical Information:</label>
                <textarea id="clinical-info" placeholder="Add clinical information...">${patient.clinical_info || ''}</textarea>
                <button onclick="worklistManager.saveClinicalInfo()" class="btn btn-save">Save</button>
            </div>
            ${this.canWriteReport() ? `
                <div class="detail-group">
                    <label>Report:</label>
                    <textarea id="report-text" placeholder="Write report...">${patient.report || ''}</textarea>
                    <button onclick="worklistManager.saveReport()" class="btn btn-save">Save Report</button>
                </div>
            ` : ''}
        `;
    }

    viewPatient(patientId) {
        const patient = this.patients.find(p => p.id == patientId);
        if (patient) {
            window.open(`/viewer/?study_id=${patient.study_id}`, '_blank');
        }
    }

    printReport(patientId) {
        const patient = this.patients.find(p => p.id == patientId);
        if (patient) {
            window.open(`/reports/print/${patient.id}/`, '_blank');
        }
    }

    filterPatients(searchTerm) {
        const filteredPatients = this.patients.filter(patient => 
            patient.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            patient.patient_id.toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        const tbody = document.getElementById('patients-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        filteredPatients.forEach(patient => {
            const row = this.createPatientRow(patient);
            tbody.appendChild(row);
        });
    }

    saveClinicalInfo() {
        if (!this.selectedPatient) return;
        
        const clinicalInfo = document.getElementById('clinical-info').value;
        
        fetch(`/api/patients/${this.selectedPatient.id}/clinical-info/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({ clinical_info: clinicalInfo })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showNotification('Clinical information saved', 'success');
            }
        })
        .catch(error => {
            console.error('Error saving clinical info:', error);
            this.showNotification('Error saving clinical information', 'error');
        });
    }

    saveReport() {
        if (!this.selectedPatient) return;
        
        const reportText = document.getElementById('report-text').value;
        
        fetch(`/api/patients/${this.selectedPatient.id}/report/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({ report: reportText })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showNotification('Report saved', 'success');
            }
        })
        .catch(error => {
            console.error('Error saving report:', error);
            this.showNotification('Error saving report', 'error');
        });
    }

    canPrintReport() {
        const userRole = document.body.dataset.userRole;
        return userRole === 'radiologist' || userRole === 'admin' || userRole === 'facility';
    }

    canWriteReport() {
        const userRole = document.body.dataset.userRole;
        return userRole === 'radiologist' || userRole === 'admin';
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    showNotification(message, type) {
        // Reuse the notification system from DicomViewer
        const notificationArea = document.getElementById('notification-area');
        if (!notificationArea) return;
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close">×</button>
            </div>
        `;
        
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        notificationArea.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

// Global instances
let dicomViewer;
let worklistManager;

// Initialize based on page
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('dicom-canvas')) {
        dicomViewer = new DicomViewer();
    }
    
    if (document.getElementById('patients-tbody')) {
        worklistManager = new WorklistManager();
    }
});