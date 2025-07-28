from django.contrib import admin
from .models import WorklistEntry, DicomSCPServer, StudyAssignment


@admin.register(WorklistEntry)
class WorklistEntryAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'patient_id', 'study_date', 'modality', 'priority', 'status', 'facility', 'has_images']
    list_filter = ['modality', 'priority', 'status', 'facility', 'study_date', 'created_at']
    search_fields = ['patient_name', 'patient_id', 'accession_number', 'study_description']
    readonly_fields = ['study_instance_uid', 'created_at', 'updated_at', 'has_images']
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_id', 'patient_name', 'patient_dob', 'patient_sex')
        }),
        ('Study Information', {
            'fields': ('study_instance_uid', 'accession_number', 'study_date', 'study_time', 
                      'modality', 'study_description', 'body_part', 'referring_physician')
        }),
        ('Facility & Status', {
            'fields': ('institution_name', 'facility', 'priority', 'status')
        }),
        ('System Information', {
            'fields': ('dicom_study', 'created_by', 'created_at', 'updated_at', 'has_images')
        }),
    )


@admin.register(DicomSCPServer)
class DicomSCPServerAdmin(admin.ModelAdmin):
    list_display = ['name', 'ae_title', 'host', 'port', 'is_active', 'facility', 'auto_route_to_worklist']
    list_filter = ['is_active', 'facility', 'auto_route_to_worklist', 'created_at']
    search_fields = ['name', 'ae_title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(StudyAssignment)
class StudyAssignmentAdmin(admin.ModelAdmin):
    list_display = ['worklist_entry', 'assigned_to', 'assigned_by', 'assigned_at', 'started_at', 'completed_at']
    list_filter = ['assigned_at', 'started_at', 'completed_at']
    search_fields = ['worklist_entry__patient_name', 'assigned_to__username', 'notes']
    readonly_fields = ['assigned_at']