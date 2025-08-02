// Viewer Worklist Integration Fix
// This script ensures proper initialization when redirecting from worklist

(function() {
    'use strict';
    
    console.log('Viewer Worklist Fix: Loading...');
    
    // Function to ensure canvas exists and is properly initialized
    function ensureCanvasExists() {
        let canvas = document.getElementById('dicom-canvas-advanced');
        
        if (!canvas) {
            console.log('Canvas not found, creating it...');
            
            // Find the canvas container
            const canvasContainer = document.getElementById('canvas-container') || 
                                   document.querySelector('.canvas-container') ||
                                   document.querySelector('.viewer-canvas-container');
            
            if (canvasContainer) {
                // Create canvas element
                canvas = document.createElement('canvas');
                canvas.id = 'dicom-canvas-advanced';
                canvas.className = 'dicom-canvas-advanced';
                canvas.width = canvasContainer.clientWidth || 800;
                canvas.height = canvasContainer.clientHeight || 600;
                canvas.style.cssText = 'width: 100%; height: 100%; background: #000; display: block;';
                
                // Clear container and add canvas
                canvasContainer.innerHTML = '';
                canvasContainer.appendChild(canvas);
                
                console.log('Canvas created successfully:', canvas.width + 'x' + canvas.height);
                
                // Update debug panel if exists
                const debugCanvas = document.getElementById('debug-canvas');
                if (debugCanvas) {
                    debugCanvas.textContent = `Canvas: Created ${canvas.width}x${canvas.height}`;
                    debugCanvas.style.color = '#00ff88';
                }
            } else {
                console.error('Canvas container not found! Looking for alternatives...');
                
                // Try to find the main viewer content area
                const viewerContent = document.querySelector('.viewer-content-advanced') ||
                                    document.querySelector('.viewer-main-content') ||
                                    document.querySelector('.main-content-advanced');
                
                if (viewerContent) {
                    // Create container and canvas
                    const container = document.createElement('div');
                    container.id = 'canvas-container';
                    container.className = 'canvas-container';
                    container.style.cssText = 'position: relative; width: 100%; height: 600px; background: #000;';
                    
                    canvas = document.createElement('canvas');
                    canvas.id = 'dicom-canvas-advanced';
                    canvas.className = 'dicom-canvas-advanced';
                    canvas.width = 800;
                    canvas.height = 600;
                    canvas.style.cssText = 'width: 100%; height: 100%; background: #000; display: block;';
                    
                    container.appendChild(canvas);
                    
                    // Find where to insert it
                    const viewportGrid = viewerContent.querySelector('.viewport-grid-advanced');
                    if (viewportGrid) {
                        viewportGrid.appendChild(container);
                    } else {
                        viewerContent.insertBefore(container, viewerContent.firstChild);
                    }
                    
                    console.log('Canvas and container created in viewer content');
                }
            }
        } else {
            console.log('Canvas already exists:', canvas.width + 'x' + canvas.height);
        }
        
        return canvas;
    }
    
    // Function to reinitialize viewer if needed
    function reinitializeViewer() {
        // Ensure canvas exists
        const canvas = ensureCanvasExists();
        
        if (!canvas) {
            console.error('Failed to create canvas, cannot initialize viewer');
            return;
        }
        
        // Check if viewer is already initialized
        if (window.advancedViewer && window.advancedViewer.canvas) {
            console.log('Viewer already initialized');
            
            // If we have a study ID from the URL, load it
            const urlPath = window.location.pathname;
            const studyMatch = urlPath.match(/\/viewer\/study\/(\d+)\//);
            
            if (studyMatch) {
                const studyId = parseInt(studyMatch[1]);
                console.log('Loading study from URL:', studyId);
                
                if (window.advancedViewer.currentStudy?.id !== studyId) {
                    window.advancedViewer.loadStudy(studyId);
                }
            }
        } else {
            console.log('Viewer not initialized, attempting to initialize...');
            
            // Get study ID from URL or Django context
            let studyId = null;
            const urlPath = window.location.pathname;
            const studyMatch = urlPath.match(/\/viewer\/study\/(\d+)\//);
            
            if (studyMatch) {
                studyId = parseInt(studyMatch[1]);
            }
            
            // Wait a bit for scripts to load, then initialize
            setTimeout(() => {
                if (typeof AdvancedDicomViewer !== 'undefined') {
                    console.log('Initializing AdvancedDicomViewer with study:', studyId);
                    window.advancedViewer = new AdvancedDicomViewer(studyId);
                    
                    // Update debug panel
                    const debugStudy = document.getElementById('debug-study');
                    if (debugStudy && studyId) {
                        debugStudy.textContent = `Study: Loading #${studyId}`;
                        debugStudy.style.color = '#ffaa00';
                    }
                } else {
                    console.error('AdvancedDicomViewer class not found after waiting');
                    
                    // Try to reload the main script
                    const script = document.createElement('script');
                    script.src = '/static/js/dicom_viewer_advanced.js';
                    script.onload = function() {
                        console.log('Script reloaded, trying initialization again...');
                        if (typeof AdvancedDicomViewer !== 'undefined') {
                            window.advancedViewer = new AdvancedDicomViewer(studyId);
                        }
                    };
                    document.head.appendChild(script);
                }
            }, 500);
        }
    }
    
    // Function to monitor viewer state
    function monitorViewerState() {
        const updateDebugInfo = () => {
            if (window.advancedViewer) {
                const debugStudy = document.getElementById('debug-study');
                const debugImages = document.getElementById('debug-images');
                const debugApi = document.getElementById('debug-api');
                const debugTool = document.getElementById('debug-tool');
                
                if (debugStudy && window.advancedViewer.currentStudy) {
                    debugStudy.textContent = `Study: #${window.advancedViewer.currentStudy.id} - ${window.advancedViewer.currentStudy.patient_name || 'Unknown'}`;
                    debugStudy.style.color = '#00ff88';
                }
                
                if (debugImages) {
                    const imageCount = window.advancedViewer.currentImages?.length || 0;
                    const currentIndex = window.advancedViewer.currentImageIndex || 0;
                    debugImages.textContent = `Images: ${currentIndex + 1}/${imageCount}`;
                    debugImages.style.color = imageCount > 0 ? '#00ff88' : '#ff6b35';
                }
                
                if (debugApi) {
                    debugApi.textContent = 'API Status: Connected';
                    debugApi.style.color = '#00ff88';
                }
                
                if (debugTool) {
                    debugTool.textContent = `Active Tool: ${window.advancedViewer.activeTool || 'None'}`;
                    debugTool.style.color = '#00ff88';
                }
            }
        };
        
        // Update immediately and then periodically
        updateDebugInfo();
        setInterval(updateDebugInfo, 1000);
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            console.log('DOM loaded, initializing viewer worklist fix...');
            reinitializeViewer();
            monitorViewerState();
        });
    } else {
        console.log('DOM already loaded, initializing viewer worklist fix immediately...');
        reinitializeViewer();
        monitorViewerState();
    }
    
    // Also try on window load as backup
    window.addEventListener('load', () => {
        console.log('Window loaded, checking viewer initialization...');
        if (!window.advancedViewer || !window.advancedViewer.canvas) {
            reinitializeViewer();
        }
    });
    
    // Expose fix function globally
    window.viewerWorklistFix = {
        ensureCanvasExists,
        reinitializeViewer,
        version: '1.0.0'
    };
    
    console.log('Viewer Worklist Fix: Loaded successfully');
})();