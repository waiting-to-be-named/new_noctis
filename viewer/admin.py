# dicom_viewer/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from .models import (
    Facility, FacilityUser, DicomStudy, DicomSeries, DicomImage, Measurement, 
    Annotation, Report, WorklistEntry, AIAnalysis, Notification
)
import os

# Register your models here.
admin.site.site_header = "Noctis Administration"
admin.site.site_title = "Noctis Admin"
admin.site.index_title = "Noctis Medical Imaging Platform"


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'email', 'address']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Facility Information', {
            'fields': ('name', 'address', 'phone', 'email')
        }),
        ('Branding', {
            'fields': ('letterhead_logo',)
        }),
        ('System Information', {
            'fields': ('created_at',)
        }),
    )


@admin.register(FacilityUser)
class FacilityUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'facility', 'email', 'is_active', 'last_login']
    list_filter = ['is_active', 'created_at', 'facility']
    search_fields = ['username', 'email', 'facility__name']
    readonly_fields = ['created_at', 'last_login']
    
    fieldsets = (
        ('User Information', {
            'fields': ('facility', 'username', 'email', 'password')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('System Information', {
            'fields': ('created_at', 'last_login')
        }),
    )


@admin.register(DicomStudy)
class DicomStudyAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'study_date', 'modality', 'series_count', 'total_images', 'facility', 'created_at']
    list_filter = ['modality', 'study_date', 'created_at', 'facility']
    search_fields = ['patient_name', 'patient_id', 'study_description']
    readonly_fields = ['study_instance_uid', 'created_at', 'series_count', 'total_images']
    actions = ['delete_selected_studies']
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_name', 'patient_id')
        }),
        ('Study Information', {
            'fields': ('study_instance_uid', 'study_date', 'study_time', 'study_description', 'modality', 'institution_name')
        }),
        ('Upload Information', {
            'fields': ('uploaded_by', 'facility', 'facility_user')
        }),
        ('System Information', {
            'fields': ('created_at', 'series_count', 'total_images')
        }),
    )
    
    def delete_selected_studies(self, request, queryset):
        """Custom delete action for studies"""
        count = queryset.count()
        for study in queryset:
            # Delete all related images and files
            for series in study.series.all():
                for image in series.images.all():
                    if image.file_path:
                        try:
                            if os.path.exists(image.file_path.path):
                                os.remove(image.file_path.path)
                        except:
                            pass
                    image.delete()
                series.delete()
            study.delete()
        
        messages.success(request, f'Successfully deleted {count} studies and all associated data.')
        return HttpResponseRedirect(request.get_full_path())
    
    delete_selected_studies.short_description = "Delete selected studies and all associated data"


@admin.register(DicomSeries)
class DicomSeriesAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'study', 'modality', 'image_count', 'created_at']
    list_filter = ['modality', 'created_at']
    search_fields = ['series_description', 'study__patient_name']
    readonly_fields = ['series_instance_uid', 'created_at', 'image_count']
    actions = ['delete_selected_series']
    
    fieldsets = (
        ('Series Information', {
            'fields': ('study', 'series_instance_uid', 'series_number', 'series_description', 'modality', 'body_part_examined')
        }),
        ('System Information', {
            'fields': ('created_at', 'image_count')
        }),
    )
    
    def delete_selected_series(self, request, queryset):
        """Custom delete action for series"""
        count = queryset.count()
        for series in queryset:
            # Delete all related images and files
            for image in series.images.all():
                if image.file_path:
                    try:
                        if os.path.exists(image.file_path.path):
                            os.remove(image.file_path.path)
                    except:
                        pass
                image.delete()
            series.delete()
        
        messages.success(request, f'Successfully deleted {count} series and all associated data.')
        return HttpResponseRedirect(request.get_full_path())
    
    delete_selected_series.short_description = "Delete selected series and all associated data"


@admin.register(DicomImage)
class DicomImageAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'series', 'rows', 'columns', 'window_width', 'window_center', 'created_at']
    list_filter = ['created_at', 'series__modality']
    search_fields = ['sop_instance_uid', 'series__series_description', 'series__study__patient_name']
    readonly_fields = ['sop_instance_uid', 'created_at']
    actions = ['delete_selected_images']
    
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
    
    def delete_selected_images(self, request, queryset):
        """Custom delete action for images"""
        count = queryset.count()
        for image in queryset:
            if image.file_path:
                try:
                    if os.path.exists(image.file_path.path):
                        os.remove(image.file_path.path)
                except:
                    pass
            image.delete()
        
        messages.success(request, f'Successfully deleted {count} images and associated files.')
        return HttpResponseRedirect(request.get_full_path())
    
    delete_selected_images.short_description = "Delete selected images and associated files"


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'image', 'measurement_type', 'created_by', 'created_at']
    list_filter = ['measurement_type', 'unit', 'created_at']
    search_fields = ['notes', 'image__series__study__patient_name']
    readonly_fields = ['created_at']
    actions = ['delete_selected_measurements']
    
    fieldsets = (
        ('Measurement Information', {
            'fields': ('image', 'measurement_type', 'coordinates', 'value', 'unit', 'notes')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at')
        }),
    )
    
    def delete_selected_measurements(self, request, queryset):
        """Custom delete action for measurements"""
        count = queryset.count()
        queryset.delete()
        messages.success(request, f'Successfully deleted {count} measurements.')
        return HttpResponseRedirect(request.get_full_path())
    
    delete_selected_measurements.short_description = "Delete selected measurements"


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'image', 'x_coordinate', 'y_coordinate', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['text', 'image__series__study__patient_name']
    readonly_fields = ['created_at']
    actions = ['delete_selected_annotations']
    
    fieldsets = (
        ('Annotation Information', {
            'fields': ('image', 'x_coordinate', 'y_coordinate', 'text')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at')
        }),
    )
    
    def delete_selected_annotations(self, request, queryset):
        """Custom delete action for annotations"""
        count = queryset.count()
        queryset.delete()
        messages.success(request, f'Successfully deleted {count} annotations.')
        return HttpResponseRedirect(request.get_full_path())
    
    delete_selected_annotations.short_description = "Delete selected annotations"


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['study', 'radiologist', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['study__patient_name', 'radiologist__username']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['delete_selected_reports']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('study', 'radiologist', 'findings', 'impression', 'recommendations', 'status')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at', 'finalized_at')
        }),
    )
    
    def delete_selected_reports(self, request, queryset):
        """Custom delete action for reports"""
        count = queryset.count()
        queryset.delete()
        messages.success(request, f'Successfully deleted {count} reports.')
        return HttpResponseRedirect(request.get_full_path())
    
    delete_selected_reports.short_description = "Delete selected reports"


@admin.register(WorklistEntry)
class WorklistEntryAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'accession_number', 'modality', 'facility', 'status', 'scheduled_procedure_step_start_date']
    list_filter = ['status', 'modality', 'scheduled_procedure_step_start_date', 'facility']
    search_fields = ['patient_name', 'accession_number', 'procedure_description']
    readonly_fields = ['created_at']
    actions = ['delete_selected_worklist_entries']
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_name', 'patient_id', 'accession_number')
        }),
        ('Procedure Information', {
            'fields': ('scheduled_station_ae_title', 'scheduled_procedure_step_start_date', 'scheduled_procedure_step_start_time', 'modality', 'scheduled_performing_physician', 'procedure_description')
        }),
        ('System Information', {
            'fields': ('facility', 'status', 'study', 'created_at')
        }),
    )
    
    def delete_selected_worklist_entries(self, request, queryset):
        """Custom delete action for worklist entries"""
        count = queryset.count()
        queryset.delete()
        messages.success(request, f'Successfully deleted {count} worklist entries.')
        return HttpResponseRedirect(request.get_full_path())
    
    delete_selected_worklist_entries.short_description = "Delete selected worklist entries"


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ['image', 'analysis_type', 'confidence_score', 'created_at']
    list_filter = ['analysis_type', 'created_at']
    search_fields = ['image__series__study__patient_name']
    readonly_fields = ['created_at']
    actions = ['delete_selected_ai_analyses']
    
    fieldsets = (
        ('Analysis Information', {
            'fields': ('image', 'analysis_type', 'findings', 'summary', 'confidence_score', 'highlighted_regions')
        }),
        ('System Information', {
            'fields': ('created_at',)
        }),
    )
    
    def delete_selected_ai_analyses(self, request, queryset):
        """Custom delete action for AI analyses"""
        count = queryset.count()
        queryset.delete()
        messages.success(request, f'Successfully deleted {count} AI analyses.')
        return HttpResponseRedirect(request.get_full_path())
    
    delete_selected_ai_analyses.short_description = "Delete selected AI analyses"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__username']
    readonly_fields = ['created_at']
    actions = ['delete_selected_notifications']
    
    fieldsets = (
        ('Notification Information', {
            'fields': ('recipient', 'notification_type', 'title', 'message', 'related_study', 'is_read')
        }),
        ('System Information', {
            'fields': ('created_at',)
        }),
    )
    
    def delete_selected_notifications(self, request, queryset):
        """Custom delete action for notifications"""
        count = queryset.count()
        queryset.delete()
        messages.success(request, f'Successfully deleted {count} notifications.')
        return HttpResponseRedirect(request.get_full_path())
    
    delete_selected_notifications.short_description = "Delete selected notifications"