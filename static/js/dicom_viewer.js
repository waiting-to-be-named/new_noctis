// static/js/dicom_viewer.js

class DicomViewer {
    constructor(initialStudyId = null) {
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
        
        // Store initial study ID
        this.initialStudyId = initialStudyId;
        
        this.init();
    }
    
    async init() {
        this.setupCanvas();
        this.setupEventListeners();
        await this.loadBackendStudies();
        this.setupNotifications();
        this.setupMeasurementUnitSelector();
        this.setup3DControls();
        this.setupAIPanel();
        
        // Load initial study if provided
        if (this.initialStudyId) {
            console.log('Loading initial study:', this.initialStudyId);
            await this.loadStudy(this.initialStudyId);
        }
    }
    
    setupCanvas() {
        // Set canvas size
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    resizeCanvas() {
        const viewport = document.querySelector('.viewport');
        if (viewport) {
            // Use devicePixelRatio for high-DPI displays
            const devicePixelRatio = window.devicePixelRatio || 1;
            const displayWidth = viewport.clientWidth;
            const displayHeight = viewport.clientHeight;
            
            this.canvas.width = displayWidth * devicePixelRatio;
            this.canvas.height = displayHeight * devicePixelRatio;
            
            this.canvas.style.width = displayWidth + 'px';
            this.canvas.style.height = displayHeight + 'px';
            
            // Reset the context and scale for high-DPI displays
            this.ctx.setTransform(1, 0, 0, 1, 0, 0);
            this.ctx.scale(devicePixelRatio, devicePixelRatio);
            
            this.redraw();
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
        
        // Worklist button
        const worklistBtn = document.getElementById('worklist-btn');
        if (worklistBtn) {
            worklistBtn.addEventListener('click', () => {
                window.location.href = '/worklist/';
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
        
        // Worklist button
        document.getElementById('worklist-btn').addEventListener('click', () => {
            window.location.href = '/worklist/';
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
        const hiddenFileInput = document.getElementById('hidden-file-input');
        
        // Close modal
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        // Close modal when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            this.uploadFiles(e.target.files);
        });
        
        // Hidden file input for directory upload
        hiddenFileInput.addEventListener('change', (e) => {
            this.uploadFolder(e.target.files);
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
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                // Check if this looks like a folder upload (multiple files with similar paths)
                const filePaths = Array.from(files).map(f => f.webkitRelativePath || f.name);
                const hasSubdirectories = filePaths.some(path => path.includes('/'));
                
                if (hasSubdirectories || files.length > 5) {
                    // Treat as folder upload
                    this.uploadFolder(files);
                } else {
                    // Treat as individual file upload
                    this.uploadFiles(files);
                }
            }
        });
        
        // Click to select files
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });
        
        // Add directory upload button
        const uploadAreaContent = uploadArea.innerHTML;
        uploadArea.innerHTML = `
            ${uploadAreaContent}
            <div class="upload-buttons">
                <button type="button" class="upload-btn" id="select-files-btn">
                    <i class="fas fa-file"></i>
                    Select Files
                </button>
                <button type="button" class="upload-btn" id="select-folder-btn">
                    <i class="fas fa-folder"></i>
                    Select Folder
                </button>
            </div>
        `;
        
        // Add event listeners for buttons
        document.getElementById('select-files-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
        
        document.getElementById('select-folder-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            hiddenFileInput.setAttribute('webkitdirectory', '');
            hiddenFileInput.setAttribute('directory', '');
            hiddenFileInput.click();
        });
    }
    
    showUploadModal() {
        document.getElementById('upload-modal').style.display = 'flex';
    }
    
    async uploadFiles(files) {
        if (!files || files.length === 0) {
            alert('Please select DICOM files to upload');
            return;
        }
        
        // Validate files before upload
        const validFiles = Array.from(files).filter(file => {
            const fileName = file.name.toLowerCase();
            const fileSize = file.size;
            
            // Check file size (100MB limit)
            if (fileSize > 100 * 1024 * 1024) {
                alert(`File ${file.name} is too large (max 100MB)`);
                return false;
            }
            
            // Accept various DICOM formats
            const isDicomCandidate = (
                fileName.endsWith('.dcm') ||
                fileName.endsWith('.dicom') ||
                fileName.endsWith('.dcm.gz') ||
                fileName.endsWith('.dicom.gz') ||
                fileName.endsWith('.dcm.bz2') ||
                fileName.endsWith('.dicom.bz2') ||
                fileName.endsWith('.img') ||
                fileName.endsWith('.ima') ||
                fileName.endsWith('.raw') ||
                !fileName.includes('.') ||  // Files without extension
                fileSize > 1024  // Files larger than 1KB
            );
            
            if (!isDicomCandidate) {
                console.warn(`File ${file.name} may not be a DICOM file`);
            }
            
            return true; // Accept all files and let server handle validation
        });
        
        if (validFiles.length === 0) {
            alert('No valid files selected for upload');
            return;
        }
        
        const formData = new FormData();
        validFiles.forEach(file => {
            formData.append('files', file);
        });
        
        const progressDiv = document.getElementById('upload-progress');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        progressDiv.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = `Uploading ${validFiles.length} files...`;
        
        try {
            const response = await fetch('/viewer/api/upload/', {
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
                
                // Show warnings if any
                if (result.warnings && result.warnings.length > 0) {
                    console.warn('Upload warnings:', result.warnings);
                    setTimeout(() => {
                        alert(`Upload completed with warnings:\n${result.warnings.join('\n')}`);
                    }, 500);
                }
                
                setTimeout(() => {
                    document.getElementById('upload-modal').style.display = 'none';
                    progressDiv.style.display = 'none';
                    
                    if (result.study_id) {
                        this.loadStudy(result.study_id);
                        // Refresh the studies list
                        this.loadBackendStudies();
                    }
                    
                    // Show success message
                    if (result.uploaded_files && result.uploaded_files.length > 0) {
                        const message = `Successfully uploaded ${result.uploaded_files.length} DICOM file(s)`;
                        if (result.warnings && result.warnings.length > 0) {
                            alert(message + '\n\nSome files had issues but were processed successfully.');
                        } else {
                            alert(message);
                        }
                    }
                }, 1000);
            } else {
                // Enhanced error handling
                let errorMessage = 'Upload failed';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || 'Upload failed';
                    
                    // Handle specific error types
                    if (errorData.error_type === 'validation_error') {
                        errorMessage = 'File validation failed: ' + errorMessage;
                    } else if (errorData.error_type === 'csrf_error') {
                        errorMessage = 'Security token error. Please refresh the page and try again.';
                    }
                } catch (parseError) {
                    console.error('Failed to parse error response:', parseError);
                    // Try to get response text
                    try {
                        const responseText = await response.text();
                        console.error('Response text:', responseText);
                        
                        // Check if it's HTML error page
                        if (responseText.includes('<!DOCTYPE') || responseText.includes('<html')) {
                            errorMessage = `Server returned HTML error (${response.status}). Please try again.`;
                        } else {
                            errorMessage = `Server error (${response.status}): ${responseText.substring(0, 200)}`;
                        }
                    } catch (textError) {
                        errorMessage = `Server error (${response.status}). Please try again.`;
                    }
                }
                
                throw new Error(errorMessage);
            }
        } catch (error) {
            progressText.textContent = 'Upload failed: ' + error.message;
            console.error('Upload error:', error);
            
            // Show error message to user
            setTimeout(() => {
                alert('Upload failed: ' + error.message);
                progressDiv.style.display = 'none';
            }, 2000);
        }
    }
    
    async uploadFolder(files) {
        if (!files || files.length === 0) {
            alert('Please select a folder containing DICOM files');
            return;
        }
        
        // Enhanced DICOM file filtering
        const dicomFiles = Array.from(files).filter(file => {
            const fileName = file.name.toLowerCase();
            const fileSize = file.size;
            
            // Check file size (100MB limit)
            if (fileSize > 100 * 1024 * 1024) {
                console.warn(`File ${file.name} is too large (max 100MB)`);
                return false;
            }
            
            // Accept various DICOM formats
            const isDicomCandidate = (
                fileName.endsWith('.dcm') ||
                fileName.endsWith('.dicom') ||
                fileName.endsWith('.dcm.gz') ||
                fileName.endsWith('.dicom.gz') ||
                fileName.endsWith('.dcm.bz2') ||
                fileName.endsWith('.dicom.bz2') ||
                fileName.endsWith('.img') ||
                fileName.endsWith('.ima') ||
                fileName.endsWith('.raw') ||
                !fileName.includes('.') ||  // Files without extension
                fileSize > 1024  // Files larger than 1KB
            );
            
            return isDicomCandidate;
        });
        
        if (dicomFiles.length === 0) {
            alert('No DICOM files found in the selected folder. Please ensure the folder contains DICOM files (.dcm, .dicom, .img, .ima, etc.)');
            return;
        }
        
        const formData = new FormData();
        dicomFiles.forEach(file => {
            formData.append('files', file);
        });
        
        const progressDiv = document.getElementById('upload-progress');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        progressDiv.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = `Uploading ${dicomFiles.length} DICOM files...`;
        
        try {
            const response = await fetch('/viewer/api/upload-folder/', {
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
                
                // Show warnings if any
                if (result.warnings && result.warnings.length > 0) {
                    console.warn('Upload warnings:', result.warnings);
                    setTimeout(() => {
                        alert(`Upload completed with warnings:\n${result.warnings.join('\n')}`);
                    }, 500);
                }
                
                setTimeout(() => {
                    document.getElementById('upload-modal').style.display = 'none';
                    progressDiv.style.display = 'none';
                    
                    if (result.study_id) {
                        this.loadStudy(result.study_id);
                        // Refresh the studies list
                        this.loadBackendStudies();
                    }
                    
                    // Show success message
                    if (result.uploaded_files && result.uploaded_files.length > 0) {
                        const message = `Successfully uploaded ${result.uploaded_files.length} DICOM files from ${result.message.split(' ')[-2]} study(ies)`;
                        if (result.warnings && result.warnings.length > 0) {
                            alert(message + '\n\nSome files had issues but were processed successfully.');
                        } else {
                            alert(message);
                        }
                    }
                }, 1000);
            } else {
                // Enhanced error handling
                let errorMessage = 'Upload failed';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || 'Upload failed';
                    
                    // Handle specific error types
                    if (errorData.error_type === 'validation_error') {
                        errorMessage = 'File validation failed: ' + errorMessage;
                    } else if (errorData.error_type === 'csrf_error') {
                        errorMessage = 'Security token error. Please refresh the page and try again.';
                    }
                } catch (parseError) {
                    console.error('Failed to parse error response:', parseError);
                    // Try to get response text
                    try {
                        const responseText = await response.text();
                        console.error('Response text:', responseText);
                        
                        // Check if it's HTML error page
                        if (responseText.includes('<!DOCTYPE') || responseText.includes('<html')) {
                            errorMessage = `Server returned HTML error (${response.status}). Please try again.`;
                        } else {
                            errorMessage = `Server error (${response.status}): ${responseText.substring(0, 200)}`;
                        }
                    } catch (textError) {
                        errorMessage = `Server error (${response.status}). Please try again.`;
                    }
                }
                
                throw new Error(errorMessage);
            }
        } catch (error) {
            progressText.textContent = 'Upload failed: ' + error.message;
            console.error('Upload error:', error);
            
            // Show error message to user
            setTimeout(() => {
                alert('Upload failed: ' + error.message);
                progressDiv.style.display = 'none';
            }, 2000);
        }
    }
    
    async loadBackendStudies() {
        try {
            const response = await fetch('/viewer/api/studies/');
            const studies = await response.json();
            
            // Store studies for future use (e.g., in a menu or list)
            this.availableStudies = studies;
            
            console.log(`Loaded ${studies.length} studies from backend`);
            
        } catch (error) {
            console.error('Error loading studies:', error);
            this.showError('Failed to load studies from backend');
        }
    }
    
    async loadStudy(studyId) {
        try {
            console.log(`Loading study ${studyId}...`);
            const response = await fetch(`/viewer/api/studies/${studyId}/images/`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (!data.images || data.images.length === 0) {
                throw new Error('No images found in this study');
            }
            
            console.log(`Found ${data.images.length} images in study`);
            
            this.currentStudy = data.study;
            this.currentSeries = data.series || null;
            this.currentImages = data.images;
            this.currentImageIndex = 0;
            
            // Update UI
            this.updatePatientInfo();
            this.updateSliders();
            
            // Load the first image
            await this.loadCurrentImage();
            
            // Study loaded successfully - no need to update selector as it's removed
            
            console.log('Study loaded successfully');
            
        } catch (error) {
            console.error('Error loading study:', error);
            this.showError('Error loading study: ' + error.message);
            // Reset patient info on error
            this.updatePatientInfo();
        }
    }
    
    async loadCurrentImage() {
        if (!this.currentImages.length) {
            console.log('No images available');
            return;
        }
        
        const imageData = this.currentImages[this.currentImageIndex];
        console.log(`Loading image ${this.currentImageIndex + 1}/${this.currentImages.length}, ID: ${imageData.id}`);
        
        try {
            const params = new URLSearchParams({
                window_width: this.windowWidth,
                window_level: this.windowLevel,
                inverted: this.inverted
            });
            
            const response = await fetch(`/viewer/api/images/${imageData.id}/data/?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.image_data) {
                const img = new Image();
                img.onload = () => {
                    console.log('Image loaded successfully');
                    this.currentImage = {
                        image: img,
                        metadata: data.metadata,
                        id: imageData.id,
                        rows: data.metadata.rows,
                        columns: data.metadata.columns,
                        pixel_spacing_x: data.metadata.pixel_spacing_x,
                        pixel_spacing_y: data.metadata.pixel_spacing_y,
                        pixel_spacing: `${data.metadata.pixel_spacing_x},${data.metadata.pixel_spacing_y}`,
                        slice_thickness: data.metadata.slice_thickness
                    };
                    // Ensure canvas is properly sized before drawing
                    this.resizeCanvas();
                    this.updateDisplay();
                    this.loadMeasurements();
                    this.loadAnnotations();
                    this.updatePatientInfo();
                };
                img.onerror = (error) => {
                    console.error('Failed to load image data:', error);
                    console.error('Image source:', img.src);
                    this.showError('Failed to load image. Please try refreshing or selecting another image.');
                };
                img.src = data.image_data;
            } else {
                throw new Error(data.error || 'No image data received');
            }
            
        } catch (error) {
            console.error('Error loading image:', error);
            this.showError('Error loading image: ' + error.message);
        }
    }
    
    showError(message) {
        console.error(message);
        // Create a more user-friendly error display
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <div class="error-content">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff4444;
            color: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            z-index: 1000;
            max-width: 400px;
        `;
        document.body.appendChild(errorDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 5000);
    }
    
    updatePatientInfo() {
        if (!this.currentStudy) {
            const patientInfo = document.getElementById('patient-info');
            if (patientInfo) {
                patientInfo.textContent = 'Patient: - | Study Date: - | Modality: -';
            }
            return;
        }
        
        const patientInfo = document.getElementById('patient-info');
        if (patientInfo) {
            patientInfo.textContent = `Patient: ${this.currentStudy.patient_name} | Study Date: ${this.currentStudy.study_date} | Modality: ${this.currentStudy.modality}`;
        }
        
        // Update image info in right panel if elements exist
        const currentImageData = this.currentImages[this.currentImageIndex];
        if (currentImageData) {
            const infoDimensions = document.getElementById('info-dimensions');
            const infoPixelSpacing = document.getElementById('info-pixel-spacing');
            const infoSeries = document.getElementById('info-series');
            const infoInstitution = document.getElementById('info-institution');
            
            if (infoDimensions) {
                infoDimensions.textContent = `${currentImageData.columns}x${currentImageData.rows}`;
            }
            if (infoPixelSpacing) {
                infoPixelSpacing.textContent = 
                    `${currentImageData.pixel_spacing_x || 'Unknown'}\\${currentImageData.pixel_spacing_y || 'Unknown'}`;
            }
            if (infoSeries) {
                infoSeries.textContent = currentImageData.series_description || 'Unknown';
            }
            if (infoInstitution) {
                infoInstitution.textContent = this.currentStudy.institution_name || 'Unknown';
            }
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
        const scale = this.getScale();
        
        const displayWidth = img.width * scale;
        const displayHeight = img.height * scale;
        // Use display dimensions for positioning
        const canvasDisplayWidth = this.canvas.style.width ? parseInt(this.canvas.style.width) : this.canvas.width;
        const canvasDisplayHeight = this.canvas.style.height ? parseInt(this.canvas.style.height) : this.canvas.height;
        const x = (canvasDisplayWidth - displayWidth) / 2 + this.panX;
        const y = (canvasDisplayHeight - displayHeight) / 2 + this.panY;
        
        // Draw image
        this.ctx.drawImage(img, x, y, displayWidth, displayHeight);
        
        // Update overlay labels
        this.updateOverlayLabels();
    }
    
    // New helper to calculate the current pixel scale while preventing unintended up-scaling
    getScale() {
        if (!this.currentImage) return 1;
        const img = this.currentImage.image;
        // Use the display size (style dimensions) instead of canvas dimensions for scaling
        const displayWidth = this.canvas.style.width ? parseInt(this.canvas.style.width) : this.canvas.width;
        const displayHeight = this.canvas.style.height ? parseInt(this.canvas.style.height) : this.canvas.height;
        const baseScale = Math.min(displayWidth / img.width, displayHeight / img.height);
        const clampedBase = baseScale > 1 ? 1 : baseScale; // never upscale automatically
        return this.zoomFactor * clampedBase;
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
                const text = (typeof measurement.value === 'number' && !isNaN(measurement.value)) ? `${measurement.value.toFixed(1)} HU` : 'HU: -';
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
                const volText = (typeof measurement.value === 'number' && !isNaN(measurement.value)) ? `${measurement.value.toFixed(2)} ${measurement.unit || ''}` : 'Vol: -';
                const textMetrics = this.ctx.measureText(volText);
                this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                this.ctx.fillRect(centroidX - textMetrics.width/2 - 4, centroidY - 8, textMetrics.width + 8, 16);
                this.ctx.fillStyle = 'blue';
                this.ctx.fillText(volText, centroidX - textMetrics.width/2, centroidY + 4);
            } else if (measurement.type === 'line' && coords && coords.length >= 2) {
                // Draw distance/line measurement
                const start = this.imageToCanvasCoords(coords[0].x, coords[0].y);
                const end = this.imageToCanvasCoords(coords[1].x, coords[1].y);
                
                this.ctx.beginPath();
                this.ctx.moveTo(start.x, start.y);
                this.ctx.lineTo(end.x, end.y);
                this.ctx.stroke();
                
                // Draw measurement text
                const midX = (start.x + end.x) / 2;
                const midY = (start.y + end.y) / 2;
                const distanceText = (typeof measurement.value === 'number' && !isNaN(measurement.value)) ? `${measurement.value.toFixed(1)} ${measurement.unit || ''}` : '-';
                const textMetrics = this.ctx.measureText(distanceText);
                
                // Background for text
                this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                this.ctx.fillRect(midX - textMetrics.width/2 - 4, midY - 8, textMetrics.width + 8, 16);
                
                this.ctx.fillStyle = 'red';
                this.ctx.fillText(distanceText, midX - textMetrics.width/2, midY + 4);
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
        // Don't change active state for dropdown tools
        if (tool !== 'ai' && tool !== '3d') {
            // Remove active class from all non-dropdown tool buttons
            document.querySelectorAll('.tool-btn:not(.dropdown-toggle)').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to clicked button
            const clickedBtn = document.querySelector(`[data-tool="${tool}"]`);
            if (clickedBtn && !clickedBtn.classList.contains('dropdown-toggle')) {
                clickedBtn.classList.add('active');
            }
            
            this.activeTool = tool;
        }
        
        // Handle specific tool actions
        switch (tool) {
            case 'windowing':
                this.canvas.style.cursor = 'default';
                break;
            case 'zoom':
                this.canvas.style.cursor = 'zoom-in';
                break;
            case 'pan':
                this.canvas.style.cursor = 'grab';
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
            case 'crosshair':
                this.crosshair = !this.crosshair;
                this.redraw();
                break;
            case 'invert':
                this.inverted = !this.inverted;
                this.updateDisplay();
                break;
            case 'reset':
                this.resetView();
                break;
            case 'volume':
                this.canvas.style.cursor = 'crosshair';
                this.startVolumeCalculation();
                break;
            case 'ai':
                // Dropdown handled by onclick in HTML
                break;
            case '3d':
                // Dropdown handled by onclick in HTML
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
        
        if (this.activeTool === 'windowing') {
            this.isDragging = true;
            this.dragStart = { x, y };
        } else if (this.activeTool === 'pan') {
            this.isDragging = true;
            this.dragStart = { x, y };
        } else if (this.activeTool === 'measure') {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.currentMeasurement = {
                start: imageCoords,
                end: imageCoords,
                type: 'distance'
            };
        } else if (this.activeTool === 'ellipse') {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.currentEllipse = {
                center: imageCoords,
                radius: 0,
                type: 'ellipse'
            };
        } else if (this.activeTool === 'volume') {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.volumeContour.push(imageCoords);
            this.redraw();
        }
    }
    
    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.activeTool === 'windowing' && this.isDragging) {
            const deltaX = x - this.dragStart.x;
            const deltaY = y - this.dragStart.y;
            
            // Adjust window width and level based on mouse movement
            this.windowWidth += deltaX * 2;
            this.windowLevel += deltaY * 2;
            
            // Clamp values
            this.windowWidth = Math.max(1, Math.min(4000, this.windowWidth));
            this.windowLevel = Math.max(-1000, Math.min(1000, this.windowLevel));
            
            this.dragStart = { x, y };
            this.updateSliders();
            this.updateDisplay();
        } else if (this.activeTool === 'pan' && this.isDragging) {
            const deltaX = x - this.dragStart.x;
            const deltaY = y - this.dragStart.y;
            
            this.panX += deltaX;
            this.panY += deltaY;
            
            this.dragStart = { x, y };
            this.redraw();
        } else if (this.activeTool === 'measure' && this.currentMeasurement) {
            const imageCoords = this.canvasToImageCoords(x, y);
            this.currentMeasurement.end = imageCoords;
            this.redraw();
        } else if (this.activeTool === 'ellipse' && this.currentEllipse) {
            const imageCoords = this.canvasToImageCoords(x, y);
            const dx = imageCoords.x - this.currentEllipse.center.x;
            const dy = imageCoords.y - this.currentEllipse.center.y;
            this.currentEllipse.radius = Math.sqrt(dx * dx + dy * dy);
            this.redraw();
        }
        
        // Update crosshair position
        if (this.crosshair) {
            const crosshair = document.getElementById('crosshair');
            if (crosshair) {
                crosshair.style.left = x + 'px';
                crosshair.style.top = y + 'px';
                crosshair.style.display = 'block';
            }
        }
    }
    
    onMouseUp(e) {
        if (this.activeTool === 'windowing' || this.activeTool === 'pan') {
            this.isDragging = false;
            this.dragStart = null;
        } else if (this.activeTool === 'measure' && this.currentMeasurement) {
            // Persist the measurement using the dedicated handler
            const measurementData = {
                start: this.currentMeasurement.start,
                end: this.currentMeasurement.end
            };
            this.addMeasurement(measurementData);
            this.currentMeasurement = null;
            this.redraw();
        } else if (this.activeTool === 'ellipse' && this.currentEllipse) {
            this.measurements.push(this.currentEllipse);
            this.updateMeasurementsList();
            this.currentEllipse = null;
            this.redraw();
        }
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
        if (this.activeTool === 'volume' && this.volumeContour.length >= 3) {
            this.calculateVolumeFromContour();
        }
    }
    
    // Coordinate conversion
    imageToCanvasCoords(imageX, imageY) {
        if (!this.currentImage) return { x: 0, y: 0 };
        
        const img = this.currentImage.image;
        const scale = this.getScale();
        
        const displayWidth = img.width * scale;
        const displayHeight = img.height * scale;
        // Use display dimensions for offset calculation
        const canvasDisplayWidth = this.canvas.style.width ? parseInt(this.canvas.style.width) : this.canvas.width;
        const canvasDisplayHeight = this.canvas.style.height ? parseInt(this.canvas.style.height) : this.canvas.height;
        const offsetX = (canvasDisplayWidth - displayWidth) / 2 + this.panX;
        const offsetY = (canvasDisplayHeight - displayHeight) / 2 + this.panY;
        
        return {
            x: offsetX + (imageX * scale),
            y: offsetY + (imageY * scale)
        };
    }
    
    canvasToImageCoords(canvasX, canvasY) {
        if (!this.currentImage) return { x: 0, y: 0 };
        
        const img = this.currentImage.image;
        const scale = this.getScale();
        
        const displayWidth = img.width * scale;
        const displayHeight = img.height * scale;
        // Use display dimensions for offset calculation
        const canvasDisplayWidth = this.canvas.style.width ? parseInt(this.canvas.style.width) : this.canvas.width;
        const canvasDisplayHeight = this.canvas.style.height ? parseInt(this.canvas.style.height) : this.canvas.height;
        const offsetX = (canvasDisplayWidth - displayWidth) / 2 + this.panX;
        const offsetY = (canvasDisplayHeight - displayHeight) / 2 + this.panY;
        
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
            const response = await fetch('/viewer/api/measurements/save/', {
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
            const response = await fetch('/viewer/api/annotations/save/', {
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
            const response = await fetch(`/viewer/api/images/${this.currentImage.id}/measurements/`);
            this.measurements = await response.json();
            this.updateMeasurementsList();
        } catch (error) {
            console.error('Error loading measurements:', error);
        }
    }
    
    async loadAnnotations() {
        if (!this.currentImage) return;
        
        try {
            const response = await fetch(`/viewer/api/images/${this.currentImage.id}/annotations/`);
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
            
            const hasNumericValue = typeof measurement.value === 'number' && !isNaN(measurement.value);
            const safeValue = hasNumericValue ? measurement.value : null;
            const minVal = typeof measurement.hounsfield_min === 'number' ? measurement.hounsfield_min : null;
            const maxVal = typeof measurement.hounsfield_max === 'number' ? measurement.hounsfield_max : null;
            
            switch(measurement.type) {
                case 'ellipse':
                    typeText = 'HU Analysis';
                    if (safeValue !== null) {
                        displayText = `${safeValue.toFixed(1)} HU`;
                    } else {
                        displayText = '-';
                    }
                    if (minVal !== null && maxVal !== null) {
                        displayText += ` (${minVal.toFixed(1)} - ${maxVal.toFixed(1)})`;
                    }
                    if (measurement.notes) {
                        displayText += ` - ${measurement.notes}`;
                    }
                    break;
                case 'volume':
                    typeText = 'Volume';
                    displayText = safeValue !== null ? `${safeValue.toFixed(2)} ${measurement.unit || ''}` : '-';
                    break;
                case 'line':
                    typeText = 'Distance';
                    displayText = safeValue !== null ? `${safeValue.toFixed(1)} ${measurement.unit || ''}` : '-';
                    break;
                case 'area':
                    typeText = 'Area';
                    displayText = safeValue !== null ? `${safeValue.toFixed(2)} ${measurement.unit || ''}` : '-';
                    break;
                case 'angle':
                    typeText = 'Angle';
                    displayText = safeValue !== null ? `${safeValue.toFixed(1)}°` : '-';
                    break;
                default:
                    typeText = 'Measurement';
                    displayText = safeValue !== null ? `${safeValue.toFixed(1)} ${measurement.unit || ''}` : '-';
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
            const response = await fetch(`/viewer/api/images/${this.currentImage.id}/clear-measurements/`, {
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
            const response = await fetch('/viewer/api/measurements/hu/', {
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
    
    startVolumeCalculation() {
        this.volumeTool = true;
        this.volumeContour = [];
        this.currentContour = null;
        alert('Volume measurement: Click to create a closed contour around the region to measure volume. Double-click to complete the contour.');
    }
    
    async calculateVolumeFromContour() {
        if (this.volumeContour.length < 3) {
            alert('At least 3 points are required for volume calculation');
            return;
        }
        
        try {
            const response = await fetch('/viewer/api/volume/calculate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    contour_points: this.volumeContour,
                    pixel_spacing: this.currentImage ? this.parsePixelSpacing(this.currentImage.pixel_spacing) : [1.0, 1.0],
                    slice_thickness: this.currentImage ? this.currentImage.slice_thickness : 1.0
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                alert(`Volume Calculation Results:\nArea: ${result.area_mm2} mm²\nVolume: ${result.volume_mm3} mm³ (${result.volume_ml} ml)`);
                
                // Save volume measurement
                this.saveVolumeMeasurement(result);
            } else {
                const error = await response.json();
                alert('Volume calculation failed: ' + error.error);
            }
        } catch (error) {
            console.error('Volume calculation error:', error);
            alert('Volume calculation failed: ' + error.message);
        }
    }
    
    parsePixelSpacing(pixelSpacingStr) {
        if (!pixelSpacingStr) return [1.0, 1.0];
        try {
            const spacing = pixelSpacingStr.split(',');
            return [parseFloat(spacing[0]), parseFloat(spacing[1])];
        } catch (e) {
            return [1.0, 1.0];
        }
    }
    
    saveVolumeMeasurement(volumeData) {
        const measurement = {
            type: 'volume',
            volume_mm3: volumeData.volume_mm3,
            volume_ml: volumeData.volume_ml,
            area_mm2: volumeData.area_mm2,
            contour_points: this.volumeContour,
            timestamp: new Date().toISOString()
        };
        
        this.measurements.push(measurement);
        this.updateMeasurementsList();
    }
    
    drawVolumeContour() {
        if (this.volumeContour.length === 0) return;
        
        this.ctx.strokeStyle = '#00FF00';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        
        for (let i = 0; i < this.volumeContour.length; i++) {
            const point = this.volumeContour[i];
            const canvasPoint = this.imageToCanvasCoords(point.x, point.y);
            
            if (i === 0) {
                this.ctx.moveTo(canvasPoint.x, canvasPoint.y);
            } else {
                this.ctx.lineTo(canvasPoint.x, canvasPoint.y);
            }
        }
        
        // Close the contour
        if (this.volumeContour.length > 0) {
            const firstPoint = this.volumeContour[0];
            const canvasPoint = this.imageToCanvasCoords(firstPoint.x, firstPoint.y);
            this.ctx.lineTo(canvasPoint.x, canvasPoint.y);
        }
        
        this.ctx.stroke();
        
        // Draw points
        this.ctx.fillStyle = '#00FF00';
        this.ctx.strokeStyle = '#FFFFFF';
        this.ctx.lineWidth = 1;
        
        for (const point of this.volumeContour) {
            const canvasPoint = this.imageToCanvasCoords(point.x, point.y);
            this.ctx.beginPath();
            this.ctx.arc(canvasPoint.x, canvasPoint.y, 3, 0, 2 * Math.PI);
            this.ctx.fill();
            this.ctx.stroke();
        }
    }

    calculateVolume() {
        if (this.volumeContour.length < 3) {
            alert('Need at least 3 points to calculate volume');
            return;
        }
        
        this.calculateVolumeFromContour();
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
        const token = this.getCookie('csrftoken');
        if (!token) {
            console.warn('CSRF token not found. Upload may fail.');
            // Try to get token from meta tag as fallback
            const metaToken = document.querySelector('meta[name="csrf-token"]');
            if (metaToken) {
                return metaToken.getAttribute('content');
            }
            return '';
        }
        return token;
    }
    
    redraw() {
        this.updateDisplay();
        this.drawMeasurements();
        this.drawAnnotations();
        this.drawAIHighlights();
        this.drawVolumeContour();
        this.drawCrosshair();
        this.updateOverlayLabels();
    }

    performAIAnalysis(analysisType = 'general') {
        if (!this.currentImage) {
            alert('Please load an image first');
            return;
        }
        
        const aiPanel = document.getElementById('ai-panel');
        aiPanel.style.display = 'block';
        
        const resultsDiv = document.getElementById('ai-results');
        resultsDiv.innerHTML = '<div class="loading">Performing AI analysis...</div>';
        
        fetch(`/viewer/api/images/${this.currentImage.id}/ai-analysis/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({ analysis_type: analysisType })
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
        
        // Generate findings HTML
        let findingsHTML = '';
        if (results.findings && results.findings.length > 0) {
            findingsHTML = results.findings.map(f => `
                <div class="ai-finding">
                    <div class="finding-header">
                        <strong>${f.type}</strong>
                        <span class="confidence">${(f.confidence * 100).toFixed(1)}% confidence</span>
                    </div>
                    <div class="finding-details">
                        ${f.description || `Location: (${f.location.x}, ${f.location.y}), Size: ${f.size}px`}
                    </div>
                </div>
            `).join('');
        } else {
            findingsHTML = '<p class="no-findings">No abnormal findings detected.</p>';
        }
        
        resultsDiv.innerHTML = `
            <div class="ai-summary">
                <h4>Analysis Summary</h4>
                <p>${results.summary}</p>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${results.confidence_score * 100}%"></div>
                    <span class="confidence-text">Confidence: ${(results.confidence_score * 100).toFixed(1)}%</span>
                </div>
            </div>
            <div class="ai-findings">
                <h4>Detailed Findings</h4>
                ${findingsHTML}
            </div>
            ${results.recommendations ? `
                <div class="ai-recommendations">
                    <h4>Recommendations</h4>
                    <p>${results.recommendations}</p>
                </div>
            ` : ''}
            <div class="ai-actions">
                <button onclick="viewer.copyAIResults()">Copy Results</button>
                <button onclick="viewer.toggleAIHighlights()">Toggle Highlights</button>
                <button onclick="viewer.saveAIReport()">Save Report</button>
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
    
    saveAIReport() {
        if (!this.aiAnalysisResults) return;
        
        const report = `AI Analysis Report
        
Study: ${this.currentStudy ? this.currentStudy.patient_name : 'Unknown'}
Date: ${new Date().toLocaleString()}
Analysis Type: ${this.aiAnalysisResults.analysis_type}

Summary:
${this.aiAnalysisResults.summary}

Confidence: ${(this.aiAnalysisResults.confidence_score * 100).toFixed(1)}%

Findings:
${this.aiAnalysisResults.findings.map(f => 
    `- ${f.type}: ${f.description || `Location (${f.location.x}, ${f.location.y})`} - Confidence: ${(f.confidence * 100).toFixed(1)}%`
).join('\n')}

Recommendations:
${this.aiAnalysisResults.recommendations || 'None'}`;
        
        // Create and download text file
        const blob = new Blob([report], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `AI_Report_${this.currentStudy ? this.currentStudy.patient_id : 'Unknown'}_${new Date().toISOString().split('T')[0]}.txt`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
    
    toggle3DOptions() {
        this.create3DModal();
    }
    
    show3DResult(data, type) {
        // Create a result modal
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'block';
        
        const title = {
            'mpr': 'Multi-Planar Reconstruction',
            'volume': 'Volume Rendering',
            'bone': '3D Bone Reconstruction',
            'vessel': 'Vessel Analysis',
            'surface': 'Surface Rendering'
        }[type] || type;
        
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="reconstruction-result">
                        <p>3D reconstruction completed successfully!</p>
                        <p>Type: ${type}</p>
                        <p>Series: ${this.currentSeries ? this.currentSeries.description : 'Unknown'}</p>
                        ${data.preview_image ? `<img src="${data.preview_image}" alt="3D Preview" style="max-width: 100%; margin-top: 20px;">` : ''}
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    apply3DReconstruction(type = 'mpr') {
        const seriesId = this.currentSeries ? this.currentSeries.id : null;
        
        if (!seriesId) {
            alert('Please select a series first');
            return;
        }
        
        // Show a simple progress indicator
        const progressOverlay = document.createElement('div');
        progressOverlay.className = 'reconstruction-progress';
        progressOverlay.innerHTML = `
            <div class="progress-content">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Generating ${type.toUpperCase()} reconstruction...</p>
            </div>
        `;
        document.body.appendChild(progressOverlay);
        
        // Use default parameters for quick reconstruction
        const windowCenter = 40;
        const windowWidth = 400;
        const thresholdMin = -1000;
        const thresholdMax = 1000;
        
        const url = `/viewer/api/series/${seriesId}/3d-reconstruction/?type=${type}&window_center=${windowCenter}&window_width=${windowWidth}&threshold_min=${thresholdMin}&threshold_max=${thresholdMax}`;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                progressOverlay.remove();
                this.show3DResult(data, type);
            })
            .catch(error => {
                progressOverlay.remove();
                alert('3D reconstruction failed: ' + error.message);
                console.error('3D reconstruction error:', error);
            });
    }
    
    create3DModal() {
        // Remove existing modal if any
        const existingModal = document.getElementById('3d-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        const modal = document.createElement('div');
        modal.id = '3d-modal';
        modal.className = 'modal';
        modal.style.display = 'block';
        
        modal.innerHTML = `
            <div class="modal-content large">
                <div class="modal-header">
                    <h3>3D Reconstruction</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="3d-controls">
                        <div class="control-group">
                            <label for="3d-reconstruction-type">Reconstruction Type:</label>
                            <select id="3d-reconstruction-type" class="form-select">
                                <option value="mpr">Multi-Planar Reconstruction (MPR)</option>
                                <option value="3d_bone">3D Bone Reconstruction</option>
                                <option value="angiogram">Angiogram (MIP)</option>
                                <option value="virtual_surgery">Virtual Surgery Planning</option>
                            </select>
                        </div>
                        
                        <div class="control-group">
                            <label for="3d-window-center">Window Center:</label>
                            <input type="range" id="3d-window-center" min="-1000" max="1000" value="40" class="slider">
                            <span id="3d-window-center-value">40</span>
                        </div>
                        
                        <div class="control-group">
                            <label for="3d-window-width">Window Width:</label>
                            <input type="range" id="3d-window-width" min="1" max="4000" value="400" class="slider">
                            <span id="3d-window-width-value">400</span>
                        </div>
                        
                        <div class="control-group">
                            <label for="3d-threshold-min">Threshold Min:</label>
                            <input type="range" id="3d-threshold-min" min="-1000" max="1000" value="-1000" class="slider">
                            <span id="3d-threshold-min-value">-1000</span>
                        </div>
                        
                        <div class="control-group">
                            <label for="3d-threshold-max">Threshold Max:</label>
                            <input type="range" id="3d-threshold-max" min="-1000" max="1000" value="1000" class="slider">
                            <span id="3d-threshold-max-value">1000</span>
                        </div>
                        
                        <div class="3d-description" id="3d-description">
                            <p><strong>MPR (Multi-Planar Reconstruction):</strong> View images in axial, sagittal, and coronal planes simultaneously.</p>
                        </div>
                    </div>
                    
                    <div class="3d-progress" id="3d-progress" style="display: none;">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: 100%;"></div>
                        </div>
                        <p class="3d-progress-text">Generating 3D reconstruction...</p>
                    </div>
                    
                    <div class="3d-results" id="3d-results" style="display: none;">
                        <div class="3d-viewports">
                            <div class="viewport-container">
                                <h4>Axial</h4>
                                <canvas id="3d-axial-canvas" width="256" height="256"></canvas>
                            </div>
                            <div class="viewport-container">
                                <h4>Sagittal</h4>
                                <canvas id="3d-sagittal-canvas" width="256" height="256"></canvas>
                            </div>
                            <div class="viewport-container">
                                <h4>Coronal</h4>
                                <canvas id="3d-coronal-canvas" width="256" height="256"></canvas>
                            </div>
                        </div>
                        <div class="3d-controls-panel">
                            <button class="secondary-btn" onclick="dicomViewer.export3DResults()">Export Results</button>
                            <button class="secondary-btn" onclick="dicomViewer.save3DReconstruction()">Save Reconstruction</button>
                        </div>
                    </div>
                    
                    <div class="modal-actions">
                        <button class="primary-btn" onclick="dicomViewer.apply3DReconstruction()">Generate 3D Reconstruction</button>
                        <button class="secondary-btn" onclick="this.closest('.modal').remove()">Cancel</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Add event listeners for sliders
        const sliders = modal.querySelectorAll('input[type="range"]');
        sliders.forEach(slider => {
            const valueSpan = modal.querySelector(`#${slider.id}-value`);
            slider.addEventListener('input', () => {
                valueSpan.textContent = slider.value;
                this.update3DDescription();
            });
        });
        
        // Add event listener for reconstruction type change
        const typeSelect = modal.querySelector('#3d-reconstruction-type');
        typeSelect.addEventListener('change', () => {
            this.update3DDescription();
        });
        
        this.update3DDescription();
    }
    
    update3DDescription() {
        const modal = document.getElementById('3d-modal');
        if (!modal) return;
        
        const type = modal.querySelector('#3d-reconstruction-type').value;
        const description = modal.querySelector('#3d-description');
        
        const descriptions = {
            'mpr': '<p><strong>MPR (Multi-Planar Reconstruction):</strong> View images in axial, sagittal, and coronal planes simultaneously. Useful for understanding spatial relationships and anatomy.</p>',
            '3d_bone': '<p><strong>3D Bone Reconstruction:</strong> Create 3D surface rendering of bone structures. Useful for orthopedic planning and fracture assessment.</p>',
            'angiogram': '<p><strong>Angiogram (MIP):</strong> Maximum Intensity Projection for vessel visualization. Highlights contrast-filled vessels and blood flow.</p>',
            'virtual_surgery': '<p><strong>Virtual Surgery Planning:</strong> Tissue segmentation and surgical planning tools. Includes cutting planes and surgical tool simulation.</p>'
        };
        
        description.innerHTML = descriptions[type] || descriptions['mpr'];
    }
    
    display3DReconstruction(data, modal) {
        const resultsDiv = modal.querySelector('#3d-results');
        const progressDiv = modal.querySelector('#3d-progress');
        
        progressDiv.style.display = 'none';
        resultsDiv.style.display = 'block';
        
        if (data.type === 'mpr') {
            this.displayMPRReconstruction(data, modal);
        } else if (data.type === '3d_bone') {
            this.display3DBoneReconstruction(data, modal);
        } else if (data.type === 'angiogram') {
            this.displayAngiogramReconstruction(data, modal);
        } else if (data.type === 'virtual_surgery') {
            this.displayVirtualSurgeryReconstruction(data, modal);
        }
    }
    
    displayMPRReconstruction(data, modal) {
        // Display axial, sagittal, and coronal views
        if (data.axial_data && data.axial_data.length > 0) {
            this.displaySlice(data.axial_data[0], '3d-axial-canvas', 'Axial');
        }
        
        if (data.sagittal_data && data.sagittal_data.length > 0) {
            this.displaySlice(data.sagittal_data[0], '3d-sagittal-canvas', 'Sagittal');
        }
        
        if (data.coronal_data && data.coronal_data.length > 0) {
            this.displaySlice(data.coronal_data[0], '3d-coronal-canvas', 'Coronal');
        }
    }
    
    display3DBoneReconstruction(data, modal) {
        // Display 3D bone reconstruction
        if (data.volume_data && data.volume_data.length > 0) {
            this.displayVolumeSlice(data.volume_data[0], '3d-axial-canvas', '3D Bone');
        }
    }
    
    displayAngiogramReconstruction(data, modal) {
        // Display angiogram with MIP
        if (data.mip_data) {
            this.displayMIPSlice(data.mip_data, '3d-axial-canvas', 'MIP Angiogram');
        }
    }
    
    displayVirtualSurgeryReconstruction(data, modal) {
        // Display virtual surgery planning
        if (data.segmentation_data && data.segmentation_data.length > 0) {
            this.displaySegmentationSlice(data.segmentation_data[0], '3d-axial-canvas', 'Virtual Surgery');
        }
    }
    
    displaySlice(sliceData, canvasId, title) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const imageData = ctx.createImageData(canvas.width, canvas.height);
        
        // Convert pixel data to image
        const pixelData = sliceData.pixel_data;
        const rows = sliceData.rows;
        const cols = sliceData.columns;
        
        for (let y = 0; y < rows && y < canvas.height; y++) {
            for (let x = 0; x < cols && x < canvas.width; x++) {
                const pixelIndex = (y * canvas.width + x) * 4;
                const value = pixelData[y] ? pixelData[y][x] : 0;
                
                imageData.data[pixelIndex] = value;     // R
                imageData.data[pixelIndex + 1] = value; // G
                imageData.data[pixelIndex + 2] = value; // B
                imageData.data[pixelIndex + 3] = 255;   // A
            }
        }
        
        ctx.putImageData(imageData, 0, 0);
    }
    
    displayVolumeSlice(sliceData, canvasId, title) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const imageData = ctx.createImageData(canvas.width, canvas.height);
        
        // Display bone mask with different colors
        const maskData = sliceData.mask_data;
        const rows = sliceData.rows;
        const cols = sliceData.columns;
        
        for (let y = 0; y < rows && y < canvas.height; y++) {
            for (let x = 0; x < cols && x < canvas.width; x++) {
                const pixelIndex = (y * canvas.width + x) * 4;
                const isBone = maskData[y] ? maskData[y][x] : false;
                
                if (isBone) {
                    imageData.data[pixelIndex] = 255;     // R (white for bone)
                    imageData.data[pixelIndex + 1] = 255; // G
                    imageData.data[pixelIndex + 2] = 255; // B
                } else {
                    imageData.data[pixelIndex] = 0;       // R (black for background)
                    imageData.data[pixelIndex + 1] = 0;   // G
                    imageData.data[pixelIndex + 2] = 0;   // B
                }
                imageData.data[pixelIndex + 3] = 255;     // A
            }
        }
        
        ctx.putImageData(imageData, 0, 0);
    }
    
    displayMIPSlice(mipData, canvasId, title) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const imageData = ctx.createImageData(canvas.width, canvas.height);
        
        // Display MIP data
        const pixelData = mipData.pixel_data;
        const rows = mipData.rows;
        const cols = mipData.columns;
        
        for (let y = 0; y < rows && y < canvas.height; y++) {
            for (let x = 0; x < cols && x < canvas.width; x++) {
                const pixelIndex = (y * canvas.width + x) * 4;
                const value = pixelData[y] ? pixelData[y][x] : 0;
                
                // Use red color for vessels
                imageData.data[pixelIndex] = value;     // R
                imageData.data[pixelIndex + 1] = 0;     // G
                imageData.data[pixelIndex + 2] = 0;     // B
                imageData.data[pixelIndex + 3] = 255;   // A
            }
        }
        
        ctx.putImageData(imageData, 0, 0);
    }
    
    displaySegmentationSlice(sliceData, canvasId, title) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const imageData = ctx.createImageData(canvas.width, canvas.height);
        
        // Display segmented tissues with different colors
        const segmentation = sliceData.segmentation;
        const rows = sliceData.rows;
        const cols = sliceData.columns;
        
        for (let y = 0; y < rows && y < canvas.height; y++) {
            for (let x = 0; x < cols && x < canvas.width; x++) {
                const pixelIndex = (y * canvas.width + x) * 4;
                
                let r = 0, g = 0, b = 0;
                
                if (segmentation.air && segmentation.air[y] && segmentation.air[y][x]) {
                    r = 0; g = 0; b = 0; // Black for air
                } else if (segmentation.fat && segmentation.fat[y] && segmentation.fat[y][x]) {
                    r = 255; g = 255; b = 0; // Yellow for fat
                } else if (segmentation.soft_tissue && segmentation.soft_tissue[y] && segmentation.soft_tissue[y][x]) {
                    r = 128; g = 128; b = 128; // Gray for soft tissue
                } else if (segmentation.bone && segmentation.bone[y] && segmentation.bone[y][x]) {
                    r = 255; g = 255; b = 255; // White for bone
                }
                
                imageData.data[pixelIndex] = r;
                imageData.data[pixelIndex + 1] = g;
                imageData.data[pixelIndex + 2] = b;
                imageData.data[pixelIndex + 3] = 255;
            }
        }
        
        ctx.putImageData(imageData, 0, 0);
    }
    
    export3DResults() {
        alert('3D results export functionality would be implemented here');
    }
    
    save3DReconstruction() {
        alert('3D reconstruction save functionality would be implemented here');
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
        
        fetch('/viewer/api/measurements/save/', {
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
        
        fetch('/viewer/api/measurements/save/', {
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
        
        fetch('/viewer/api/annotations/save/', {
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

    showError(message) {
        console.error('DICOM Viewer Error:', message);
        
        // Try to find an existing error display element
        let errorDiv = document.getElementById('dicom-error-display');
        
        if (!errorDiv) {
            // Create error display element if it doesn't exist
            errorDiv = document.createElement('div');
            errorDiv.id = 'dicom-error-display';
            errorDiv.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: #f8d7da;
                color: #721c24;
                padding: 20px;
                border: 1px solid #f5c6cb;
                border-radius: 5px;
                max-width: 500px;
                z-index: 1000;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            `;
            document.body.appendChild(errorDiv);
        }
        
        errorDiv.innerHTML = `
            <div style="margin-bottom: 10px;">
                <strong>Error:</strong> ${message}
            </div>
            <button onclick="document.getElementById('dicom-error-display').style.display='none'" 
                    style="background: #721c24; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">
                Close
            </button>
        `;
        errorDiv.style.display = 'block';
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            if (errorDiv.style.display !== 'none') {
                errorDiv.style.display = 'none';
            }
        }, 10000);
    }
    
    async loadStudyImages(studyId) {
        console.log('Loading study images for study:', studyId);
        try {
            const response = await fetch(`/viewer/api/studies/${studyId}/images/`);
            
            if (!response.ok) {
                let errorMessage;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || `Failed to load study (${response.status})`;
                } catch (e) {
                    const responseText = await response.text();
                    if (responseText.includes('<!DOCTYPE')) {
                        errorMessage = `Server error (${response.status}): Received HTML instead of JSON. Please check server logs.`;
                    } else {
                        errorMessage = `Server error (${response.status}): ${responseText.substring(0, 200)}`;
                    }
                }
                console.error('Failed to load study images:', errorMessage);
                this.showError(`Failed to load study: ${errorMessage}`);
                return;
            }

            const data = await response.json();
            console.log('Loaded study data:', data);
            
            if (!data.images || data.images.length === 0) {
                this.showError('No images found in this study. The study may be corrupted or the files may have been moved.');
                return;
            }

            this.currentStudy = data.study;
            this.currentImages = data.images;
            this.currentImageIndex = 0;
            
            // Update the UI with study information
            this.updateStudyInfo(data.study);
            
            // Load the first image
            if (this.currentImages.length > 0) {
                await this.loadImage(0);
                this.updateImageControls();
            }
            
        } catch (error) {
            console.error('Error loading study images:', error);
            this.showError(`Network error loading study: ${error.message}. Please check your connection and try again.`);
        }
    }
}

// Initialize the viewer when the page loads
let viewer;
document.addEventListener('DOMContentLoaded', () => {
    // Get initial study ID from global variable (if set by template)
    const initialStudyId = window.initialStudyId || null;
    viewer = new DicomViewer(initialStudyId);
});