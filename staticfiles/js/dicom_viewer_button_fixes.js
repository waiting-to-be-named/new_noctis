// Comprehensive Button Fix Script for DICOM Viewer
// Ensures all buttons are properly connected and functional

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing button fixes...');
    
    // Wait for the main viewer to initialize
    setTimeout(function() {
        setupButtonFixes();
    }, 2000);
});

function setupButtonFixes() {
    console.log('Setting up button fixes...');
    
    // Get the viewer instance
    const viewer = window.advancedViewer;
    
    // Basic navigation buttons
    setupNavigationButtons();
    
    // Tool buttons
    setupToolButtons(viewer);
    
    // Header buttons
    setupHeaderButtons(viewer);
    
    // Control buttons
    setupControlButtons(viewer);
    
    // Measurement and annotation buttons
    setupMeasurementButtons(viewer);
    
    // Add visual feedback for all buttons
    addButtonFeedback();
    
    console.log('Button fixes applied successfully!');
}

function setupNavigationButtons() {
    console.log('Setting up navigation buttons...');
    
    // Previous/Next study buttons
    const prevStudyBtn = document.getElementById('prev-study-btn');
    const nextStudyBtn = document.getElementById('next-study-btn');
    
    if (prevStudyBtn) {
        prevStudyBtn.addEventListener('click', function() {
            console.log('Previous study clicked');
            if (window.advancedViewer) {
                window.advancedViewer.previousStudy();
            }
        });
    }
    
    if (nextStudyBtn) {
        nextStudyBtn.addEventListener('click', function() {
            console.log('Next study clicked');
            if (window.advancedViewer) {
                window.advancedViewer.nextStudy();
            }
        });
    }
    
    // Image navigation buttons
    const prevImageBtn = document.getElementById('prev-image-btn');
    const nextImageBtn = document.getElementById('next-image-btn');
    
    if (prevImageBtn) {
        prevImageBtn.addEventListener('click', function() {
            console.log('Previous image clicked');
            if (window.advancedViewer) {
                window.advancedViewer.previousImage();
            }
        });
    }
    
    if (nextImageBtn) {
        nextImageBtn.addEventListener('click', function() {
            console.log('Next image clicked');
            if (window.advancedViewer) {
                window.advancedViewer.nextImage();
            }
        });
    }
}

function setupToolButtons(viewer) {
    console.log('Setting up tool buttons...');
    
    // Define all tool buttons with their actions
    const toolButtons = {
        // Basic tools
        'windowing-adv-btn': () => setTool('windowing'),
        'pan-adv-btn': () => setTool('pan'),
        'zoom-adv-btn': () => setTool('zoom'),
        'rotate-btn': () => rotateImage(),
        'flip-btn': () => flipImage(),
        
        // Measurement tools
        'measure-distance-btn': () => setTool('measure-distance'),
        'measure-angle-btn': () => setTool('measure-angle'),
        'measure-area-btn': () => setTool('measure-area'),
        'measure-volume-btn': () => setTool('measure-volume'),
        'hu-measurement-btn': () => setTool('hu-measurement'),
        
        // Annotation tools
        'text-annotation-btn': () => setTool('text-annotation'),
        'arrow-annotation-btn': () => setTool('arrow-annotation'),
        'circle-annotation-btn': () => setTool('circle-annotation'),
        'rectangle-annotation-btn': () => setTool('rectangle-annotation'),
        
        // Enhancement tools
        'invert-adv-btn': () => toggleInvert(),
        'crosshair-adv-btn': () => toggleCrosshair(),
        'magnify-btn': () => toggleMagnify(),
        'sharpen-btn': () => applySharpen(),
        
        // 3D/MPR tools
        'mpr-btn': () => enableMPR(),
        'volume-render-btn': () => enableVolumeRendering(),
        'mip-btn': () => enableMIP(),
        
        // AI tools
        'ai-analysis-btn': () => runAIAnalysis(),
        'ai-segment-btn': () => runAISegmentation(),
        
        // Utility tools
        'reset-adv-btn': () => resetView(),
        'fit-to-window-btn': () => fitToWindow(),
        'actual-size-btn': () => actualSize()
    };
    
    // Set up event listeners for all tool buttons
    Object.entries(toolButtons).forEach(([buttonId, action]) => {
        const button = document.getElementById(buttonId);
        if (button) {
            // Remove any existing listeners
            button.replaceWith(button.cloneNode(true));
            const newButton = document.getElementById(buttonId);
            
            newButton.addEventListener('click', function(e) {
                e.preventDefault();
                console.log(`Tool button clicked: ${buttonId}`);
                try {
                    action();
                    // Add active state
                    document.querySelectorAll('.tool-btn-advanced').forEach(btn => btn.classList.remove('active'));
                    newButton.classList.add('active');
                } catch (error) {
                    console.error(`Error executing action for ${buttonId}:`, error);
                    showNotification(`Error: ${error.message}`, 'error');
                }
            });
            
            console.log(`✓ Set up event listener for ${buttonId}`);
        } else {
            console.warn(`✗ Button not found: ${buttonId}`);
        }
    });
    
    // Tool action functions
    function setTool(toolName) {
        console.log(`Setting active tool: ${toolName}`);
        if (viewer && viewer.setActiveTool) {
            viewer.setActiveTool(toolName);
        } else {
            showNotification(`Tool ${toolName} activated`, 'info');
        }
    }
    
    function rotateImage() {
        console.log('Rotating image');
        if (viewer && viewer.rotateImage) {
            viewer.rotateImage(90);
        } else {
            showNotification('Rotate feature not available', 'warning');
        }
    }
    
    function flipImage() {
        console.log('Flipping image');
        if (viewer && viewer.flipImage) {
            viewer.flipImage();
        } else {
            showNotification('Flip feature not available', 'warning');
        }
    }
    
    function toggleInvert() {
        console.log('Toggling invert');
        if (viewer && viewer.toggleInvert) {
            viewer.toggleInvert();
        } else {
            showNotification('Invert feature not available', 'warning');
        }
    }
    
    function toggleCrosshair() {
        console.log('Toggling crosshair');
        if (viewer && viewer.toggleCrosshair) {
            viewer.toggleCrosshair();
        } else {
            showNotification('Crosshair feature not available', 'warning');
        }
    }
    
    function toggleMagnify() {
        console.log('Toggling magnify');
        if (viewer && viewer.toggleMagnify) {
            viewer.toggleMagnify();
        } else {
            showNotification('Magnify feature not available', 'warning');
        }
    }
    
    function applySharpen() {
        console.log('Applying sharpen');
        if (viewer && viewer.applySharpenFilter) {
            viewer.applySharpenFilter();
        } else {
            showNotification('Sharpen feature not available', 'warning');
        }
    }
    
    function enableMPR() {
        console.log('Enabling MPR');
        if (viewer && viewer.enableMPR) {
            viewer.enableMPR();
        } else {
            showNotification('MPR feature not available', 'warning');
        }
    }
    
    function enableVolumeRendering() {
        console.log('Enabling volume rendering');
        if (viewer && viewer.enableVolumeRendering) {
            viewer.enableVolumeRendering();
        } else {
            showNotification('Volume rendering feature not available', 'warning');
        }
    }
    
    function enableMIP() {
        console.log('Enabling MIP');
        if (viewer && viewer.enableMIP) {
            viewer.enableMIP();
        } else {
            showNotification('MIP feature not available', 'warning');
        }
    }
    
    function runAIAnalysis() {
        console.log('Running AI analysis');
        if (viewer && viewer.runAIAnalysis) {
            viewer.runAIAnalysis();
        } else {
            showNotification('AI Analysis feature not available', 'warning');
        }
    }
    
    function runAISegmentation() {
        console.log('Running AI segmentation');
        if (viewer && viewer.runAISegmentation) {
            viewer.runAISegmentation();
        } else {
            showNotification('AI Segmentation feature not available', 'warning');
        }
    }
    
    function resetView() {
        console.log('Resetting view');
        if (viewer && viewer.resetView) {
            viewer.resetView();
        } else {
            showNotification('Reset view feature not available', 'warning');
        }
    }
    
    function fitToWindow() {
        console.log('Fitting to window');
        if (viewer && viewer.fitToWindow) {
            viewer.fitToWindow();
        } else {
            showNotification('Fit to window feature not available', 'warning');
        }
    }
    
    function actualSize() {
        console.log('Setting actual size');
        if (viewer && viewer.actualSize) {
            viewer.actualSize();
        } else {
            showNotification('Actual size feature not available', 'warning');
        }
    }
}

function setupHeaderButtons(viewer) {
    console.log('Setting up header buttons...');
    
    const headerButtons = {
        'upload-advanced-btn': () => showUploadModal(),
        'export-btn': () => showExportModal(),
        'settings-btn': () => showSettingsModal(),
        'fullscreen-btn': () => toggleFullscreen(),
        'logout-advanced-btn': () => logout()
    };
    
    Object.entries(headerButtons).forEach(([buttonId, action]) => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.replaceWith(button.cloneNode(true));
            const newButton = document.getElementById(buttonId);
            
            newButton.addEventListener('click', function(e) {
                e.preventDefault();
                console.log(`Header button clicked: ${buttonId}`);
                try {
                    action();
                } catch (error) {
                    console.error(`Error executing action for ${buttonId}:`, error);
                    showNotification(`Error: ${error.message}`, 'error');
                }
            });
            
            console.log(`✓ Set up event listener for ${buttonId}`);
        }
    });
    
    // Header action functions
    function showUploadModal() {
        console.log('Showing upload modal');
        const uploadModal = document.getElementById('uploadModal');
        if (uploadModal) {
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const modal = new bootstrap.Modal(uploadModal);
                modal.show();
            } else {
                showNotification('Bootstrap not loaded. Please refresh the page.', 'error');
                console.error('Bootstrap is not defined. Make sure Bootstrap JS is loaded before this script.');
            }
        } else {
            showNotification('Upload modal not found', 'error');
        }
    }
    
    function showExportModal() {
        console.log('Showing export modal');
        showNotification('Export feature coming soon', 'info');
    }
    
    function showSettingsModal() {
        console.log('Showing settings modal');
        showNotification('Settings feature coming soon', 'info');
    }
    
    function toggleFullscreen() {
        console.log('Toggling fullscreen');
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            document.documentElement.requestFullscreen();
        }
    }
    
    function logout() {
        console.log('Logging out');
        if (confirm('Are you sure you want to logout?')) {
            window.location.href = '/accounts/logout/';
        }
    }
}

function setupControlButtons(viewer) {
    console.log('Setting up control buttons...');
    
    // Window/Level controls
    const windowSlider = document.getElementById('window-width-slider');
    const levelSlider = document.getElementById('window-level-slider');
    
    if (windowSlider) {
        windowSlider.addEventListener('input', function() {
            const value = this.value;
            console.log(`Window width changed: ${value}`);
            if (viewer && viewer.setWindowWidth) {
                viewer.setWindowWidth(value);
            }
            updateWindowInfo();
        });
    }
    
    if (levelSlider) {
        levelSlider.addEventListener('input', function() {
            const value = this.value;
            console.log(`Window level changed: ${value}`);
            if (viewer && viewer.setWindowLevel) {
                viewer.setWindowLevel(value);
            }
            updateWindowInfo();
        });
    }
    
    // Zoom controls
    const zoomSlider = document.getElementById('zoom-slider');
    if (zoomSlider) {
        zoomSlider.addEventListener('input', function() {
            const value = this.value;
            console.log(`Zoom changed: ${value}`);
            if (viewer && viewer.setZoom) {
                viewer.setZoom(value);
            }
            updateZoomInfo();
        });
    }
    
    // Series selector
    const seriesSelector = document.getElementById('series-selector');
    if (seriesSelector) {
        seriesSelector.addEventListener('change', function() {
            const seriesId = this.value;
            console.log(`Series changed: ${seriesId}`);
            if (viewer && viewer.loadSeries) {
                viewer.loadSeries(seriesId);
            }
        });
    }
    
    function updateWindowInfo() {
        const windowInfo = document.getElementById('window-info');
        const windowSlider = document.getElementById('window-width-slider');
        const levelSlider = document.getElementById('window-level-slider');
        
        if (windowInfo && windowSlider && levelSlider) {
            windowInfo.textContent = `W: ${windowSlider.value} L: ${levelSlider.value}`;
        }
    }
    
    function updateZoomInfo() {
        const zoomLevel = document.getElementById('zoom-level');
        const zoomSlider = document.getElementById('zoom-slider');
        
        if (zoomLevel && zoomSlider) {
            zoomLevel.textContent = `${Math.round(zoomSlider.value * 100)}%`;
        }
    }
}

function setupMeasurementButtons(viewer) {
    console.log('Setting up measurement buttons...');
    
    // Clear measurements button
    const clearMeasurementsBtn = document.getElementById('clear-measurements-btn');
    if (clearMeasurementsBtn) {
        clearMeasurementsBtn.addEventListener('click', function() {
            console.log('Clearing measurements');
            if (viewer && viewer.clearMeasurements) {
                viewer.clearMeasurements();
            } else {
                showNotification('Clear measurements feature not available', 'warning');
            }
        });
    }
    
    // Clear annotations button
    const clearAnnotationsBtn = document.getElementById('clear-annotations-btn');
    if (clearAnnotationsBtn) {
        clearAnnotationsBtn.addEventListener('click', function() {
            console.log('Clearing annotations');
            if (viewer && viewer.clearAnnotations) {
                viewer.clearAnnotations();
            } else {
                showNotification('Clear annotations feature not available', 'warning');
            }
        });
    }
}

function addButtonFeedback() {
    console.log('Adding button feedback...');
    
    // Add hover and click effects to all buttons
    const buttons = document.querySelectorAll('button, .btn');
    
    buttons.forEach(button => {
        // Add ripple effect on click
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            ripple.classList.add('ripple');
            
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
        
        // Add loading state for async operations
        button.addEventListener('click', function() {
            if (this.classList.contains('async-action')) {
                this.classList.add('loading');
                setTimeout(() => {
                    this.classList.remove('loading');
                }, 2000);
            }
        });
    });
}

function showNotification(message, type = 'info') {
    console.log(`Notification: ${message} (${type})`);
    
    // Try to use the viewer's notification system first
    if (window.advancedViewer && window.advancedViewer.notyf) {
        window.advancedViewer.notyf[type](message);
        return;
    }
    
    // Fallback to creating our own notification
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'error' ? '#ff3333' : type === 'warning' ? '#ff6b35' : type === 'success' ? '#00ff88' : '#0088ff'};
        color: white;
        border-radius: 4px;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Add CSS for button effects
const style = document.createElement('style');
style.textContent = `
.ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.3);
    transform: scale(0);
    animation: ripple-animation 0.6s linear;
    pointer-events: none;
}

@keyframes ripple-animation {
    to {
        transform: scale(4);
        opacity: 0;
    }
}

.loading {
    position: relative;
    pointer-events: none;
}

.loading::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 16px;
    height: 16px;
    margin: -8px 0 0 -8px;
    border: 2px solid #ffffff;
    border-radius: 50%;
    border-top-color: transparent;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes slideOut {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(100%);
        opacity: 0;
    }
}

button:hover {
    transform: translateY(-1px);
    transition: transform 0.2s ease;
}

button:active {
    transform: translateY(0);
}

.tool-btn-advanced.active {
    background-color: #0088ff !important;
    color: white !important;
}
`;

document.head.appendChild(style);

// Export for debugging
window.buttonFixes = {
    setupButtonFixes,
    setupNavigationButtons,
    setupToolButtons,
    setupHeaderButtons,
    setupControlButtons,
    setupMeasurementButtons,
    addButtonFeedback,
    showNotification
};

console.log('Button fixes script loaded successfully!');