// DICOM Tissue Differentiation Enhancement Module
// Created from today's enhancement discussions
// Provides advanced tissue density visualization for medical imaging

class DicomTissueEnhancement {
    constructor(viewer) {
        this.viewer = viewer;
        this.enhancementActive = false;
        this.densityMap = null;
        this.enhancementLevel = 1.0;
        this.contrastBoost = 1.2;
        this.edgeEnhancement = 0.5;
        this.noiseReduction = 0.3;
        
        // Hounsfield Unit ranges for different tissues
        this.tissueRanges = {
            air: { min: -1000, max: -950, color: [0, 0, 0] },
            lung: { min: -950, max: -500, color: [64, 64, 64] },
            fat: { min: -200, max: -50, color: [255, 255, 128] },
            water: { min: -10, max: 10, color: [128, 128, 255] },
            muscle: { min: 10, max: 40, color: [255, 128, 128] },
            liver: { min: 40, max: 70, color: [255, 192, 128] },
            bone: { min: 200, max: 1000, color: [255, 255, 255] },
            metal: { min: 1000, max: 3000, color: [255, 255, 0] }
        };
        
        this.init();
    }
    
    init() {
        this.createEnhancementControls();
        this.setupEventListeners();
    }
    
    createEnhancementControls() {
        const controlsHTML = `
            <div class="tissue-enhancement-panel" id="tissue-enhancement-panel">
                <h4><i class="fas fa-microscope"></i> Tissue Enhancement</h4>
                
                <div class="enhancement-controls">
                    <div class="control-group">
                        <label>Enhancement Level:</label>
                        <input type="range" id="enhancement-level" min="0" max="2" step="0.1" value="1.0">
                        <span id="enhancement-level-value">1.0</span>
                    </div>
                    
                    <div class="control-group">
                        <label>Contrast Boost:</label>
                        <input type="range" id="contrast-boost" min="0.5" max="3" step="0.1" value="1.2">
                        <span id="contrast-boost-value">1.2</span>
                    </div>
                    
                    <div class="control-group">
                        <label>Edge Enhancement:</label>
                        <input type="range" id="edge-enhancement" min="0" max="1" step="0.1" value="0.5">
                        <span id="edge-enhancement-value">0.5</span>
                    </div>
                    
                    <div class="control-group">
                        <label>Noise Reduction:</label>
                        <input type="range" id="noise-reduction" min="0" max="1" step="0.1" value="0.3">
                        <span id="noise-reduction-value">0.3</span>
                    </div>
                </div>
                
                <div class="enhancement-buttons">
                    <button id="toggle-enhancement" class="tool-btn-enhanced">
                        <i class="fas fa-eye"></i> Toggle Enhancement
                    </button>
                    <button id="density-mapping" class="tool-btn-enhanced">
                        <i class="fas fa-map"></i> Density Map
                    </button>
                    <button id="reset-enhancement" class="tool-btn-enhanced">
                        <i class="fas fa-undo"></i> Reset
                    </button>
                </div>
                
                <div class="tissue-legend" id="tissue-legend">
                    <h5>Tissue Types (HU)</h5>
                    <div class="legend-items">
                        <div class="legend-item" data-tissue="air">
                            <div class="color-box" style="background: rgb(0,0,0)"></div>
                            <span>Air (-1000 to -950)</span>
                        </div>
                        <div class="legend-item" data-tissue="lung">
                            <div class="color-box" style="background: rgb(64,64,64)"></div>
                            <span>Lung (-950 to -500)</span>
                        </div>
                        <div class="legend-item" data-tissue="fat">
                            <div class="color-box" style="background: rgb(255,255,128)"></div>
                            <span>Fat (-200 to -50)</span>
                        </div>
                        <div class="legend-item" data-tissue="water">
                            <div class="color-box" style="background: rgb(128,128,255)"></div>
                            <span>Water (-10 to 10)</span>
                        </div>
                        <div class="legend-item" data-tissue="muscle">
                            <div class="color-box" style="background: rgb(255,128,128)"></div>
                            <span>Muscle (10 to 40)</span>
                        </div>
                        <div class="legend-item" data-tissue="liver">
                            <div class="color-box" style="background: rgb(255,192,128)"></div>
                            <span>Liver (40 to 70)</span>
                        </div>
                        <div class="legend-item" data-tissue="bone">
                            <div class="color-box" style="background: rgb(255,255,255)"></div>
                            <span>Bone (200 to 1000)</span>
                        </div>
                        <div class="legend-item" data-tissue="metal">
                            <div class="color-box" style="background: rgb(255,255,0)"></div>
                            <span>Metal (1000+)</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add to tool panel if it exists
        const toolPanel = document.querySelector('.tool-panel, .left-panel');
        if (toolPanel) {
            toolPanel.insertAdjacentHTML('beforeend', controlsHTML);
        }
    }
    
    setupEventListeners() {
        // Enhancement level control
        const enhancementLevel = document.getElementById('enhancement-level');
        if (enhancementLevel) {
            enhancementLevel.addEventListener('input', (e) => {
                this.enhancementLevel = parseFloat(e.target.value);
                document.getElementById('enhancement-level-value').textContent = this.enhancementLevel.toFixed(1);
                this.applyEnhancements();
            });
        }
        
        // Contrast boost control
        const contrastBoost = document.getElementById('contrast-boost');
        if (contrastBoost) {
            contrastBoost.addEventListener('input', (e) => {
                this.contrastBoost = parseFloat(e.target.value);
                document.getElementById('contrast-boost-value').textContent = this.contrastBoost.toFixed(1);
                this.applyEnhancements();
            });
        }
        
        // Edge enhancement control
        const edgeEnhancement = document.getElementById('edge-enhancement');
        if (edgeEnhancement) {
            edgeEnhancement.addEventListener('input', (e) => {
                this.edgeEnhancement = parseFloat(e.target.value);
                document.getElementById('edge-enhancement-value').textContent = this.edgeEnhancement.toFixed(1);
                this.applyEnhancements();
            });
        }
        
        // Noise reduction control
        const noiseReduction = document.getElementById('noise-reduction');
        if (noiseReduction) {
            noiseReduction.addEventListener('input', (e) => {
                this.noiseReduction = parseFloat(e.target.value);
                document.getElementById('noise-reduction-value').textContent = this.noiseReduction.toFixed(1);
                this.applyEnhancements();
            });
        }
        
        // Toggle enhancement button
        const toggleBtn = document.getElementById('toggle-enhancement');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                this.toggleEnhancement();
            });
        }
        
        // Density mapping button
        const densityBtn = document.getElementById('density-mapping');
        if (densityBtn) {
            densityBtn.addEventListener('click', () => {
                this.toggleDensityMapping();
            });
        }
        
        // Reset button
        const resetBtn = document.getElementById('reset-enhancement');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetEnhancements();
            });
        }
    }
    
    toggleEnhancement() {
        this.enhancementActive = !this.enhancementActive;
        const toggleBtn = document.getElementById('toggle-enhancement');
        
        if (this.enhancementActive) {
            toggleBtn.classList.add('active');
            toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i> Disable Enhancement';
            this.applyEnhancements();
        } else {
            toggleBtn.classList.remove('active');
            toggleBtn.innerHTML = '<i class="fas fa-eye"></i> Enable Enhancement';
            this.removeEnhancements();
        }
    }
    
    toggleDensityMapping() {
        const densityBtn = document.getElementById('density-mapping');
        const isActive = densityBtn.classList.contains('active');
        
        if (isActive) {
            densityBtn.classList.remove('active');
            this.removeDensityMapping();
        } else {
            densityBtn.classList.add('active');
            this.applyDensityMapping();
        }
    }
    
    applyEnhancements() {
        if (!this.enhancementActive || !this.viewer.canvas) return;
        
        const canvas = this.viewer.canvas;
        const ctx = canvas.getContext('2d');
        
        // Apply CSS filters for real-time enhancement
        const filters = [];
        
        // Contrast enhancement
        if (this.contrastBoost !== 1.0) {
            filters.push(`contrast(${this.contrastBoost})`);
        }
        
        // Brightness adjustment for better tissue differentiation
        const brightness = 1.0 + (this.enhancementLevel - 1.0) * 0.2;
        if (brightness !== 1.0) {
            filters.push(`brightness(${brightness})`);
        }
        
        // Saturation for better grayscale perception
        const saturation = 1.0 + (this.enhancementLevel - 1.0) * 0.1;
        if (saturation !== 1.0) {
            filters.push(`saturate(${saturation})`);
        }
        
        // Apply filters
        canvas.style.filter = filters.join(' ');
        
        // Show enhancement indicator
        this.showEnhancementIndicator();
    }
    
    applyDensityMapping() {
        if (!this.viewer.canvas || !this.viewer.imageData) return;
        
        const canvas = this.viewer.canvas;
        const ctx = canvas.getContext('2d');
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;
        
        // Create density-mapped version
        for (let i = 0; i < data.length; i += 4) {
            const gray = data[i]; // Assuming grayscale DICOM
            const hu = this.grayToHounsfieldUnit(gray);
            const tissueColor = this.getTissueColor(hu);
            
            // Apply tissue-specific coloring with transparency
            data[i] = Math.min(255, data[i] + tissueColor[0] * 0.3);     // Red
            data[i + 1] = Math.min(255, data[i + 1] + tissueColor[1] * 0.3); // Green  
            data[i + 2] = Math.min(255, data[i + 2] + tissueColor[2] * 0.3); // Blue
            // Alpha stays the same
        }
        
        ctx.putImageData(imageData, 0, 0);
        this.showDensityIndicator();
    }
    
    removeDensityMapping() {
        // Redraw original image
        if (this.viewer.currentImage) {
            this.viewer.drawImage();
        }
        this.hideDensityIndicator();
    }
    
    grayToHounsfieldUnit(grayValue) {
        // Convert grayscale value to approximate Hounsfield Unit
        // This is a simplified conversion - real DICOM has specific formulas
        return (grayValue - 128) * 8; // Approximate conversion
    }
    
    getTissueColor(hu) {
        for (const [tissue, range] of Object.entries(this.tissueRanges)) {
            if (hu >= range.min && hu <= range.max) {
                return range.color;
            }
        }
        return [128, 128, 128]; // Default gray
    }
    
    removeEnhancements() {
        if (this.viewer.canvas) {
            this.viewer.canvas.style.filter = 'none';
        }
        this.hideEnhancementIndicator();
    }
    
    resetEnhancements() {
        // Reset all controls to default values
        this.enhancementLevel = 1.0;
        this.contrastBoost = 1.2;
        this.edgeEnhancement = 0.5;
        this.noiseReduction = 0.3;
        
        // Update UI controls
        document.getElementById('enhancement-level').value = this.enhancementLevel;
        document.getElementById('enhancement-level-value').textContent = this.enhancementLevel.toFixed(1);
        document.getElementById('contrast-boost').value = this.contrastBoost;
        document.getElementById('contrast-boost-value').textContent = this.contrastBoost.toFixed(1);
        document.getElementById('edge-enhancement').value = this.edgeEnhancement;
        document.getElementById('edge-enhancement-value').textContent = this.edgeEnhancement.toFixed(1);
        document.getElementById('noise-reduction').value = this.noiseReduction;
        document.getElementById('noise-reduction-value').textContent = this.noiseReduction.toFixed(1);
        
        // Remove all enhancements
        this.removeEnhancements();
        this.removeDensityMapping();
        
        // Reset button states
        document.getElementById('toggle-enhancement').classList.remove('active');
        document.getElementById('density-mapping').classList.remove('active');
        
        this.enhancementActive = false;
    }
    
    showEnhancementIndicator() {
        let indicator = document.getElementById('enhancement-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'enhancement-indicator';
            indicator.className = 'enhancement-indicator';
            indicator.innerHTML = '<i class="fas fa-microscope"></i> Tissue Enhancement Active';
            document.body.appendChild(indicator);
        }
        indicator.style.display = 'block';
    }
    
    hideEnhancementIndicator() {
        const indicator = document.getElementById('enhancement-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
    
    showDensityIndicator() {
        let indicator = document.getElementById('density-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'density-indicator';
            indicator.className = 'density-indicator';
            indicator.innerHTML = '<i class="fas fa-map"></i> Density Mapping Active';
            document.body.appendChild(indicator);
        }
        indicator.style.display = 'block';
    }
    
    hideDensityIndicator() {
        const indicator = document.getElementById('density-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
    
    // Advanced tissue analysis
    analyzeTissueComposition(x, y, radius = 10) {
        if (!this.viewer.canvas) return null;
        
        const canvas = this.viewer.canvas;
        const ctx = canvas.getContext('2d');
        const imageData = ctx.getImageData(x - radius, y - radius, radius * 2, radius * 2);
        const data = imageData.data;
        
        const tissueComposition = {};
        let totalPixels = 0;
        
        for (let i = 0; i < data.length; i += 4) {
            const gray = data[i];
            const hu = this.grayToHounsfieldUnit(gray);
            
            for (const [tissue, range] of Object.entries(this.tissueRanges)) {
                if (hu >= range.min && hu <= range.max) {
                    tissueComposition[tissue] = (tissueComposition[tissue] || 0) + 1;
                    totalPixels++;
                    break;
                }
            }
        }
        
        // Convert to percentages
        for (const tissue in tissueComposition) {
            tissueComposition[tissue] = (tissueComposition[tissue] / totalPixels * 100).toFixed(1);
        }
        
        return tissueComposition;
    }
    
    // Export enhancement settings
    exportSettings() {
        return {
            enhancementLevel: this.enhancementLevel,
            contrastBoost: this.contrastBoost,
            edgeEnhancement: this.edgeEnhancement,
            noiseReduction: this.noiseReduction,
            enhancementActive: this.enhancementActive
        };
    }
    
    // Import enhancement settings
    importSettings(settings) {
        if (settings.enhancementLevel !== undefined) this.enhancementLevel = settings.enhancementLevel;
        if (settings.contrastBoost !== undefined) this.contrastBoost = settings.contrastBoost;
        if (settings.edgeEnhancement !== undefined) this.edgeEnhancement = settings.edgeEnhancement;
        if (settings.noiseReduction !== undefined) this.noiseReduction = settings.noiseReduction;
        if (settings.enhancementActive !== undefined) this.enhancementActive = settings.enhancementActive;
        
        this.updateUIControls();
        if (this.enhancementActive) {
            this.applyEnhancements();
        }
    }
    
    updateUIControls() {
        // Update all UI controls to match current settings
        const controls = {
            'enhancement-level': this.enhancementLevel,
            'contrast-boost': this.contrastBoost,
            'edge-enhancement': this.edgeEnhancement,
            'noise-reduction': this.noiseReduction
        };
        
        for (const [id, value] of Object.entries(controls)) {
            const control = document.getElementById(id);
            const valueDisplay = document.getElementById(id + '-value');
            if (control) control.value = value;
            if (valueDisplay) valueDisplay.textContent = value.toFixed(1);
        }
    }
}

// Global initialization function
function initializeTissueEnhancement(viewer) {
    if (!window.tissueEnhancement) {
        window.tissueEnhancement = new DicomTissueEnhancement(viewer);
        console.log('✅ Tissue Enhancement module initialized');
    }
    return window.tissueEnhancement;
}

// CSS for enhancement indicators
const enhancementCSS = `
.tissue-enhancement-panel {
    background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
    border: 1px solid rgba(0, 255, 136, 0.3);
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
}

.tissue-enhancement-panel h4 {
    color: #00ff88;
    margin: 0 0 15px 0;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.enhancement-controls {
    margin-bottom: 15px;
}

.enhancement-buttons {
    display: flex;
    gap: 5px;
    margin-bottom: 15px;
    flex-wrap: wrap;
}

.tissue-legend {
    background: rgba(0, 0, 0, 0.3);
    border-radius: 6px;
    padding: 10px;
}

.tissue-legend h5 {
    color: #9ca3af;
    margin: 0 0 10px 0;
    font-size: 12px;
}

.legend-items {
    display: grid;
    gap: 5px;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    color: #e0e6ed;
    cursor: pointer;
    padding: 2px;
    border-radius: 3px;
    transition: background 0.2s;
}

.legend-item:hover {
    background: rgba(255, 255, 255, 0.1);
}

.color-box {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid rgba(255, 255, 255, 0.3);
}

.enhancement-indicator, .density-indicator {
    position: fixed;
    top: 80px;
    right: 20px;
    background: rgba(0, 255, 136, 0.9);
    color: #0a0a0a;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: bold;
    z-index: 1000;
    display: none;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.density-indicator {
    top: 110px;
    background: rgba(59, 130, 246, 0.9);
    color: #ffffff;
}
`;

// Inject CSS
if (!document.getElementById('tissue-enhancement-css')) {
    const style = document.createElement('style');
    style.id = 'tissue-enhancement-css';
    style.textContent = enhancementCSS;
    document.head.appendChild(style);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DicomTissueEnhancement;
}