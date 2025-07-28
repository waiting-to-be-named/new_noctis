// static/js/worklist.js

class WorklistManager {
    constructor() {
        this.currentStudyId = null;
        this.notifications = [];
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupFilters();
        this.loadNotifications();
        this.startNotificationPolling();
    }
    
    setupEventListeners() {
        // Launch viewer button
        document.getElementById('launch-viewer-btn').addEventListener('click', () => {
            this.launchViewer();
        });
        
        // Study row clicks
        document.querySelectorAll('.study-row').forEach(row => {
            row.addEventListener('click', (e) => {
                if (!e.target.closest('.action-btn')) {
                    this.selectStudy(row);
                }
            });
        });
        
        // Action buttons
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const studyId = btn.dataset.studyId;
                this.viewStudy(studyId);
            });
        });
        
        document.querySelectorAll('.clinical-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const studyId = btn.dataset.studyId;
                this.showClinicalModal(studyId);
            });
        });
        
        document.querySelectorAll('.report-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const studyId = btn.dataset.studyId;
                this.showReportModal(studyId);
            });
        });
        
        document.querySelectorAll('.print-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const studyId = btn.dataset.studyId;
                this.printReport(studyId);
            });
        });
        
        // Modal events
        this.setupModalEvents();
        
        // Clear filters
        document.getElementById('clear-filters').addEventListener('click', () => {
            this.clearFilters();
        });
    }
    
    setupFilters() {
        const modalityFilter = document.getElementById('modality-filter');
        const dateFilter = document.getElementById('date-filter');
        const searchFilter = document.getElementById('search-filter');
        
        [modalityFilter, dateFilter, searchFilter].forEach(filter => {
            filter.addEventListener('change', () => this.applyFilters());
            filter.addEventListener('input', () => this.applyFilters());
        });
    }
    
    applyFilters() {
        const modality = document.getElementById('modality-filter').value;
        const date = document.getElementById('date-filter').value;
        const search = document.getElementById('search-filter').value.toLowerCase();
        
        document.querySelectorAll('.study-row').forEach(row => {
            const rowModality = row.dataset.modality;
            const rowDate = row.dataset.date;
            const patientName = row.querySelector('.patient-name').textContent.toLowerCase();
            const patientId = row.querySelector('.patient-id').textContent.toLowerCase();
            
            let show = true;
            
            // Modality filter
            if (modality && rowModality !== modality) {
                show = false;
            }
            
            // Date filter
            if (date && rowDate !== date) {
                show = false;
            }
            
            // Search filter
            if (search && !patientName.includes(search) && !patientId.includes(search)) {
                show = false;
            }
            
            row.style.display = show ? 'table-row' : 'none';
        });
    }
    
    clearFilters() {
        document.getElementById('modality-filter').value = '';
        document.getElementById('date-filter').value = '';
        document.getElementById('search-filter').value = '';
        this.applyFilters();
    }
    
    selectStudy(row) {
        // Remove previous selection
        document.querySelectorAll('.study-row').forEach(r => {
            r.classList.remove('selected');
        });
        
        // Add selection to current row
        row.classList.add('selected');
        this.currentStudyId = row.dataset.studyId;
    }
    
    launchViewer() {
        if (this.currentStudyId) {
            // Open viewer with selected study
            window.open(`/?study=${this.currentStudyId}`, '_blank');
        } else {
            // Open viewer without specific study
            window.open('/', '_blank');
        }
    }
    
    viewStudy(studyId) {
        window.open(`/?study=${studyId}`, '_blank');
    }
    
    showClinicalModal(studyId) {
        this.currentStudyId = studyId;
        const modal = document.getElementById('clinical-modal');
        modal.style.display = 'flex';
        
        // Load existing clinical notes
        this.loadClinicalNotes(studyId);
    }
    
    showReportModal(studyId) {
        this.currentStudyId = studyId;
        const modal = document.getElementById('report-modal');
        modal.style.display = 'flex';
        
        // Load existing report if available
        this.loadExistingReport(studyId);
    }
    
    setupModalEvents() {
        // Clinical modal
        const clinicalModal = document.getElementById('clinical-modal');
        const clinicalForm = document.getElementById('clinical-form');
        const cancelClinical = document.getElementById('cancel-clinical');
        
        clinicalModal.querySelector('.modal-close').addEventListener('click', () => {
            clinicalModal.style.display = 'none';
        });
        
        cancelClinical.addEventListener('click', () => {
            clinicalModal.style.display = 'none';
        });
        
        clinicalForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveClinicalNotes();
        });
        
        // Report modal
        const reportModal = document.getElementById('report-modal');
        const reportForm = document.getElementById('report-form');
        const cancelReport = document.getElementById('cancel-report');
        
        reportModal.querySelector('.modal-close').addEventListener('click', () => {
            reportModal.style.display = 'none';
        });
        
        cancelReport.addEventListener('click', () => {
            reportModal.style.display = 'none';
        });
        
        reportForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveReport();
        });
        
        // Close modals when clicking outside
        [clinicalModal, reportModal].forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        });
    }
    
    async loadClinicalNotes(studyId) {
        try {
            const response = await fetch(`/api/studies/${studyId}/clinical-notes/`);
            if (response.ok) {
                const data = await response.json();
                document.getElementById('clinical-notes').value = data.clinical_notes || '';
            }
        } catch (error) {
            console.error('Error loading clinical notes:', error);
        }
    }
    
    async saveClinicalNotes() {
        if (!this.currentStudyId) return;
        
        const notes = document.getElementById('clinical-notes').value;
        
        try {
            const response = await fetch(`/api/studies/${this.currentStudyId}/clinical-notes/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ clinical_notes: notes })
            });
            
            if (response.ok) {
                document.getElementById('clinical-modal').style.display = 'none';
                this.showNotification('Clinical notes saved successfully', 'success');
            } else {
                throw new Error('Failed to save clinical notes');
            }
        } catch (error) {
            console.error('Error saving clinical notes:', error);
            this.showNotification('Failed to save clinical notes', 'error');
        }
    }
    
    async loadExistingReport(studyId) {
        try {
            const response = await fetch(`/api/studies/${studyId}/reports/`);
            if (response.ok) {
                const reports = await response.json();
                if (reports.length > 0) {
                    const latestReport = reports[0];
                    document.getElementById('report-title').value = latestReport.title;
                    document.getElementById('report-status').value = latestReport.status;
                    document.getElementById('report-findings').value = latestReport.findings;
                    document.getElementById('report-impression').value = latestReport.impression;
                }
            }
        } catch (error) {
            console.error('Error loading existing report:', error);
        }
    }
    
    async saveReport() {
        if (!this.currentStudyId) return;
        
        const reportData = {
            title: document.getElementById('report-title').value,
            status: document.getElementById('report-status').value,
            findings: document.getElementById('report-findings').value,
            impression: document.getElementById('report-impression').value
        };
        
        try {
            const response = await fetch(`/api/studies/${this.currentStudyId}/reports/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(reportData)
            });
            
            if (response.ok) {
                document.getElementById('report-modal').style.display = 'none';
                this.showNotification('Report saved successfully', 'success');
                this.refreshStudyStatus(this.currentStudyId);
            } else {
                throw new Error('Failed to save report');
            }
        } catch (error) {
            console.error('Error saving report:', error);
            this.showNotification('Failed to save report', 'error');
        }
    }
    
    async printReport(studyId) {
        try {
            const response = await fetch(`/api/studies/${studyId}/reports/`);
            if (response.ok) {
                const reports = await response.json();
                if (reports.length > 0) {
                    // Open print window with report
                    const printWindow = window.open('', '_blank');
                    printWindow.document.write(this.generateReportHTML(reports[0]));
                    printWindow.document.close();
                    printWindow.print();
                } else {
                    this.showNotification('No report available to print', 'warning');
                }
            }
        } catch (error) {
            console.error('Error printing report:', error);
            this.showNotification('Failed to print report', 'error');
        }
    }
    
    generateReportHTML(report) {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Radiology Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .header { text-align: center; margin-bottom: 30px; }
                    .report-content { margin: 20px 0; }
                    .section { margin: 20px 0; }
                    .section h3 { color: #333; border-bottom: 2px solid #0078d4; }
                    .footer { margin-top: 40px; text-align: center; font-size: 12px; color: #666; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Radiology Report</h1>
                    <p>Generated on ${new Date().toLocaleDateString()}</p>
                </div>
                <div class="report-content">
                    <div class="section">
                        <h3>Findings</h3>
                        <p>${report.findings || 'No findings recorded.'}</p>
                    </div>
                    <div class="section">
                        <h3>Impression</h3>
                        <p>${report.impression || 'No impression recorded.'}</p>
                    </div>
                </div>
                <div class="footer">
                    <p>Report Status: ${report.status.toUpperCase()}</p>
                    <p>Generated by: ${report.created_by}</p>
                </div>
            </body>
            </html>
        `;
    }
    
    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications/');
            if (response.ok) {
                const data = await response.json();
                this.notifications = data.notifications;
                this.updateNotificationBadge();
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }
    
    updateNotificationBadge() {
        const unreadCount = this.notifications.length;
        // You can add a notification badge to the header here
        if (unreadCount > 0) {
            this.showNotificationPanel();
        }
    }
    
    showNotificationPanel() {
        const panel = document.getElementById('notifications-panel');
        const list = document.getElementById('notifications-list');
        
        list.innerHTML = '';
        this.notifications.forEach(notification => {
            const notificationElement = document.createElement('div');
            notificationElement.className = 'notification-item';
            notificationElement.innerHTML = `
                <div class="notification-header">
                    <strong>${notification.title}</strong>
                    <button class="mark-read-btn" data-id="${notification.id}">&times;</button>
                </div>
                <div class="notification-message">${notification.message}</div>
                <div class="notification-time">${new Date(notification.created_at).toLocaleString()}</div>
            `;
            list.appendChild(notificationElement);
        });
        
        panel.classList.add('show');
    }
    
    startNotificationPolling() {
        // Poll for new notifications every 30 seconds
        setInterval(() => {
            this.loadNotifications();
        }, 30000);
    }
    
    showNotification(message, type = 'info') {
        // Create a simple notification toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            z-index: 3000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
    
    refreshStudyStatus(studyId) {
        // Update the status badge for the study
        const row = document.querySelector(`[data-study-id="${studyId}"]`);
        if (row) {
            const statusCell = row.querySelector('.status');
            statusCell.innerHTML = '<span class="status-badge completed">Report Ready</span>';
        }
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}

// Initialize the worklist manager when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new WorklistManager();
});

// Add CSS animations for notifications
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
    
    .notification-item {
        background: #444;
        border-radius: 4px;
        padding: 12px;
        margin-bottom: 10px;
        border-left: 3px solid #0078d4;
    }
    
    .notification-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .notification-message {
        color: #ccc;
        font-size: 14px;
        margin-bottom: 8px;
    }
    
    .notification-time {
        color: #666;
        font-size: 12px;
    }
    
    .mark-read-btn {
        background: none;
        border: none;
        color: #ccc;
        cursor: pointer;
        font-size: 16px;
    }
    
    .mark-read-btn:hover {
        color: white;
    }
`;
document.head.appendChild(style);