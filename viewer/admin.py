# dicom_viewer/admin.py
from django.contrib import admin
from .models import (DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
                     Facility, UserProfile, ClinicalInformation, RadiologyReport, Notification)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'email', 'ae_title', 'created_at')
    search_fields = ('name', 'address', 'ae_title')
    list_filter = ('created_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'facility', 'license_number', 'created_at')
    list_filter = ('role', 'facility', 'created_at')
    search_fields = ('user__username', 'user__email', 'license_number')


@admin.register(DicomStudy)
class DicomStudyAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'patient_id', 'study_date', 'modality', 'facility', 'is_processed', 'created_at')
    list_filter = ('modality', 'facility', 'is_processed', 'study_date', 'created_at')
    search_fields = ('patient_name', 'patient_id', 'study_instance_uid')
    readonly_fields = ('study_instance_uid', 'created_at')


@admin.register(DicomSeries)
class DicomSeriesAdmin(admin.ModelAdmin):
    list_display = ('study', 'series_number', 'series_description', 'modality', 'image_count', 'created_at')
    list_filter = ('modality', 'created_at')
    search_fields = ('series_description', 'series_instance_uid')
    readonly_fields = ('series_instance_uid', 'created_at')


@admin.register(DicomImage)
class DicomImageAdmin(admin.ModelAdmin):
    list_display = ('series', 'instance_number', 'rows', 'columns', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('sop_instance_uid',)
    readonly_fields = ('sop_instance_uid', 'created_at')


@admin.register(ClinicalInformation)
class ClinicalInformationAdmin(admin.ModelAdmin):
    list_display = ('study', 'patient_age', 'patient_sex', 'referring_physician', 'created_at')
    list_filter = ('patient_sex', 'created_at')
    search_fields = ('study__patient_name', 'referring_physician', 'clinical_history')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RadiologyReport)
class RadiologyReportAdmin(admin.ModelAdmin):
    list_display = ('study', 'status', 'radiologist', 'created_at', 'finalized_at')
    list_filter = ('status', 'created_at', 'finalized_at')
    search_fields = ('study__patient_name', 'radiologist__username', 'findings', 'impression')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ('image', 'measurement_type', 'value', 'unit', 'created_at', 'created_by')
    list_filter = ('measurement_type', 'unit', 'created_at')
    search_fields = ('notes',)
    readonly_fields = ('created_at',)


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ('image', 'text', 'x_coordinate', 'y_coordinate', 'created_at', 'created_by')
    list_filter = ('created_at',)
    search_fields = ('text',)
    readonly_fields = ('created_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at',)