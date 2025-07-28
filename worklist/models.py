from django.db import models
from django.contrib.auth.models import User
from viewer.models import DicomStudy, Facility


class WorklistEntry(models.Model):
    """Model to represent entries in the DICOM worklist"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    patient_id = models.CharField(max_length=100)
    patient_name = models.CharField(max_length=200)
    patient_dob = models.DateField(null=True, blank=True)
    patient_sex = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True)
    
    study_instance_uid = models.CharField(max_length=100, unique=True)
    accession_number = models.CharField(max_length=100, blank=True)
    study_date = models.DateField()
    study_time = models.TimeField(null=True, blank=True)
    
    modality = models.CharField(max_length=10)
    study_description = models.TextField(blank=True)
    body_part = models.CharField(max_length=100, blank=True)
    
    referring_physician = models.CharField(max_length=200, blank=True)
    institution_name = models.CharField(max_length=200, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True)
    
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Link to actual DICOM study if uploaded
    dicom_study = models.OneToOneField(DicomStudy, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-study_date', '-study_time']
        verbose_name_plural = "Worklist Entries"
    
    def __str__(self):
        return f"{self.patient_name} - {self.study_description} ({self.study_date})"
    
    @property
    def has_images(self):
        return self.dicom_study is not None


class DicomSCPServer(models.Model):
    """Model to configure DICOM SCP server settings"""
    name = models.CharField(max_length=100)
    ae_title = models.CharField(max_length=16, default='NOCTISVIEW')
    port = models.IntegerField(default=11112)
    host = models.CharField(max_length=100, default='0.0.0.0')
    is_active = models.BooleanField(default=True)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True)
    
    # Storage settings
    auto_route_to_worklist = models.BooleanField(default=True)
    storage_path = models.CharField(max_length=500, default='dicom_storage/')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "DICOM SCP Server"
        verbose_name_plural = "DICOM SCP Servers"
    
    def __str__(self):
        return f"{self.name} ({self.ae_title}:{self.port})"


class StudyAssignment(models.Model):
    """Model to track study assignments to radiologists"""
    worklist_entry = models.ForeignKey(WorklistEntry, on_delete=models.CASCADE, related_name='assignments')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_studies')
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments_made')
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    # Status tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['worklist_entry', 'assigned_to']
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.worklist_entry.patient_name} assigned to {self.assigned_to.username}"