# dicom_viewer/serializers.py
from rest_framework import serializers
from .models import (
    DicomStudy, DicomSeries, DicomImage, Measurement, Annotation,
    Facility, UserProfile, Report, Notification, AIAnalysis, ReconstructionSettings
)
from django.contrib.auth.models import User


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'username', 'role', 'facility', 'facility_name', 'created_at']


class DicomStudySerializer(serializers.ModelSerializer):
    series_count = serializers.ReadOnlyField()
    total_images = serializers.ReadOnlyField()
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    
    class Meta:
        model = DicomStudy
        fields = [
            'id', 'study_instance_uid', 'patient_name', 'patient_id',
            'study_date', 'study_time', 'study_description', 'modality',
            'institution_name', 'facility', 'facility_name', 'clinical_history',
            'indication', 'series_count', 'total_images', 'created_at'
        ]


class DicomSeriesSerializer(serializers.ModelSerializer):
    image_count = serializers.ReadOnlyField()
    
    class Meta:
        model = DicomSeries
        fields = [
            'id', 'series_instance_uid', 'series_number', 'series_description',
            'modality', 'body_part_examined', 'image_count', 'created_at'
        ]


class DicomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DicomImage
        fields = [
            'id', 'sop_instance_uid', 'instance_number', 'rows', 'columns',
            'pixel_spacing_x', 'pixel_spacing_y', 'slice_thickness',
            'window_width', 'window_center', 'created_at'
        ]


class MeasurementSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Measurement
        fields = [
            'id', 'measurement_type', 'coordinates', 'value', 'unit',
            'notes', 'created_at', 'created_by', 'created_by_username'
        ]


class AnnotationSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Annotation
        fields = [
            'id', 'x_coordinate', 'y_coordinate', 'text', 'font_size',
            'is_draggable', 'created_at', 'created_by', 'created_by_username'
        ]


class ReportSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    finalized_by_username = serializers.CharField(source='finalized_by.username', read_only=True)
    patient_name = serializers.CharField(source='study.patient_name', read_only=True)
    study_date = serializers.DateField(source='study.study_date', read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'study', 'patient_name', 'study_date', 'report_text',
            'impression', 'status', 'created_by', 'created_by_username',
            'finalized_by', 'finalized_by_username', 'created_at',
            'modified_at', 'finalized_at'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    study_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'study',
            'study_info', 'is_read', 'created_at'
        ]
    
    def get_study_info(self, obj):
        if obj.study:
            return {
                'id': obj.study.id,
                'patient_name': obj.study.patient_name,
                'study_date': obj.study.study_date,
                'modality': obj.study.modality
            }
        return None


class AIAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysis
        fields = [
            'id', 'analysis_type', 'results', 'confidence_score',
            'highlighted_regions', 'status', 'created_at', 'completed_at'
        ]


class ReconstructionSettingsSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = ReconstructionSettings
        fields = [
            'id', 'reconstruction_type', 'settings', 'thumbnail',
            'created_by', 'created_by_username', 'created_at'
        ]