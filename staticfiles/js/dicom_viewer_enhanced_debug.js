
// Enhanced debugging and initialization script
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing enhanced DICOM viewer...');
    
    // Debug panel updates
    function updateDebugPanel(key, value) {
        const element = document.getElementById(`debug-${key}`);
        if (element) {
            element.textContent = `${key.charAt(0).toUpperCase() + key.slice(1)}: ${value}`;
        }
    }
    
    // Test API connectivity
    async function testAPI() {
        try {
            updateDebugPanel('api', 'Testing...');
            const response = await fetch('/viewer/api/test/');
            const data = await response.json();
            updateDebugPanel('api', `Working (${data.data.studies} studies)`);
            console.log('API test result:', data);
            return data;
        } catch (error) {
            updateDebugPanel('api', 'Failed');
            console.error('API test failed:', error);
            return null;
        }
    }
    
    // Enhanced viewer initialization
    function initializeEnhancedViewer() {
        console.log('Starting enhanced viewer initialization...');
        
        // Check canvas
        const canvas = document.getElementById('dicom-canvas-advanced');
        if (canvas) {
            updateDebugPanel('canvas', 'Found');
            console.log('Canvas found:', canvas);
            
            // Set canvas size
            const container = canvas.parentElement;
            if (container) {
                canvas.width = container.clientWidth || 800;
                canvas.height = container.clientHeight || 600;
                console.log(`Canvas sized: ${canvas.width}x${canvas.height}`);
            }
        } else {
            updateDebugPanel('canvas', 'Missing');
            console.error('Canvas not found!');
        }
        
        // Test API and load data
        testAPI().then(apiData => {
            if (apiData && apiData.data.studies > 0) {
                updateDebugPanel('study', 'Available');
                updateDebugPanel('images', apiData.data.images);
                
                // Initialize the actual viewer
                if (window.AdvancedDicomViewer) {
                    try {
                        window.advancedViewer = new AdvancedDicomViewer(null);
                        console.log('Advanced viewer initialized successfully');
                    } catch (error) {
                        console.error('Error initializing advanced viewer:', error);
                    }
                }
            } else {
                updateDebugPanel('study', 'None found');
                updateDebugPanel('images', '0');
                console.warn('No studies found in database');
                
                // Show helpful message
                showMessage('No DICOM studies found. Please upload DICOM files to begin.', 'warning');
            }
        });
    }
    
    // Show message function
    function showMessage(message, type = 'info') {
        const errorsDiv = document.getElementById('viewer-errors');
        if (errorsDiv) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `alert alert-${type} alert-dismissible fade show`;
            messageDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            errorsDiv.appendChild(messageDiv);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                messageDiv.remove();
            }, 5000);
        }
    }
    
    // Wait a bit for all resources to load, then initialize
    setTimeout(initializeEnhancedViewer, 1000);
});

// Global debug functions
window.debugViewer = {
    testAPI: async () => {
        const response = await fetch('/viewer/api/test/');
        const data = await response.json();
        console.log('API Debug:', data);
        return data;
    },
    
    checkCanvas: () => {
        const canvas = document.getElementById('dicom-canvas-advanced');
        console.log('Canvas Debug:', {
            found: !!canvas,
            dimensions: canvas ? `${canvas.width}x${canvas.height}` : 'N/A',
            context: canvas ? !!canvas.getContext('2d') : false
        });
        return canvas;
    },
    
    listStudies: async () => {
        try {
            const response = await fetch('/viewer/api/studies/');
            const data = await response.json();
            console.log('Studies Debug:', data);
            return data;
        } catch (error) {
            console.error('Failed to fetch studies:', error);
            return null;
        }
    }
};
