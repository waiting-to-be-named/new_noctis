# dicom_viewer/admin.py
from django.contrib import admin
from .models import (
    DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
    Facility, WorklistPatient, ClinicalInformation, Report, Notification
)


@admin.register(DicomStudy)
class DicomStudyAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'study_date', 'modality', 'series_count', 'total_images', 'created_at']
    list_filter = ['modality', 'study_date', 'created_at']
    search_fields = ['patient_name', 'patient_id', 'study_description']
    readonly_fields = ['study_instance_uid', 'created_at', 'series_count', 'total_images']
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_name', 'patient_id')
        }),
        ('Study Information', {
            'fields': ('study_instance_uid', 'study_date', 'study_time', 'study_description', 'modality', 'institution_name')
        }),
        ('System Information', {
            'fields': ('uploaded_by', 'created_at', 'series_count', 'total_images')
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
            'fields': ('rows', 'columns', 'pixel_spacing_x', 'pixel_spacing_y', 'slice_thickness')
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
    list_display = ['__str__', 'image', 'measurement_type', 'created_by', 'created_at']
    list_filter = ['measurement_type', 'unit', 'created_at']
    search_fields = ['notes', 'image__series__study__patient_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Measurement Information', {
            'fields': ('image', 'measurement_type', 'coordinates', 'value', 'unit', 'notes')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at')
        }),
    )


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'image', 'x_coordinate', 'y_coordinate', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['text', 'image__series__study__patient_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Annotation Information', {
            'fields': ('image', 'x_coordinate', 'y_coordinate', 'text')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at')
        }),
    )


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'phone', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at']


@admin.register(WorklistPatient)
class WorklistPatientAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'patient_id', 'study_date', 'modality', 'facility', 'is_viewed', 'created_at']
    list_filter = ['modality', 'facility', 'is_viewed', 'study_date', 'created_at']
    search_fields = ['patient_name', 'patient_id']
    readonly_fields = ['created_at']


@admin.register(ClinicalInformation)
class ClinicalInformationAdmin(admin.ModelAdmin):
    list_display = ['study', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['study__patient_name', 'chief_complaint', 'clinical_history']
    readonly_fields = ['created_at']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['study', 'status', 'created_by', 'signed_by', 'created_at', 'signed_at']
    list_filter = ['status', 'created_at', 'signed_at']
    search_fields = ['study__patient_name', 'findings', 'impression']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'facility', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at']