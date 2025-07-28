# dicom_viewer/serializers.py
from rest_framework import serializers
from .models import DicomStudy, DicomSeries, DicomImage, Measurement, Annotation


class DicomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DicomImage
        fields = [
            'id', 'sop_instance_uid', 'instance_number', 'rows', 'columns',
            'pixel_spacing_x', 'pixel_spacing_y', 'slice_thickness',
            'window_width', 'window_center', 'bits_allocated', 'image_number',
            'photometric_interpretation', 'pixel_spacing', 'samples_per_pixel',
            'created_at'
        ]


class DicomSeriesSerializer(serializers.ModelSerializer):
    images = DicomImageSerializer(many=True, read_only=True)
    image_count = serializers.ReadOnlyField()
    
    class Meta:
        model = DicomSeries
        fields = [
            'id', 'series_instance_uid', 'series_number', 'series_description',
            'modality', 'body_part_examined', 'image_count', 'images', 'created_at'
        ]


class DicomStudySerializer(serializers.ModelSerializer):
    series = DicomSeriesSerializer(many=True, read_only=True)
    series_count = serializers.ReadOnlyField()
    total_images = serializers.ReadOnlyField()
    
    class Meta:
        model = DicomStudy
        fields = [
            'id', 'study_instance_uid', 'patient_name', 'patient_id',
            'study_date', 'study_time', 'study_description', 'modality',
            'institution_name', 'series_count', 'total_images', 'series', 'created_at'
        ]


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = [
            'id', 'measurement_type', 'coordinates', 'value', 'unit',
            'notes', 'created_at'
        ]


class AnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = [
            'id', 'x_coordinate', 'y_coordinate', 'text', 'created_at'
        ]