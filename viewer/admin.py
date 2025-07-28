# dicom_viewer/admin.py
from django.contrib import admin
from .models import (
    Facility, UserProfile, DicomStudy, DicomSeries, DicomImage,
    Measurement, Annotation, Report, Notification, AIAnalysis, ReconstructionSettings
)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'created_at']
    search_fields = ['name', 'email']
    list_filter = ['created_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'facility', 'created_at']
    list_filter = ['role', 'facility', 'created_at']
    search_fields = ['user__username', 'user__email']


@admin.register(DicomStudy)
class DicomStudyAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'patient_id', 'study_date', 'modality', 'facility', 'uploaded_by']
    list_filter = ['modality', 'facility', 'study_date', 'created_at']
    search_fields = ['patient_name', 'patient_id', 'study_instance_uid']
    readonly_fields = ['study_instance_uid', 'created_at']


@admin.register(DicomSeries)
class DicomSeriesAdmin(admin.ModelAdmin):
    list_display = ['study', 'series_number', 'series_description', 'modality', 'image_count']
    list_filter = ['modality', 'created_at']
    search_fields = ['series_description', 'series_instance_uid']


@admin.register(DicomImage)
class DicomImageAdmin(admin.ModelAdmin):
    list_display = ['series', 'instance_number', 'rows', 'columns', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['sop_instance_uid', 'created_at']


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ['image', 'measurement_type', 'value', 'unit', 'created_by', 'created_at']
    list_filter = ['measurement_type', 'unit', 'created_at']
    search_fields = ['notes']


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ['image', 'text', 'font_size', 'is_draggable', 'created_by', 'created_at']
    list_filter = ['is_draggable', 'created_at']
    search_fields = ['text']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['study', 'status', 'created_by', 'created_at', 'finalized_by', 'finalized_at']
    list_filter = ['status', 'created_at', 'finalized_at']
    search_fields = ['study__patient_name', 'report_text', 'impression']
    readonly_fields = ['created_at', 'modified_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message']


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ['image', 'analysis_type', 'status', 'confidence_score', 'created_at', 'completed_at']
    list_filter = ['analysis_type', 'status', 'created_at']
    readonly_fields = ['created_at', 'completed_at']


@admin.register(ReconstructionSettings)
class ReconstructionSettingsAdmin(admin.ModelAdmin):
    list_display = ['study', 'reconstruction_type', 'created_by', 'created_at']
    list_filter = ['reconstruction_type', 'created_at']
    readonly_fields = ['created_at']