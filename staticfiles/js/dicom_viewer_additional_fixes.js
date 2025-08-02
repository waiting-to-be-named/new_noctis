
// Additional DICOM Viewer Fixes
(function() {
    'use strict';
    
    console.log('Applying additional DICOM viewer fixes...');
    
    // Ensure buttons work even without backend data
    window.addEventListener('DOMContentLoaded', function() {
        // Fix logout button
        const logoutBtn = document.getElementById('logout-advanced-btn');
        if (logoutBtn && !logoutBtn.onclick) {
            logoutBtn.onclick = function() {
                if (confirm('Are you sure you want to logout?')) {
                    window.location.href = '/accounts/logout/';
                }
            };
        }
        
        // Fix back to worklist button
        const backBtn = document.getElementById('back-to-worklist-btn');
        if (backBtn && !backBtn.onclick) {
            backBtn.onclick = function() {
                window.location.href = '/worklist/';
            };
        }
        
        // Fix fullscreen button
        const fullscreenBtn = document.getElementById('fullscreen-btn');
        if (fullscreenBtn && !fullscreenBtn.onclick) {
            fullscreenBtn.onclick = function() {
                if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen();
                    this.innerHTML = '<i class="fas fa-compress"></i>';
                } else {
                    document.exitFullscreen();
                    this.innerHTML = '<i class="fas fa-expand"></i>';
                }
            };
        }
        
        // Create demo image if no real images
        const canvas = document.getElementById('dicom-canvas-advanced');
        if (canvas && !window.currentDicomImage) {
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#000';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#fff';
            ctx.font = '20px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No DICOM image loaded', canvas.width/2, canvas.height/2);
            ctx.fillText('Use Upload button to load images', canvas.width/2, canvas.height/2 + 30);
        }
        
        // Show notification system is working
        if (window.showNotification) {
            window.showNotification('DICOM Viewer initialized', 'success');
        }
    });
})();
