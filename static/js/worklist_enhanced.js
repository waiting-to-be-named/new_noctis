
// Enhanced Worklist JavaScript for Professional Medical Environment

class EnhancedWorklist {
    constructor() {
        this.currentData = [];
        this.filteredData = [];
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadWorklistData();
        this.setupUploadHandlers();
        this.setupNotifications();
        this.setupSearch();
        this.setupFilters();
        
        console.log('Enhanced Worklist initialized');
    }
    
    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
        }
        
        // Filter functionality
        const filters = ['status-filter', 'modality-filter', 'facility-filter'];
        filters.forEach(filterId => {
            const filter = document.getElementById(filterId);
            if (filter) {
                filter.addEventListener('change', () => this.applyFilters());
            }
        });
        
        // Table sorting
        document.querySelectorAll('.worklist-table th').forEach(th => {
            th.style.cursor = 'pointer';
            th.addEventListener('click', () => this.handleSort(th));
        });
        
        // Auto-refresh
        setInterval(() => this.loadWorklistData(), 30000); // Refresh every 30 seconds
    }
    
    async loadWorklistData() {
        try {
            const response = await fetch('/worklist/api/studies/', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.currentData = data.studies || [];
                this.applyFilters();
                this.updateWorklistDisplay();
            } else {
                console.error('Failed to load worklist data:', response.status);
                this.showMessage('Failed to load worklist data', 'error');
            }
        } catch (error) {
            console.error('Error loading worklist:', error);
            this.showMessage('Error loading worklist data', 'error');
        }
    }
    
    handleSearch(searchTerm) {
        const term = searchTerm.toLowerCase().trim();
        
        if (term === '') {
            this.filteredData = [...this.currentData];
        } else {
            this.filteredData = this.currentData.filter(study => 
                study.patient_name.toLowerCase().includes(term) ||
                study.patient_id.toLowerCase().includes(term) ||
                (study.accession_number && study.accession_number.toLowerCase().includes(term)) ||
                (study.study_description && study.study_description.toLowerCase().includes(term))
            );
        }
        
        this.updateWorklistDisplay();
    }
    
    applyFilters() {
        let filtered = [...this.currentData];
        
        // Status filter
        const statusFilter = document.getElementById('status-filter');
        if (statusFilter && statusFilter.value) {
            filtered = filtered.filter(study => study.status === statusFilter.value);
        }
        
        // Modality filter
        const modalityFilter = document.getElementById('modality-filter');
        if (modalityFilter && modalityFilter.value) {
            filtered = filtered.filter(study => study.modality === modalityFilter.value);
        }
        
        // Facility filter
        const facilityFilter = document.getElementById('facility-filter');
        if (facilityFilter && facilityFilter.value) {
            filtered = filtered.filter(study => study.facility_id == facilityFilter.value);
        }
        
        this.filteredData = filtered;
        this.updateWorklistDisplay();
    }
    
    handleSort(th) {
        const column = th.textContent.toLowerCase().replace(/[^a-z]/g, '');
        
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }
        
        // Update sort indicators
        document.querySelectorAll('.worklist-table th').forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
        });
        
        th.classList.add(`sort-${this.sortDirection}`);
        
        // Sort data
        this.filteredData.sort((a, b) => {
            let aVal = this.getSortValue(a, column);
            let bVal = this.getSortValue(b, column);
            
            if (this.sortDirection === 'desc') {
                [aVal, bVal] = [bVal, aVal];
            }
            
            return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
        });
        
        this.updateWorklistDisplay();
    }
    
    getSortValue(study, column) {
        const columnMap = {
            'patientname': study.patient_name,
            'patientid': study.patient_id,
            'accession': study.accession_number || '',
            'modality': study.modality,
            'studydate': study.study_date,
            'status': study.status,
            'facility': study.facility_name || ''
        };
        
        return (columnMap[column] || '').toString().toLowerCase();
    }
    
    updateWorklistDisplay() {
        const tbody = document.querySelector('.worklist-table tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (this.filteredData.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="100%" style="text-align: center; padding: 40px; color: #94a3b8;">
                        <i class="fas fa-search" style="font-size: 48px; margin-bottom: 15px; opacity: 0.5;"></i>
                        <br>No studies found matching your criteria
                    </td>
                </tr>
            `;
            return;
        }
        
        this.filteredData.forEach(study => {
            const row = this.createStudyRow(study);
            tbody.appendChild(row);
        });
        
        // Update count display
        this.updateResultsCount();
    }
    
    createStudyRow(study) {
        const row = document.createElement('tr');
        row.className = 'study-row';
        row.dataset.studyId = study.id;
        
        // Determine priority class
        const priorityClass = this.getPriorityClass(study);
        
        row.innerHTML = `
            <td class="${priorityClass}">
                <strong>${study.patient_name}</strong>
                <br><small style="color: #94a3b8;">DOB: ${study.patient_birth_date || 'Unknown'}</small>
            </td>
            <td>${study.patient_id}</td>
            <td>${study.accession_number || '-'}</td>
            <td>
                <span class="modality-badge modality-${study.modality.toLowerCase()}">
                    ${study.modality}
                </span>
            </td>
            <td>${this.formatDate(study.study_date)}</td>
            <td>
                <span class="status-badge status-${study.status}">
                    ${this.formatStatus(study.status)}
                </span>
            </td>
            <td>${study.facility_name || 'Unknown'}</td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn btn-view-study" onclick="viewStudy(${study.id})" title="View Study">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="action-btn btn-edit" onclick="editStudy(${study.id})" title="Edit Study">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="action-btn btn-report" onclick="generateReport(${study.id})" title="Generate Report">
                        <i class="fas fa-file-alt"></i> Report
                    </button>
                </div>
            </td>
        `;
        
        // Add click handler for row selection
        row.addEventListener('click', (e) => {
            if (!e.target.closest('button')) {
                this.selectStudy(study.id);
            }
        });
        
        return row;
    }
    
    getPriorityClass(study) {
        // Determine priority based on study age and status
        const studyDate = new Date(study.study_date);
        const now = new Date();
        const daysDiff = (now - studyDate) / (1000 * 60 * 60 * 24);
        
        if (study.status === 'scheduled' && daysDiff > 7) {
            return 'priority-urgent';
        } else if (study.status === 'in_progress' && daysDiff > 3) {
            return 'priority-high';
        }
        
        return 'priority-normal';
    }
    
    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }
    
    formatStatus(status) {
        const statusMap = {
            'scheduled': 'Scheduled',
            'in_progress': 'In Progress',
            'completed': 'Completed',
            'reported': 'Reported'
        };
        return statusMap[status] || status;
    }
    
    selectStudy(studyId) {
        // Remove previous selections
        document.querySelectorAll('.study-row').forEach(row => {
            row.classList.remove('selected');
        });
        
        // Add selection to current row
        const row = document.querySelector(`[data-study-id="${studyId}"]`);
        if (row) {
            row.classList.add('selected');
        }
    }
    
    updateResultsCount() {
        const total = this.currentData.length;
        const filtered = this.filteredData.length;
        
        let countDisplay = document.getElementById('results-count');
        if (!countDisplay) {
            countDisplay = document.createElement('div');
            countDisplay.id = 'results-count';
            countDisplay.style.cssText = 'margin: 15px 30px; color: #94a3b8; font-size: 14px;';
            
            const container = document.querySelector('.worklist-table-container');
            if (container) {
                container.parentNode.insertBefore(countDisplay, container);
            }
        }
        
        countDisplay.innerHTML = `
            <i class="fas fa-list"></i> 
            Showing ${filtered} of ${total} studies
            ${filtered !== total ? '(filtered)' : ''}
        `;
    }
    
    setupUploadHandlers() {
        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');
        const fileInputFiles = document.getElementById('file-input-files');
        
        if (uploadZone) {
            // Drag and drop handlers
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.classList.add('dragover');
            });
            
            uploadZone.addEventListener('dragleave', () => {
                uploadZone.classList.remove('dragover');
            });
            
            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                this.handleFileUpload(e.dataTransfer.files);
            });
            
            uploadZone.addEventListener('click', () => {
                fileInput.click();
            });
        }
        
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileUpload(e.target.files);
            });
        }
        
        if (fileInputFiles) {
            fileInputFiles.addEventListener('change', (e) => {
                this.handleFileUpload(e.target.files);
            });
        }
    }
    
    async handleFileUpload(files) {
        if (!files || files.length === 0) return;
        
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });
        
        this.showUploadProgress(true);
        
        try {
            const response = await fetch('/viewer/api/upload-dicom-files/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showMessage(`Successfully uploaded ${files.length} files`, 'success');
                this.loadWorklistData(); // Refresh the worklist
            } else {
                throw new Error(`Upload failed: ${response.status}`);
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showMessage('Upload failed', 'error');
        } finally {
            this.showUploadProgress(false);
        }
    }
    
    showUploadProgress(show) {
        const progressDiv = document.getElementById('upload-progress');
        if (progressDiv) {
            progressDiv.style.display = show ? 'block' : 'none';
        }
    }
    
    setupNotifications() {
        // Setup notification polling
        setInterval(() => this.checkNotifications(), 60000); // Check every minute
    }
    
    async checkNotifications() {
        try {
            const response = await fetch('/worklist/api/notifications/', {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateNotificationCount(data.count || 0);
            }
        } catch (error) {
            console.log('Notification check failed:', error);
        }
    }
    
    updateNotificationCount(count) {
        const notificationCount = document.getElementById('notification-count');
        if (notificationCount) {
            notificationCount.textContent = count;
            notificationCount.style.display = count > 0 ? 'flex' : 'none';
        }
    }
    
    setupSearch() {
        // Enhanced search with debouncing
        let searchTimeout;
        const searchInput = document.getElementById('search');
        
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.handleSearch(e.target.value);
                }, 300);
            });
        }
    }
    
    setupFilters() {
        // Add filter reset button
        const filtersContainer = document.querySelector('.filters');
        if (filtersContainer) {
            const resetBtn = document.createElement('button');
            resetBtn.className = 'btn btn-view';
            resetBtn.innerHTML = '<i class="fas fa-refresh"></i> Reset Filters';
            resetBtn.addEventListener('click', () => this.resetFilters());
            filtersContainer.appendChild(resetBtn);
        }
    }
    
    resetFilters() {
        document.getElementById('search').value = '';
        document.getElementById('status-filter').value = '';
        document.getElementById('modality-filter').value = '';
        const facilityFilter = document.getElementById('facility-filter');
        if (facilityFilter) facilityFilter.value = '';
        
        this.filteredData = [...this.currentData];
        this.updateWorklistDisplay();
    }
    
    showMessage(message, type = 'info') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `${type}-message`;
        messageDiv.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'times' : 'info'}-circle"></i>
            ${message}
        `;
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            messageDiv.remove();
        }, 5000);
    }
    
    getCSRFToken() {
        const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
        return tokenElement ? tokenElement.value : '';
    }
}

// Global functions for button actions
function viewStudy(studyId) {
    window.location.href = `/viewer/study/${studyId}/`;
}

function editStudy(studyId) {
    // Implementation for editing study details
    console.log('Edit study:', studyId);
}

function generateReport(studyId) {
    // Implementation for generating reports
    console.log('Generate report for study:', studyId);
}

function selectUploadType() {
    document.getElementById('file-input').click();
}

function toggleNotifications() {
    console.log('Toggle notifications');
}

function toggleChat() {
    console.log('Toggle chat');
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.enhancedWorklist = new EnhancedWorklist();
});
