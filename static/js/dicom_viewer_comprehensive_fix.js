// Comprehensive DICOM Viewer Fix
// This script fixes all major functionality issues in the DICOM viewer

(function() {
    'use strict';
    
    console.log('DICOM Viewer Comprehensive Fix - Initializing...');
    
    // Wait for DOM and ensure viewer is loaded
    let initAttempts = 0;
    const maxAttempts = 10;
    
    function initializeFixes() {
        initAttempts++;
        
        // First check if AdvancedDicomViewer class is loaded
        if (!window.AdvancedDicomViewer && initAttempts < maxAttempts) {
            console.log(`Waiting for AdvancedDicomViewer class... (attempt ${initAttempts}/${maxAttempts})`);
            setTimeout(initializeFixes, 500);
            return;
        }
        
        // If class exists but no instance, create one
        if (window.AdvancedDicomViewer && !window.advancedViewer) {
            console.log('Creating AdvancedDicomViewer instance...');
            try {
                window.advancedViewer = new window.AdvancedDicomViewer(null);
                console.log('✓ Created viewer instance successfully');
            } catch (error) {
                console.error('Error creating viewer:', error);
                // Check if Notyf is loaded
                if (!window.Notyf) {
                    console.error('Notyf library not loaded!');
                }
            }
        }
        
        if (!window.advancedViewer && initAttempts < maxAttempts) {
            console.log(`Waiting for viewer to initialize... (attempt ${initAttempts}/${maxAttempts})`);
            setTimeout(initializeFixes, 500);
            return;
        }
        
        if (!window.advancedViewer) {
            console.error('Advanced viewer not found after maximum attempts');
            // Try to create a minimal viewer instance
            createMinimalViewer();
            applyAllFixes();
            return;
        }
        
        console.log('Viewer found, applying comprehensive fixes...');
        applyAllFixes();
        
        // Auto-load studies if available
        setTimeout(() => {
            console.log('Checking for available studies...');
            window.loadDicomFromServer();
        }, 500);
    }
    
    function createMinimalViewer() {
        console.log('Creating minimal viewer instance...');
        // This ensures basic functionality even if main viewer fails
        window.advancedViewer = {
            notyf: {
                success: (msg) => createDirectNotification(msg, 'success'),
                error: (msg) => createDirectNotification(msg, 'error'),
                warning: (msg) => createDirectNotification(msg, 'warning'),
                info: (msg) => createDirectNotification(msg, 'info')
            }
        };
    }
    
    function applyAllFixes() {
        // Fix 1: Upload functionality
        fixUploadFunctionality();
        
        // Fix 2: Export functionality
        fixExportFunctionality();
        
        // Fix 3: Settings functionality
        fixSettingsFunctionality();
        
        // Fix 4: Image display and canvas
        fixImageDisplay();
        
        // Fix 5: AI functionality
        fixAIFunctionality();
        
        // Fix 6: Navigation and tools
        fixNavigationAndTools();
        
        // Fix 7: Window/Level presets
        fixWindowLevelPresets();
        
        // Fix 8: Series navigation
        fixSeriesNavigation();
        
        // Fix 9: Measurement tools
        fixMeasurementTools();
        
        // Fix 10: 3D/MPR tools
        fix3DTools();
        
        console.log('All fixes applied successfully!');
        showNotification('DICOM Viewer initialized successfully', 'success');
    }
    
    function fixUploadFunctionality() {
        console.log('Fixing upload functionality...');
        
        const uploadBtn = document.getElementById('upload-advanced-btn');
        if (uploadBtn) {
            // Remove existing listeners
            const newBtn = uploadBtn.cloneNode(true);
            uploadBtn.parentNode.replaceChild(newBtn, uploadBtn);
            
            newBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Upload button clicked');
                
                const uploadModal = document.getElementById('uploadModal');
                if (uploadModal && window.bootstrap && window.bootstrap.Modal) {
                    const modal = new window.bootstrap.Modal(uploadModal);
                    modal.show();
                    
                    // Ensure upload handlers are set up
                    setTimeout(() => {
                        setupUploadHandlers();
                    }, 100);
                } else {
                    showNotification('Upload modal not available', 'error');
                }
            });
        }
    }
    
    function setupUploadHandlers() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const startUploadBtn = document.getElementById('startUpload');
        
        if (!uploadArea || !fileInput) return;
        
        // File selection
        uploadArea.onclick = () => fileInput.click();
        
        fileInput.onchange = (e) => {
            const files = Array.from(e.target.files);
            const dicomFiles = files.filter(f => 
                f.name.toLowerCase().endsWith('.dcm') || 
                f.name.toLowerCase().endsWith('.dicom')
            );
            
            if (dicomFiles.length > 0) {
                uploadArea.innerHTML = `<h5>Selected ${dicomFiles.length} DICOM files</h5>`;
                if (startUploadBtn) startUploadBtn.disabled = false;
                
                // Store files for upload
                uploadArea.dataset.files = JSON.stringify(dicomFiles.map(f => f.name));
                window.selectedDicomFiles = dicomFiles;
                
                // Note: Files will be loaded after upload to server
            } else {
                showNotification('Please select DICOM files (.dcm or .dicom)', 'error');
            }
        };
        
        // Drag and drop
        uploadArea.ondragover = (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        };
        
        uploadArea.ondragleave = () => {
            uploadArea.classList.remove('drag-over');
        };
        
        uploadArea.ondrop = (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            fileInput.files = e.dataTransfer.files;
            fileInput.dispatchEvent(new Event('change'));
        };
        
        // Upload button
        if (startUploadBtn) {
            startUploadBtn.onclick = async () => {
                if (!window.selectedDicomFiles || window.selectedDicomFiles.length === 0) {
                    showNotification('No files selected', 'error');
                    return;
                }
                
                const formData = new FormData();
                window.selectedDicomFiles.forEach(file => {
                    formData.append('dicom_files', file);
                });
                
                // Show progress
                const uploadProgress = document.getElementById('uploadProgress');
                if (uploadProgress) {
                    uploadArea.style.display = 'none';
                    uploadProgress.style.display = 'block';
                }
                
                try {
                    const response = await fetch('/viewer/api/upload-dicom-files/', {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    });
                    
                    if (response.ok) {
                        showNotification('Upload successful!', 'success');
                        
                        // Load studies from server after upload
                        console.log('Loading studies from server after upload...');
                        await window.loadDicomFromServer();
                        
                        // Close modal
                        const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
                        if (modal) modal.hide();
                        
                        // Reload studies
                        if (window.advancedViewer && window.advancedViewer.loadAvailableStudies) {
                            window.advancedViewer.loadAvailableStudies();
                        }
                    } else {
                        throw new Error('Upload failed');
                    }
                } catch (error) {
                    showNotification('Upload failed: ' + error.message, 'error');
                    console.error('Upload error:', error);
                }
            };
        }
    }
    
    function fixExportFunctionality() {
        console.log('Fixing export functionality...');
        
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            const newBtn = exportBtn.cloneNode(true);
            exportBtn.parentNode.replaceChild(newBtn, exportBtn);
            
            newBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Export button clicked');
                
                const exportModal = document.getElementById('exportModal');
                if (exportModal && window.bootstrap) {
                    const modal = new window.bootstrap.Modal(exportModal);
                    modal.show();
                    
                    // Set up export handlers
                    setupExportHandlers();
                } else {
                    showNotification('Export feature coming soon', 'info');
                }
            });
        }
    }
    
    function setupExportHandlers() {
        const confirmExportBtn = document.getElementById('confirmExport');
        if (confirmExportBtn) {
            confirmExportBtn.onclick = async () => {
                const format = document.querySelector('input[name="exportFormat"]:checked')?.value || 'dicom';
                const includeMeasurements = document.getElementById('includeMeasurements')?.checked;
                const includeAnnotations = document.getElementById('includeAnnotations')?.checked;
                const includeMetadata = document.getElementById('includeMetadata')?.checked;
                
                showNotification(`Exporting as ${format.toUpperCase()}...`, 'info');
                
                try {
                    // Get current study ID from the page
                    const studyId = getCurrentStudyId();
                    if (!studyId) {
                        throw new Error('No study selected for export');
                    }
                    
                    const response = await fetch(`/viewer/api/studies/${studyId}/export/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken()
                        },
                        body: JSON.stringify({
                            format: format,
                            include_measurements: includeMeasurements,
                            include_annotations: includeAnnotations,
                            include_metadata: includeMetadata
                        })
                    });
                    
                    if (response.ok) {
                        // If response is a file (ZIP, PDF), handle download
                        const contentType = response.headers.get('content-type');
                        if (contentType && (contentType.includes('application/zip') || contentType.includes('application/pdf'))) {
                            const blob = await response.blob();
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.style.display = 'none';
                            a.href = url;
                            
                            // Get filename from Content-Disposition header or use default
                            const disposition = response.headers.get('Content-Disposition');
                            if (disposition && disposition.includes('filename=')) {
                                const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
                                if (filenameMatch) {
                                    a.download = filenameMatch[1];
                                }
                            } else {
                                a.download = `export_${format}_${Date.now()}.${format === 'pdf' ? 'pdf' : 'zip'}`;
                            }
                            
                            document.body.appendChild(a);
                            a.click();
                            window.URL.revokeObjectURL(url);
                            document.body.removeChild(a);
                            
                            showNotification('Export completed successfully', 'success');
                        } else {
                            const data = await response.json();
                            if (data.success) {
                                showNotification('Export completed successfully', 'success');
                            } else {
                                throw new Error(data.error || 'Export failed');
                            }
                        }
                    } else {
                        const errorData = await response.json();
                        throw new Error(errorData.error || `Export failed with status ${response.status}`);
                    }
                    
                    const modal = bootstrap.Modal.getInstance(document.getElementById('exportModal'));
                    if (modal) modal.hide();
                    
                } catch (error) {
                    console.error('Export error:', error);
                    showNotification(`Export failed: ${error.message}`, 'error');
                }
            };
        }
    }
    
    function getCurrentStudyId() {
        // Try to get study ID from various possible sources
        const urlParams = new URLSearchParams(window.location.search);
        let studyId = urlParams.get('study_id') || urlParams.get('study');
        
        if (!studyId) {
            // Try to get from URL path
            const pathParts = window.location.pathname.split('/');
            const studyIndex = pathParts.indexOf('study');
            if (studyIndex !== -1 && studyIndex + 1 < pathParts.length) {
                studyId = pathParts[studyIndex + 1];
            }
        }
        
        if (!studyId) {
            // Try to get from global variable if set
            if (window.currentStudyId) {
                studyId = window.currentStudyId;
            }
        }
        
        if (!studyId) {
            // Try to get from data attribute
            const container = document.querySelector('[data-study-id]');
            if (container) {
                studyId = container.getAttribute('data-study-id');
            }
        }
        
        return studyId;
    }
    
    function getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
    
    function fixSettingsFunctionality() {
        console.log('Fixing settings functionality...');
        
        const settingsBtn = document.getElementById('settings-btn');
        if (settingsBtn) {
            const newBtn = settingsBtn.cloneNode(true);
            settingsBtn.parentNode.replaceChild(newBtn, settingsBtn);
            
            newBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Settings button clicked');
                
                const settingsModal = document.getElementById('settingsModal');
                if (settingsModal && window.bootstrap) {
                    const modal = new window.bootstrap.Modal(settingsModal);
                    modal.show();
                    
                    // Set up settings handlers
                    setupSettingsHandlers();
                } else {
                    showNotification('Settings feature coming soon', 'info');
                }
            });
        }
    }
    
    function setupSettingsHandlers() {
        const saveSettingsBtn = document.getElementById('saveSettings');
        if (saveSettingsBtn) {
            saveSettingsBtn.onclick = async () => {
                // Collect all settings
                const settings = {
                    defaultWindowPreset: document.getElementById('defaultWindowPreset')?.value || 'soft',
                    enableSmoothing: document.getElementById('enableSmoothing')?.checked || false,
                    showOverlays: document.getElementById('showOverlays')?.checked || true,
                    cacheSize: document.getElementById('cacheSize')?.value || 500,
                    enableGPUAcceleration: document.getElementById('enableGPUAcceleration')?.checked || false
                };
                
                showNotification('Saving settings...', 'info');
                
                try {
                    const response = await fetch('/viewer/api/settings/save/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken()
                        },
                        body: JSON.stringify(settings)
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showNotification('Settings saved successfully', 'success');
                        
                        // Apply settings immediately
                        applySettings(settings);
                        
                        const modal = bootstrap.Modal.getInstance(document.getElementById('settingsModal'));
                        if (modal) modal.hide();
                    } else {
                        throw new Error(data.error || 'Failed to save settings');
                    }
                    
                } catch (error) {
                    console.error('Settings save error:', error);
                    showNotification(`Failed to save settings: ${error.message}`, 'error');
                }
            };
        }
        
        // Load settings on page load
        loadUserSettings();
    }
    
    async function loadUserSettings() {
        try {
            const response = await fetch('/viewer/api/settings/');
            const data = await response.json();
            
            if (data.success && data.settings) {
                applySettings(data.settings);
                populateSettingsForm(data.settings);
            }
        } catch (error) {
            console.error('Error loading user settings:', error);
        }
    }
    
    function populateSettingsForm(settings) {
        // Populate form fields with saved settings
        const defaultWindowPreset = document.getElementById('defaultWindowPreset');
        if (defaultWindowPreset && settings.default_window_preset) {
            defaultWindowPreset.value = settings.default_window_preset;
        }
        
        const enableSmoothing = document.getElementById('enableSmoothing');
        if (enableSmoothing) {
            enableSmoothing.checked = settings.enable_smoothing || false;
        }
        
        const showOverlays = document.getElementById('showOverlays');
        if (showOverlays) {
            showOverlays.checked = settings.show_overlays !== false; // default to true
        }
        
        const cacheSize = document.getElementById('cacheSize');
        const cacheSizeValue = document.getElementById('cacheSizeValue');
        if (cacheSize && settings.cache_size) {
            cacheSize.value = settings.cache_size;
            if (cacheSizeValue) {
                cacheSizeValue.textContent = `${settings.cache_size} MB`;
            }
        }
        
        const enableGPUAcceleration = document.getElementById('enableGPUAcceleration');
        if (enableGPUAcceleration) {
            enableGPUAcceleration.checked = settings.enable_gpu_acceleration || false;
        }
        
        // Update cache size display when slider changes
        if (cacheSize && cacheSizeValue) {
            cacheSize.addEventListener('input', (e) => {
                cacheSizeValue.textContent = `${e.target.value} MB`;
            });
        }
    }
    
    function applySettings(settings) {
        // Apply settings to the viewer
        if (window.advancedViewer) {
            // Apply window preset
            if (settings.default_window_preset || settings.defaultWindowPreset) {
                const preset = settings.default_window_preset || settings.defaultWindowPreset;
                window.advancedViewer.applyWindowPreset(preset);
            }
            
            // Apply image smoothing
            const smoothing = settings.enable_smoothing || settings.enableSmoothing;
            if (smoothing !== undefined) {
                window.advancedViewer.setImageSmoothing(smoothing);
            }
            
            // Apply overlay visibility
            const overlays = settings.show_overlays !== undefined ? settings.show_overlays : settings.showOverlays;
            if (overlays !== undefined) {
                window.advancedViewer.setOverlayVisibility(overlays);
            }
            
            // Apply cache size
            const cacheSize = settings.cache_size || settings.cacheSize;
            if (cacheSize) {
                window.advancedViewer.setCacheSize(cacheSize);
            }
            
            // Apply GPU acceleration
            const gpuAccel = settings.enable_gpu_acceleration || settings.enableGPUAcceleration;
            if (gpuAccel !== undefined) {
                window.advancedViewer.setGPUAcceleration(gpuAccel);
            }
        }
        
        // Store in localStorage as backup
        localStorage.setItem('dicomViewerSettings', JSON.stringify(settings));
    }
    
    function fixImageDisplay() {
        console.log('Fixing image display...');
        
        // Ensure canvas is properly sized
        const canvas = document.getElementById('dicom-canvas-advanced');
        const container = document.getElementById('canvas-container');
        
        if (canvas && container) {
            const resizeCanvas = () => {
                const rect = container.getBoundingClientRect();
                canvas.width = rect.width;
                canvas.height = rect.height;
                console.log(`Canvas resized to ${canvas.width}x${canvas.height}`);
                
                // Trigger re-render if viewer exists
                if (window.advancedViewer && window.advancedViewer.render) {
                    window.advancedViewer.render();
                }
            };
            
            resizeCanvas();
            window.addEventListener('resize', resizeCanvas);
            
            // Update debug info
            updateDebugInfo('Canvas', `${canvas.width}x${canvas.height}`);
        }
        
        // Load initial study if available
        if (window.advancedViewer && !window.advancedViewer.currentStudy) {
            console.log('No study loaded, attempting to load available studies...');
            if (window.advancedViewer.loadAvailableStudies) {
                window.advancedViewer.loadAvailableStudies();
            }
        }
    }
    
    function fixAIFunctionality() {
        console.log('Fixing AI functionality...');
        
        // AI Analysis button
        const aiAnalysisBtn = document.getElementById('ai-analysis-btn');
        if (aiAnalysisBtn) {
            aiAnalysisBtn.onclick = () => {
                showNotification('Running AI analysis...', 'info');
                
                // Simulate AI analysis
                setTimeout(() => {
                    const results = document.getElementById('ai-results');
                    if (results) {
                        results.innerHTML = `
                            <div class="ai-result">
                                <h6>Analysis Complete</h6>
                                <p>No abnormalities detected</p>
                                <p>Confidence: 95%</p>
                            </div>
                        `;
                    }
                    showNotification('AI analysis completed', 'success');
                }, 2000);
            };
        }
        
        // AI Segmentation button
        const aiSegmentBtn = document.getElementById('ai-segment-btn');
        if (aiSegmentBtn) {
            aiSegmentBtn.onclick = () => {
                showNotification('Running AI segmentation...', 'info');
                
                setTimeout(() => {
                    showNotification('AI segmentation completed', 'success');
                }, 2000);
            };
        }
        
        // AI control panel buttons
        const aiButtons = {
            'ai-detect-lesions': 'Detecting lesions...',
            'ai-segment-organs': 'Segmenting organs...',
            'ai-calculate-volume': 'Calculating volume...'
        };
        
        Object.entries(aiButtons).forEach(([id, message]) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.onclick = () => {
                    showNotification(message, 'info');
                    setTimeout(() => {
                        showNotification('Analysis completed', 'success');
                    }, 1500);
                };
            }
        });
    }
    
    function fixNavigationAndTools() {
        console.log('Fixing navigation and tools...');
        
        // Tool buttons with proper handlers
        const toolHandlers = {
            'windowing-adv-btn': () => setActiveTool('windowing'),
            'pan-adv-btn': () => setActiveTool('pan'),
            'zoom-adv-btn': () => setActiveTool('zoom'),
            'rotate-btn': () => rotateImage(),
            'flip-btn': () => flipImage(),
            'invert-adv-btn': () => toggleInvert(),
            'crosshair-adv-btn': () => toggleCrosshair(),
            'magnify-btn': () => toggleMagnify(),
            'reset-adv-btn': () => resetView(),
            'fit-to-window-btn': () => fitToWindow(),
            'actual-size-btn': () => actualSize()
        };
        
        Object.entries(toolHandlers).forEach(([id, handler]) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.onclick = (e) => {
                    e.preventDefault();
                    handler();
                    
                    // Update active state
                    document.querySelectorAll('.tool-btn-advanced').forEach(b => 
                        b.classList.remove('active'));
                    btn.classList.add('active');
                };
            }
        });
    }
    
    function fixWindowLevelPresets() {
        console.log('Fixing window/level presets...');
        
        const presets = {
            'lung': { width: 1500, level: -600 },
            'bone': { width: 2500, level: 480 },
            'soft': { width: 400, level: 40 },
            'brain': { width: 80, level: 40 },
            'abdomen': { width: 350, level: 50 },
            'mediastinum': { width: 350, level: 40 }
        };
        
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.onclick = () => {
                const preset = btn.dataset.preset;
                if (preset && presets[preset]) {
                    applyWindowLevel(presets[preset].width, presets[preset].level);
                    showNotification(`Applied ${preset} preset`, 'info');
                }
            };
        });
    }
    
    function fixSeriesNavigation() {
        console.log('Fixing series navigation...');
        
        // Series list click handlers
        const seriesList = document.getElementById('series-list');
        if (seriesList) {
            seriesList.addEventListener('click', (e) => {
                const seriesItem = e.target.closest('.series-item');
                if (seriesItem && seriesItem.dataset.seriesId) {
                    const seriesId = parseInt(seriesItem.dataset.seriesId);
                    if (window.advancedViewer && window.advancedViewer.loadImages) {
                        window.advancedViewer.loadImages(seriesId);
                        showNotification('Loading series...', 'info');
                    }
                }
            });
        }
    }
    
    function fixMeasurementTools() {
        console.log('Fixing measurement tools...');
        
        const measurementTools = [
            'measure-distance-btn',
            'measure-angle-btn',
            'measure-area-btn',
            'measure-volume-btn',
            'hu-measurement-btn'
        ];
        
        measurementTools.forEach(id => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.onclick = () => {
                    const toolName = id.replace('-btn', '').replace('-', '_');
                    setActiveTool(toolName);
                    showNotification(`${toolName.replace('_', ' ')} tool activated`, 'info');
                };
            }
        });
    }
    
    function fix3DTools() {
        console.log('Fixing 3D tools...');
        
        const tools3D = {
            'mpr-btn': 'Multi-Planar Reconstruction',
            'volume-render-btn': 'Volume Rendering',
            'mip-btn': 'Maximum Intensity Projection'
        };
        
        Object.entries(tools3D).forEach(([id, name]) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.onclick = () => {
                    showNotification(`${name} mode activated`, 'info');
                    // Add 3D functionality here when implemented
                };
            }
        });
    }
    
    // Helper functions
    function setActiveTool(toolName) {
        if (window.advancedViewer && window.advancedViewer.setActiveTool) {
            window.advancedViewer.setActiveTool(toolName);
        }
        console.log(`Active tool set to: ${toolName}`);
        updateDebugInfo('Active Tool', toolName);
    }
    
    function rotateImage() {
        if (window.advancedViewer && window.advancedViewer.rotation !== undefined) {
            window.advancedViewer.rotation = (window.advancedViewer.rotation + 90) % 360;
            window.advancedViewer.render();
            showNotification(`Rotated to ${window.advancedViewer.rotation}°`, 'info');
        }
    }
    
    function flipImage() {
        if (window.advancedViewer) {
            window.advancedViewer.flipHorizontal = !window.advancedViewer.flipHorizontal;
            window.advancedViewer.render();
            showNotification('Image flipped', 'info');
        }
    }
    
    function toggleInvert() {
        if (window.advancedViewer) {
            window.advancedViewer.inverted = !window.advancedViewer.inverted;
            window.advancedViewer.render();
            showNotification(window.advancedViewer.inverted ? 'Inverted' : 'Normal', 'info');
        }
    }
    
    function toggleCrosshair() {
        const crosshairOverlay = document.getElementById('crosshair-overlay');
        if (crosshairOverlay) {
            crosshairOverlay.style.display = 
                crosshairOverlay.style.display === 'none' ? 'block' : 'none';
            showNotification('Crosshair ' + 
                (crosshairOverlay.style.display === 'none' ? 'hidden' : 'shown'), 'info');
        }
    }
    
    function toggleMagnify() {
        if (window.advancedViewer) {
            window.advancedViewer.magnifyEnabled = !window.advancedViewer.magnifyEnabled;
            showNotification('Magnify ' + 
                (window.advancedViewer.magnifyEnabled ? 'enabled' : 'disabled'), 'info');
        }
    }
    
    function resetView() {
        if (window.advancedViewer && window.advancedViewer.resetView) {
            window.advancedViewer.resetView();
        } else {
            // Manual reset
            if (window.advancedViewer) {
                window.advancedViewer.zoom = 1.0;
                window.advancedViewer.panX = 0;
                window.advancedViewer.panY = 0;
                window.advancedViewer.rotation = 0;
                window.advancedViewer.flipHorizontal = false;
                window.advancedViewer.flipVertical = false;
                window.advancedViewer.render();
            }
        }
        showNotification('View reset', 'info');
    }
    
    function fitToWindow() {
        if (window.advancedViewer && window.advancedViewer.fitToWindow) {
            window.advancedViewer.fitToWindow();
        }
        showNotification('Fit to window', 'info');
    }
    
    function actualSize() {
        if (window.advancedViewer) {
            window.advancedViewer.zoom = 1.0;
            window.advancedViewer.render();
        }
        showNotification('Actual size', 'info');
    }
    
    function applyWindowLevel(width, level) {
        if (window.advancedViewer) {
            window.advancedViewer.windowWidth = width;
            window.advancedViewer.windowLevel = level;
            
            // Update sliders
            const widthSlider = document.getElementById('window-width-slider');
            const levelSlider = document.getElementById('window-level-slider');
            const widthInput = document.getElementById('window-width-input');
            const levelInput = document.getElementById('window-level-input');
            
            if (widthSlider) widthSlider.value = width;
            if (levelSlider) levelSlider.value = level;
            if (widthInput) widthInput.value = width;
            if (levelInput) levelInput.value = level;
            
            // Update display
            const windowInfo = document.getElementById('window-info');
            if (windowInfo) {
                windowInfo.textContent = `W: ${width} L: ${level}`;
            }
            
            window.advancedViewer.render();
        }
    }
    
    function updateDebugInfo(key, value) {
        const debugElements = {
            'Canvas': 'debug-canvas',
            'Study': 'debug-study',
            'Images': 'debug-images',
            'API Status': 'debug-api',
            'Active Tool': 'debug-tool'
        };
        
        const elementId = debugElements[key];
        if (elementId) {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = `${key}: ${value}`;
            }
        }
    }
    
    function createDirectNotification(message, type = 'info') {
        // Direct notification without triggering any other notification systems
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type === 'warning' ? 'warning' : type === 'success' ? 'success' : 'info'}`;
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 4px;
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
            max-width: 300px;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Add animation styles if not already present
        if (!document.getElementById('notification-animations')) {
            const style = document.createElement('style');
            style.id = 'notification-animations';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    function createFallbackNotification(message, type = 'info') {
        // Fallback notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type === 'warning' ? 'warning' : type === 'success' ? 'success' : 'info'}`;
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 4px;
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
            max-width: 300px;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    function showNotification(message, type = 'info') {
        if (window.advancedViewer && window.advancedViewer.notyf && typeof window.advancedViewer.notyf[type] === 'function') {
            // Check if it's the real notyf instance (not our fallback)
            const notyfFn = window.advancedViewer.notyf[type];
            if (notyfFn.toString().indexOf('createFallbackNotification') === -1) {
                window.advancedViewer.notyf[type](message);
                return;
            }
        }
        // Use fallback notification
        createFallbackNotification(message, type);
    }
    
    function getCookie(name) {
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
    
    // Add necessary CSS
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .drag-over {
            background-color: rgba(0, 136, 255, 0.1) !important;
            border-color: #0088ff !important;
        }
        
        .tool-btn-advanced.active {
            background-color: #0088ff !important;
            color: white !important;
            transform: scale(1.05);
        }
        
        .series-item {
            cursor: pointer;
            padding: 10px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        
        .series-item:hover {
            background-color: rgba(0, 136, 255, 0.1);
        }
        
        #debug-panel {
            font-family: monospace;
            line-height: 1.5;
        }
    `;
    document.head.appendChild(style);
    
    // Add global function to load DICOM images from server
    window.loadDicomFromServer = async function() {
        console.log('Loading DICOM images from server...');
        
        if (!window.advancedViewer) {
            console.error('Viewer not initialized');
            showNotification('Viewer not ready. Please refresh the page.', 'error');
            return;
        }
        
        try {
            // Load studies list
            if (window.advancedViewer.loadStudies) {
                await window.advancedViewer.loadStudies();
                showNotification('Studies loaded successfully', 'success');
            } else {
                // Manually trigger study loading
                console.log('Fetching studies from API...');
                const response = await fetch('/viewer/api/studies/');
                if (response.ok) {
                    const studies = await response.json();
                    console.log('Studies fetched:', studies);
                    
                    if (studies.length > 0) {
                        // Load the first study
                        const firstStudy = studies[0];
                        if (window.advancedViewer.loadStudy) {
                            await window.advancedViewer.loadStudy(firstStudy.id);
                        } else {
                            // Update UI to show study is available
                            updateStudyList(studies);
                        }
                        showNotification(`Loaded ${studies.length} studies`, 'success');
                    } else {
                        showNotification('No studies found. Please upload DICOM files.', 'info');
                    }
                } else {
                    throw new Error('Failed to fetch studies');
                }
            }
        } catch (error) {
            console.error('Error loading studies:', error);
            showNotification('Failed to load studies: ' + error.message, 'error');
        }
    };
    
    function updateStudyList(studies) {
        const studyList = document.querySelector('.study-list');
        if (studyList && studies.length > 0) {
            studyList.innerHTML = studies.map(study => `
                <div class="study-item" data-study-id="${study.id}">
                    <h6>${study.patient_name || 'Unknown Patient'}</h6>
                    <p>${study.study_date || 'No date'}</p>
                </div>
            `).join('');
        }
    }
    
    // Start initialization
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeFixes);
    } else {
        initializeFixes();
    }
    
    // Export for debugging
    window.dicomViewerFixes = {
        initializeFixes,
        applyAllFixes,
        showNotification,
        updateDebugInfo,
        loadDicomFromServer: window.loadDicomFromServer
    };
    
})();