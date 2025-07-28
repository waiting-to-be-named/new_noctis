# dicom_viewer/admin.py
from django.contrib import admin
from .models import (
    Facility, UserProfile, DicomStudy, DicomSeries, DicomImage,
    Measurement, Annotation, RadiologyReport, Notification
)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'phone', 'email', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['created_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'facility', 'phone', 'created_at']
    list_filter = ['role', 'facility', 'created_at']
    search_fields = ['user__username', 'user__email']


@admin.register(DicomStudy)
class DicomStudyAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'patient_id', 'study_date', 'modality', 'facility', 'status', 'created_at']
    list_filter = ['modality', 'status', 'facility', 'study_date', 'created_at']
    search_fields = ['patient_name', 'patient_id', 'study_instance_uid']
    readonly_fields = ['study_instance_uid', 'created_at']


@admin.register(DicomSeries)
class DicomSeriesAdmin(admin.ModelAdmin):
    list_display = ['study', 'series_number', 'series_description', 'modality', 'created_at']
    list_filter = ['modality', 'created_at']
    search_fields = ['series_description', 'study__patient_name']


@admin.register(DicomImage)
class DicomImageAdmin(admin.ModelAdmin):
    list_display = ['series', 'instance_number', 'rows', 'columns', 'created_at']
    list_filter = ['created_at']
    search_fields = ['series__study__patient_name', 'sop_instance_uid']


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ['image', 'measurement_type', 'value', 'unit', 'created_by', 'created_at']
    list_filter = ['measurement_type', 'unit', 'created_at']
    search_fields = ['image__series__study__patient_name']


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ['image', 'text', 'x_coordinate', 'y_coordinate', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['text', 'image__series__study__patient_name']


@admin.register(RadiologyReport)
class RadiologyReportAdmin(admin.ModelAdmin):
    list_display = ['study', 'status', 'created_by', 'created_at', 'signed_at']
    list_filter = ['status', 'created_at', 'signed_at']
    search_fields = ['study__patient_name', 'clinical_information', 'findings']
    readonly_fields = ['created_at', 'signed_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['notification_type', 'title', 'recipient', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message']