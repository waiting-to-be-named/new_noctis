// Worklist JavaScript
let currentPage = 1;
let totalPages = 1;
let studies = [];
let currentFilters = {};
let selectedStudyId = null;

// Initialize worklist
document.addEventListener('DOMContentLoaded', function() {
    loadStudies();
    setupEventListeners();
    startNotificationPolling();
    
    // Set today's date as default for date filters
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('date-to').value = today;
});

function setupEventListeners() {
    // Notification badge click
    document.getElementById('notification-badge').addEventListener('click', toggleNotifications);
    
    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    });
    
    // Click outside modal to close
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.style.display = 'none';
            }
        });
    });
}

async function loadStudies(page = 1) {
    currentPage = page;
    
    try {
        const params = new URLSearchParams({
            page: page,
            ...currentFilters
        });
        
        const response = await fetch(`/api/worklist/studies?${params}`);
        const data = await response.json();
        
        studies = data.studies;
        totalPages = data.total_pages;
        
        renderStudies();
        updatePagination();
    } catch (error) {
        console.error('Error loading studies:', error);
        showNotification('Error loading studies', 'error');
    }
}

function renderStudies() {
    const tbody = document.getElementById('patient-list');
    tbody.innerHTML = '';
    
    if (studies.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 2rem;">No studies found</td></tr>';
        return;
    }
    
    studies.forEach(study => {
        const row = document.createElement('tr');
        row.dataset.studyId = study.id;
        row.innerHTML = `
            <td>${study.patient_name}</td>
            <td>${study.patient_id}</td>
            <td>${formatDate(study.study_date)}</td>
            <td>${study.modality}</td>
            <td>${study.study_description || '-'}</td>
            <td><span class="urgency-badge urgency-${study.urgency}">${study.urgency.toUpperCase()}</span></td>
            <td><span class="status-badge status-${study.report_status.replace('_', '-')}">${formatStatus(study.report_status)}</span></td>
            <td>${study.facility_name || '-'}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn-action btn-view" onclick="viewStudy(${study.id})">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="btn-action" onclick="openClinicalModal(${study.id})">
                        <i class="fas fa-file-medical"></i> Clinical
                    </button>
                    ${canWriteReport() ? `
                        <button class="btn-action" onclick="openReportModal(${study.id})">
                            <i class="fas fa-file-alt"></i> Report
                        </button>
                    ` : ''}
                    ${study.report_status === 'completed' || study.report_status === 'verified' ? `
                        <button class="btn-action" onclick="printReport(${study.id})">
                            <i class="fas fa-print"></i> Print
                        </button>
                    ` : ''}
                </div>
            </td>
        `;
        
        // Add click event for row selection
        row.addEventListener('click', function(e) {
            if (!e.target.closest('.btn-action')) {
                selectRow(this);
            }
        });
        
        tbody.appendChild(row);
    });
}

function selectRow(row) {
    // Remove previous selection
    document.querySelectorAll('.worklist-table tbody tr').forEach(r => {
        r.classList.remove('selected');
    });
    
    // Add selection to clicked row
    row.classList.add('selected');
    selectedStudyId = row.dataset.studyId;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatStatus(status) {
    return status.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function canWriteReport() {
    // Check if user has permission to write reports
    const userRole = document.querySelector('.user-role')?.textContent;
    return userRole === 'Radiologist' || userRole === 'Administrator';
}

async function viewStudy(studyId) {
    // Launch DICOM viewer with the study
    window.location.href = `/viewer/?study_id=${studyId}`;
}

function openClinicalModal(studyId) {
    const study = studies.find(s => s.id === studyId);
    if (!study) return;
    
    document.getElementById('study-id').value = studyId;
    document.getElementById('clinical-history').value = study.clinical_history || '';
    document.getElementById('indication').value = study.indication || '';
    document.getElementById('referring-physician').value = study.referring_physician || '';
    document.getElementById('urgency').value = study.urgency;
    
    document.getElementById('clinical-modal').style.display = 'flex';
}

function closeClinicalModal() {
    document.getElementById('clinical-modal').style.display = 'none';
}

async function saveClinicalInfo() {
    const formData = new FormData(document.getElementById('clinical-form'));
    
    try {
        const response = await fetch('/api/worklist/clinical-info', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (response.ok) {
            showNotification('Clinical information saved', 'success');
            closeClinicalModal();
            loadStudies(currentPage);
        } else {
            showNotification('Error saving clinical information', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error saving clinical information', 'error');
    }
}

async function openReportModal(studyId) {
    const study = studies.find(s => s.id === studyId);
    if (!study) return;
    
    document.getElementById('report-study-id').value = studyId;
    
    // Load facility letterhead
    if (study.facility_logo) {
        document.getElementById('report-header').innerHTML = `
            <img src="${study.facility_logo}" alt="${study.facility_name}">
            <h2>${study.facility_name}</h2>
            <p>${study.facility_address || ''}</p>
        `;
    }
    
    // Load patient information
    document.getElementById('report-patient-info').innerHTML = `
        <div><strong>Patient Name:</strong> ${study.patient_name}</div>
        <div><strong>Patient ID:</strong> ${study.patient_id}</div>
        <div><strong>Study Date:</strong> ${formatDate(study.study_date)}</div>
        <div><strong>Modality:</strong> ${study.modality}</div>
        <div><strong>Study Description:</strong> ${study.study_description || '-'}</div>
        <div><strong>Referring Physician:</strong> ${study.referring_physician || '-'}</div>
    `;
    
    // Load existing report if any
    try {
        const response = await fetch(`/api/worklist/report/${studyId}`);
        if (response.ok) {
            const report = await response.json();
            document.getElementById('findings').value = report.findings || '';
            document.getElementById('impression').value = report.impression || '';
            document.getElementById('recommendations').value = report.recommendations || '';
        }
    } catch (error) {
        console.error('Error loading report:', error);
    }
    
    document.getElementById('report-modal').style.display = 'flex';
}

function closeReportModal() {
    document.getElementById('report-modal').style.display = 'none';
}

async function saveReportDraft() {
    await saveReport('draft');
}

async function finalizeReport() {
    if (!confirm('Are you sure you want to finalize this report? This action cannot be undone.')) {
        return;
    }
    await saveReport('finalized');
}

async function saveReport(status) {
    const formData = new FormData(document.getElementById('report-form'));
    formData.append('status', status);
    
    try {
        const response = await fetch('/api/worklist/report', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (response.ok) {
            showNotification(`Report ${status === 'draft' ? 'saved as draft' : 'finalized'}`, 'success');
            closeReportModal();
            loadStudies(currentPage);
        } else {
            showNotification('Error saving report', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error saving report', 'error');
    }
}

async function printReport(studyId) {
    // Open report in print mode
    window.open(`/api/worklist/report/${studyId}/print`, '_blank');
}

function applyFilters() {
    currentFilters = {
        date_from: document.getElementById('date-from').value,
        date_to: document.getElementById('date-to').value,
        modality: document.getElementById('modality-filter').value,
        status: document.getElementById('status-filter').value,
        urgency: document.getElementById('urgency-filter').value
    };
    
    // Remove empty filters
    Object.keys(currentFilters).forEach(key => {
        if (!currentFilters[key]) {
            delete currentFilters[key];
        }
    });
    
    loadStudies(1);
}

function changePage(direction) {
    const newPage = currentPage + direction;
    if (newPage >= 1 && newPage <= totalPages) {
        loadStudies(newPage);
    }
}

function updatePagination() {
    document.getElementById('current-page').textContent = currentPage;
    document.getElementById('total-pages').textContent = totalPages;
    
    const prevBtn = document.querySelector('.btn-page:first-child');
    const nextBtn = document.querySelector('.btn-page:last-child');
    
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
}

// Notifications
let notificationCount = 0;

async function checkNotifications() {
    try {
        const response = await fetch('/api/worklist/notifications/unread');
        const data = await response.json();
        
        notificationCount = data.count;
        updateNotificationBadge();
        
        if (data.notifications && data.notifications.length > 0) {
            renderNotifications(data.notifications);
        }
    } catch (error) {
        console.error('Error checking notifications:', error);
    }
}

function updateNotificationBadge() {
    const badge = document.querySelector('.badge-count');
    if (notificationCount > 0) {
        badge.textContent = notificationCount;
        badge.style.display = 'block';
    } else {
        badge.style.display = 'none';
    }
}

function toggleNotifications() {
    const panel = document.getElementById('notification-panel');
    const isVisible = panel.classList.contains('show');
    
    if (isVisible) {
        panel.classList.remove('show');
    } else {
        panel.classList.add('show');
        loadNotifications();
    }
}

async function loadNotifications() {
    try {
        const response = await fetch('/api/worklist/notifications');
        const notifications = await response.json();
        renderNotifications(notifications);
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

function renderNotifications(notifications) {
    const container = document.getElementById('notification-list');
    container.innerHTML = '';
    
    if (notifications.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);">No notifications</div>';
        return;
    }
    
    notifications.forEach(notification => {
        const item = document.createElement('div');
        item.className = `notification-item ${notification.is_read ? '' : 'unread'}`;
        item.innerHTML = `
            <div class="notification-type">${formatNotificationType(notification.notification_type)}</div>
            <div class="notification-title">${notification.title}</div>
            <div class="notification-message">${notification.message}</div>
            <div class="notification-time">${formatTime(notification.created_at)}</div>
        `;
        
        item.addEventListener('click', () => markNotificationRead(notification.id));
        container.appendChild(item);
    });
}

function formatNotificationType(type) {
    const types = {
        'new_study': 'New Study',
        'report_completed': 'Report Completed',
        'urgent_study': 'Urgent Study',
        'report_verified': 'Report Verified'
    };
    return types[type] || type;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    return date.toLocaleDateString();
}

async function markNotificationRead(notificationId) {
    try {
        await fetch(`/api/worklist/notifications/${notificationId}/read`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        checkNotifications();
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

function closeNotifications() {
    document.getElementById('notification-panel').classList.remove('show');
}

function startNotificationPolling() {
    // Check notifications immediately
    checkNotifications();
    
    // Then check every 30 seconds
    setInterval(checkNotifications, 30000);
}

// Utility functions
function showNotification(message, type = 'info') {
    // Create a temporary notification
    const notification = document.createElement('div');
    notification.className = `temp-notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 2rem;
        background-color: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
        color: white;
        border-radius: 4px;
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
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

// Add animation styles
const style = document.createElement('style');
style.textContent = `
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
`;
document.head.appendChild(style);