// static/js/worklist.js

class WorklistManager {
    constructor() {
        this.selectedStudyId = null;
        this.currentStudy = null;
        this.notifications = [];
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadNotifications();
        this.setupSearch();
        this.setupFilters();
        
        // Refresh notifications every 30 seconds
        setInterval(() => this.loadNotifications(), 30000);
    }
    
    setupEventListeners() {
        // Notification bell
        document.getElementById('notification-bell').addEventListener('click', () => {
            this.toggleNotificationsPanel();
        });
        
        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            location.reload();
        });
        
        // Clinical form
        const clinicalForm = document.getElementById('clinical-form');
        if (clinicalForm) {
            clinicalForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveClinicalInfo();
            });
        }
        
        // Report form
        const reportForm = document.getElementById('report-form');
        if (reportForm) {
            reportForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveReport();
            });
        }
        
        // Close modals on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });
    }
    
    setupSearch() {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterTable(e.target.value);
            });
        }
    }
    
    setupFilters() {
        const filters = ['date-from', 'date-to', 'modality-filter', 'status-filter'];
        filters.forEach(filterId => {
            const element = document.getElementById(filterId);
            if (element) {
                element.addEventListener('change', () => {
                    this.applyFilters();
                });
            }
        });
    }
    
    filterTable(searchTerm) {
        const rows = document.querySelectorAll('.study-row');
        const term = searchTerm.toLowerCase();
        
        rows.forEach(row => {
            const patientName = row.querySelector('.patient-name').textContent.toLowerCase();
            const patientId = row.querySelector('.patient-id').textContent.toLowerCase();
            const description = row.querySelector('.description').textContent.toLowerCase();
            
            if (patientName.includes(term) || patientId.includes(term) || description.includes(term)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
    
    applyFilters() {
        const dateFrom = document.getElementById('date-from').value;
        const dateTo = document.getElementById('date-to').value;
        const modalityFilter = document.getElementById('modality-filter').value;
        const statusFilter = document.getElementById('status-filter').value;
        
        const rows = document.querySelectorAll('.study-row');
        
        rows.forEach(row => {
            let show = true;
            
            // Date filtering
            if (dateFrom || dateTo) {
                const studyDate = row.querySelector('.study-date').textContent;
                const studyDateObj = new Date(studyDate);
                
                if (dateFrom && studyDateObj < new Date(dateFrom)) show = false;
                if (dateTo && studyDateObj > new Date(dateTo)) show = false;
            }
            
            // Modality filtering
            if (modalityFilter) {
                const modality = row.querySelector('.modality-badge').textContent;
                if (modality !== modalityFilter) show = false;
            }
            
            // Status filtering
            if (statusFilter) {
                const status = row.querySelector('.status-badge').textContent.toLowerCase();
                if (!status.includes(statusFilter)) show = false;
            }
            
            row.style.display = show ? '' : 'none';
        });
    }
    
    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications/', {
                headers: {
                    'Authorization': 'Bearer ' + (localStorage.getItem('token') || ''),
                }
            });
            
            if (response.ok) {
                this.notifications = await response.json();
                this.updateNotificationUI();
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }
    
    updateNotificationUI() {
        const countElement = document.getElementById('notification-count');
        const unreadCount = this.notifications.length;
        
        countElement.textContent = unreadCount;
        countElement.style.display = unreadCount > 0 ? 'flex' : 'none';
        
        // Update notifications panel content
        const content = document.getElementById('notifications-content');
        if (content) {
            content.innerHTML = this.renderNotifications();
        }
    }
    
    renderNotifications() {
        if (this.notifications.length === 0) {
            return '<div class="no-notifications">No new notifications</div>';
        }
        
        return this.notifications.map(notification => `
            <div class="notification-item" data-id="${notification.id}">
                <div class="notification-header">
                    <strong>${notification.title}</strong>
                    <small>${this.formatDate(notification.created_at)}</small>
                </div>
                <div class="notification-message">${notification.message}</div>
                <div class="notification-actions">
                    ${notification.study_id ? `
                        <button class="btn btn-sm btn-primary" onclick="worklistManager.viewStudyFromNotification(${notification.study_id})">
                            View Study
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-secondary" onclick="worklistManager.markNotificationRead(${notification.id})">
                        Mark Read
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    toggleNotificationsPanel() {
        const panel = document.getElementById('notifications-panel');
        panel.classList.toggle('open');
    }
    
    closeNotificationsPanel() {
        document.getElementById('notifications-panel').classList.remove('open');
    }
    
    async markNotificationRead(notificationId) {
        try {
            const response = await fetch(`/api/notifications/${notificationId}/read/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.notifications = this.notifications.filter(n => n.id !== notificationId);
                this.updateNotificationUI();
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }
    
    viewStudyFromNotification(studyId) {
        this.closeNotificationsPanel();
        viewStudy(studyId);
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }
    
    async loadStudyDetails(studyId) {
        try {
            const response = await fetch(`/api/studies/${studyId}/images/`);
            if (response.ok) {
                const data = await response.json();
                this.currentStudy = data.study;
                this.showStudyDetails(data);
            }
        } catch (error) {
            console.error('Error loading study details:', error);
        }
    }
    
    showStudyDetails(data) {
        const panel = document.getElementById('details-panel');
        const content = document.getElementById('panel-content');
        
        content.innerHTML = `
            <div class="study-details">
                <h4>Patient Information</h4>
                <div class="detail-row">
                    <label>Name:</label>
                    <span>${data.study.patient_name}</span>
                </div>
                <div class="detail-row">
                    <label>ID:</label>
                    <span>${data.study.patient_id}</span>
                </div>
                <div class="detail-row">
                    <label>Study Date:</label>
                    <span>${data.study.study_date}</span>
                </div>
                <div class="detail-row">
                    <label>Modality:</label>
                    <span>${data.study.modality}</span>
                </div>
                <div class="detail-row">
                    <label>Description:</label>
                    <span>${data.study.study_description || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <label>Institution:</label>
                    <span>${data.study.institution_name || 'N/A'}</span>
                </div>
                
                <h4>Series Information</h4>
                <div class="series-list">
                    ${this.renderSeriesList(data.images)}
                </div>
                
                <div class="detail-actions">
                    <button class="btn btn-primary" onclick="worklistManager.openClinicalModal(${data.study.id})">
                        <i class="fas fa-user-md"></i> Clinical Info
                    </button>
                    <button class="btn btn-secondary" onclick="viewStudy(${data.study.id})">
                        <i class="fas fa-eye"></i> View Images
                    </button>
                </div>
            </div>
        `;
        
        panel.classList.add('open');
    }
    
    renderSeriesList(images) {
        const seriesMap = {};
        images.forEach(image => {
            if (!seriesMap[image.series_number]) {
                seriesMap[image.series_number] = {
                    description: image.series_description,
                    count: 0
                };
            }
            seriesMap[image.series_number].count++;
        });
        
        return Object.entries(seriesMap).map(([seriesNum, info]) => `
            <div class="series-item">
                <strong>Series ${seriesNum}:</strong> ${info.description} (${info.count} images)
            </div>
        `).join('');
    }
    
    closeDetailsPanel() {
        document.getElementById('details-panel').classList.remove('open');
    }
    
    openClinicalModal(studyId) {
        this.selectedStudyId = studyId;
        document.getElementById('clinical-modal').style.display = 'flex';
        this.loadClinicalInfo(studyId);
    }
    
    async loadClinicalInfo(studyId) {
        try {
            const response = await fetch(`/api/studies/${studyId}/clinical-info/`);
            if (response.ok) {
                const data = await response.json();
                this.populateClinicalForm(data);
            }
        } catch (error) {
            console.error('Error loading clinical info:', error);
        }
    }
    
    populateClinicalForm(data) {
        document.getElementById('patient-age').value = data.patient_age || '';
        document.getElementById('patient-sex').value = data.patient_sex || '';
        document.getElementById('patient-weight').value = data.patient_weight || '';
        document.getElementById('patient-height').value = data.patient_height || '';
        document.getElementById('referring-physician').value = data.referring_physician || '';
        document.getElementById('clinical-history').value = data.clinical_history || '';
        document.getElementById('indication').value = data.indication || '';
        document.getElementById('contrast-agent').value = data.contrast_agent || '';
    }
    
    async saveClinicalInfo() {
        const formData = {
            patient_age: document.getElementById('patient-age').value,
            patient_sex: document.getElementById('patient-sex').value,
            patient_weight: parseFloat(document.getElementById('patient-weight').value) || null,
            patient_height: parseFloat(document.getElementById('patient-height').value) || null,
            referring_physician: document.getElementById('referring-physician').value,
            clinical_history: document.getElementById('clinical-history').value,
            indication: document.getElementById('indication').value,
            contrast_agent: document.getElementById('contrast-agent').value
        };
        
        try {
            const response = await fetch(`/api/studies/${this.selectedStudyId}/clinical-info/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                this.showMessage('Clinical information saved successfully', 'success');
                this.closeClinicalModal();
            } else {
                throw new Error('Failed to save clinical information');
            }
        } catch (error) {
            console.error('Error saving clinical info:', error);
            this.showMessage('Error saving clinical information', 'error');
        }
    }
    
    closeClinicalModal() {
        document.getElementById('clinical-modal').style.display = 'none';
    }
    
    openReportModal(studyId) {
        this.selectedStudyId = studyId;
        document.getElementById('report-modal').style.display = 'flex';
        this.loadReport(studyId);
    }
    
    async loadReport(studyId) {
        try {
            const response = await fetch(`/api/studies/${studyId}/report/`);
            if (response.ok) {
                const data = await response.json();
                this.populateReportForm(data);
            }
        } catch (error) {
            console.error('Error loading report:', error);
        }
    }
    
    populateReportForm(data) {
        document.getElementById('report-findings').value = data.findings || '';
        document.getElementById('report-impression').value = data.impression || '';
        document.getElementById('report-recommendations').value = data.recommendations || '';
        document.getElementById('report-status').value = data.status || 'draft';
    }
    
    async saveReport() {
        const formData = {
            findings: document.getElementById('report-findings').value,
            impression: document.getElementById('report-impression').value,
            recommendations: document.getElementById('report-recommendations').value,
            status: document.getElementById('report-status').value
        };
        
        try {
            const response = await fetch(`/api/studies/${this.selectedStudyId}/report/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                this.showMessage('Report saved successfully', 'success');
                this.closeReportModal();
                
                // If finalized, show print option
                if (formData.status === 'finalized') {
                    this.showPrintOption();
                }
            } else {
                throw new Error('Failed to save report');
            }
        } catch (error) {
            console.error('Error saving report:', error);
            this.showMessage('Error saving report', 'error');
        }
    }
    
    closeReportModal() {
        document.getElementById('report-modal').style.display = 'none';
    }
    
    showPrintOption() {
        if (confirm('Report finalized! Would you like to print it now?')) {
            this.printReport();
        }
    }
    
    printReport() {
        // Create a print-friendly version of the report
        const printWindow = window.open('', '_blank');
        const reportContent = this.generatePrintableReport();
        
        printWindow.document.write(reportContent);
        printWindow.document.close();
        printWindow.print();
    }
    
    generatePrintableReport() {
        const findings = document.getElementById('report-findings').value;
        const impression = document.getElementById('report-impression').value;
        const recommendations = document.getElementById('report-recommendations').value;
        
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Radiology Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .header { text-align: center; margin-bottom: 30px; }
                    .section { margin: 20px 0; }
                    .section h3 { color: #333; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
                    .content { margin: 10px 0; line-height: 1.6; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>RADIOLOGY REPORT</h1>
                    <p>Patient: ${this.currentStudy?.patient_name || 'N/A'}</p>
                    <p>Study Date: ${this.currentStudy?.study_date || 'N/A'}</p>
                    <p>Modality: ${this.currentStudy?.modality || 'N/A'}</p>
                </div>
                
                <div class="section">
                    <h3>FINDINGS</h3>
                    <div class="content">${findings || 'No findings documented.'}</div>
                </div>
                
                <div class="section">
                    <h3>IMPRESSION</h3>
                    <div class="content">${impression || 'No impression documented.'}</div>
                </div>
                
                <div class="section">
                    <h3>RECOMMENDATIONS</h3>
                    <div class="content">${recommendations || 'No recommendations documented.'}</div>
                </div>
                
                <div class="section">
                    <p><strong>Report Date:</strong> ${new Date().toLocaleDateString()}</p>
                    <p><strong>Radiologist:</strong> Dr. [Name]</p>
                </div>
            </body>
            </html>
        `;
    }
    
    closeAllModals() {
        document.getElementById('clinical-modal').style.display = 'none';
        const reportModal = document.getElementById('report-modal');
        if (reportModal) {
            reportModal.style.display = 'none';
        }
        this.closeDetailsPanel();
        this.closeNotificationsPanel();
    }
    
    showMessage(message, type = 'info') {
        // Create a simple toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 4px;
            color: white;
            font-weight: 500;
            z-index: 9999;
            background-color: ${type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#3498db'};
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || '';
    }
}

// Global functions for template use
function selectStudy(row) {
    // Remove previous selection
    document.querySelectorAll('.study-row').forEach(r => r.classList.remove('selected'));
    
    // Add selection to current row
    row.classList.add('selected');
    
    const studyId = parseInt(row.dataset.studyId);
    worklistManager.selectedStudyId = studyId;
    worklistManager.loadStudyDetails(studyId);
}

function viewStudy(studyId) {
    window.location.href = `/launch-viewer/${studyId}/`;
}

function openReportModal(studyId) {
    worklistManager.openReportModal(studyId);
}

function closeDetailsPanel() {
    worklistManager.closeDetailsPanel();
}

function closeClinicalModal() {
    worklistManager.closeClinicalModal();
}

function closeReportModal() {
    worklistManager.closeReportModal();
}

function closeNotificationsPanel() {
    worklistManager.closeNotificationsPanel();
}

// Initialize the worklist manager when the page loads
let worklistManager;
document.addEventListener('DOMContentLoaded', () => {
    worklistManager = new WorklistManager();
});