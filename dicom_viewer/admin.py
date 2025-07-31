from django.contrib import admin
from .models import DicomStudy, DicomSeries, DicomImage, Measurement, Annotation


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