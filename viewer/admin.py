# dicom_viewer/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    Facility, FacilityStaff, DicomStudy, DicomSeries, DicomImage, Measurement, 
    Annotation, Report, WorklistEntry, AIAnalysis, Notification, ChatMessage
)

# Register your models here.
admin.site.site_header = "Noctis Administration"
admin.site.site_title = "Noctis Admin"
admin.site.index_title = "Noctis Medical Imaging Platform"


class FacilityStaffInline(admin.TabularInline):
    """Inline admin for facility staff"""
    model = FacilityStaff
    extra = 1
    fields = ['user', 'role', 'is_primary_contact']


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    """Admin interface for Facility model"""
    list_display = ['name', 'email', 'phone', 'staff_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'email', 'address']
    readonly_fields = ['created_at']
    inlines = [FacilityStaffInline]
    
    def staff_count(self, obj):
        return obj.staff.count()
    staff_count.short_description = 'Staff Count'


@admin.register(FacilityStaff)
class FacilityStaffAdmin(admin.ModelAdmin):
    """Admin interface for FacilityStaff model"""
    list_display = ['user', 'facility', 'role', 'is_primary_contact', 'created_at']
    list_filter = ['role', 'facility', 'is_primary_contact', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'facility__name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('User Assignment', {
            'fields': ('user', 'facility')
        }),
        ('Role Information', {
            'fields': ('role', 'is_primary_contact')
        }),
        ('System Information', {
            'fields': ('created_at',)
        }),
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin interface for ChatMessage model"""
    list_display = ['sender', 'recipient', 'facility', 'message_type', 'message_preview', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read', 'facility', 'created_at']
    search_fields = ['sender__username', 'recipient__username', 'message', 'facility__name']
    readonly_fields = ['created_at']
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'
    
    fieldsets = (
        ('Message Information', {
            'fields': ('sender', 'recipient', 'facility', 'message_type', 'message')
        }),
        ('Related Data', {
            'fields': ('related_study',)
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('System Information', {
            'fields': ('created_at',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notification model"""
    list_display = ['recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'title', 'message']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Notification Information', {
            'fields': ('recipient', 'notification_type', 'title', 'message')
        }),
        ('Related Data', {
            'fields': ('related_study',)
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('System Information', {
            'fields': ('created_at',)
        }),
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
        ('DICOM Properties', {
            'fields': ('bits_allocated', 'image_number', 'photometric_interpretation', 'pixel_spacing', 'samples_per_pixel')
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