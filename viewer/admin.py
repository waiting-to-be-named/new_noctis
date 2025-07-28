# viewer/admin.py
from django.contrib import admin
from .models import (
    Facility, UserProfile, DicomStudy, DicomSeries, DicomImage, 
    Measurement, Annotation, ClinicalInfo, Report, 
    UploadNotification, AIAnalysis, Notification
)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_phone', 'contact_email', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'address', 'contact_email']
    readonly_fields = ['created_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'facility', 'license_number', 'created_at']
    list_filter = ['role', 'facility', 'created_at']
    search_fields = ['user__username', 'user__email', 'license_number']
    readonly_fields = ['created_at']


@admin.register(DicomStudy)
class DicomStudyAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'patient_id', 'study_date', 'modality', 'facility', 'status', 'created_at']
    list_filter = ['modality', 'status', 'facility', 'study_date', 'created_at']
    search_fields = ['patient_name', 'patient_id', 'accession_number', 'study_description']
    readonly_fields = ['study_instance_uid', 'created_at']
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_name', 'patient_id', 'patient_birth_date', 'patient_sex')
        }),
        ('Study Information', {
            'fields': ('study_instance_uid', 'accession_number', 'study_date', 'study_time', 'study_description', 'modality')
        }),
        ('Facility Information', {
            'fields': ('facility', 'institution_name')
        }),
        ('Status Information', {
            'fields': ('status', 'last_viewed', 'last_viewed_by')
        }),
        ('System Information', {
            'fields': ('uploaded_by', 'created_at')
        }),
    )


@admin.register(DicomSeries)
class DicomSeriesAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'study', 'modality', 'image_count', 'created_at']
    list_filter = ['modality', 'created_at']
    search_fields = ['series_description', 'study__patient_name']
    readonly_fields = ['series_instance_uid', 'created_at', 'image_count']
    
    fieldsets = (
        ('Series Information', {
            'fields': ('study', 'series_instance_uid', 'series_number', 'series_description', 'modality', 'body_part_examined')
        }),
        ('System Information', {
            'fields': ('created_at', 'image_count')
        }),
    )


@admin.register(DicomImage)
class DicomImageAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'series', 'rows', 'columns', 'window_width', 'window_center', 'created_at']
    list_filter = ['created_at', 'series__modality']
    search_fields = ['sop_instance_uid', 'series__series_description', 'series__study__patient_name']
    readonly_fields = ['sop_instance_uid', 'created_at']
    
    fieldsets = (
        ('Image Information', {
            'fields': ('series', 'sop_instance_uid', 'instance_number', 'file_path')
        }),
        ('Image Properties', {
            'fields': ('rows', 'columns', 'image_position', 'image_orientation', 'pixel_spacing', 'slice_thickness')
        }),
        ('Display Properties', {
            'fields': ('window_width', 'window_center')
        }),
        ('System Information', {
            'fields': ('created_at',)
        }),
    )


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'image', 'measurement_type', 'user', 'created_at']
    list_filter = ['measurement_type', 'unit', 'created_at']
    search_fields = ['image__series__study__patient_name', 'user__username']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Measurement Information', {
            'fields': ('image', 'measurement_type', 'coordinates', 'value', 'unit', 'metadata')
        }),
        ('System Information', {
            'fields': ('user', 'created_at')
        }),
    )


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'image', 'x_position', 'y_position', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['text', 'image__series__study__patient_name', 'user__username']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Annotation Information', {
            'fields': ('image', 'x_position', 'y_position', 'text', 'font_size', 'color')
        }),
        ('System Information', {
            'fields': ('user', 'created_at')
        }),
    )


@admin.register(ClinicalInfo)
class ClinicalInfoAdmin(admin.ModelAdmin):
    list_display = ['study', 'user', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['study__patient_name', 'content', 'user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['study', 'user', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['study__patient_name', 'content', 'user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UploadNotification)
class UploadNotificationAdmin(admin.ModelAdmin):
    list_display = ['study', 'uploaded_by', 'is_seen', 'created_at']
    list_filter = ['is_seen', 'created_at']
    search_fields = ['study__patient_name', 'message', 'uploaded_by__username']
    readonly_fields = ['created_at']


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ['image', 'analysis_type', 'user', 'confidence', 'created_at']
    list_filter = ['analysis_type', 'created_at']
    search_fields = ['image__series__study__patient_name', 'analysis_type', 'user__username']
    readonly_fields = ['created_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__username']
    readonly_fields = ['created_at']