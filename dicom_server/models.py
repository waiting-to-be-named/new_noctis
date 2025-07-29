from django.db import models
from django.utils import timezone
from viewer.models import Facility


class DicomServerConfig(models.Model):
    """Configuration for DICOM SCP/SCU server"""
    name = models.CharField(max_length=100, default='Noctis DICOM Server')
    ae_title = models.CharField(max_length=16, default='NOCTIS')
    port = models.IntegerField(default=11112)
    max_pdu_length = models.IntegerField(default=65536)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'DICOM Server Configuration'
        verbose_name_plural = 'DICOM Server Configurations'
    
    def __str__(self):
        return f"{self.name} ({self.ae_title}:{self.port})"


class FacilityAETitle(models.Model):
    """Auto-generated AE titles for different facilities"""
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='ae_titles')
    ae_title = models.CharField(max_length=16)
    port = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Facility AE Title'
        verbose_name_plural = 'Facility AE Titles'
        unique_together = ['facility', 'ae_title', 'port']
    
    def __str__(self):
        return f"{self.facility.name} ({self.ae_title}:{self.port})"
    
    @classmethod
    def generate_ae_title(cls, facility):
        """Generate a unique AE title for a facility"""
        base_ae = facility.name[:8].upper().replace(' ', '')
        if not base_ae:
            base_ae = 'FACILITY'
        
        # Find available port starting from 11113
        used_ports = cls.objects.filter(is_active=True).values_list('port', flat=True)
        port = 11113
        while port in used_ports:
            port += 1
        
        # Generate unique AE title
        counter = 1
        ae_title = base_ae
        while cls.objects.filter(ae_title=ae_title, is_active=True).exists():
            ae_title = f"{base_ae}{counter:02d}"
            counter += 1
        
        return cls.objects.create(
            facility=facility,
            ae_title=ae_title,
            port=port
        )


class DicomTransferLog(models.Model):
    """Log of DICOM transfers"""
    TRANSFER_TYPES = [
        ('C_STORE', 'C-STORE'),
        ('C_FIND', 'C-FIND'),
        ('C_MOVE', 'C-MOVE'),
        ('C_ECHO', 'C-ECHO'),
    ]
    
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('IN_PROGRESS', 'In Progress'),
    ]
    
    transfer_type = models.CharField(max_length=10, choices=TRANSFER_TYPES)
    calling_ae_title = models.CharField(max_length=16)
    called_ae_title = models.CharField(max_length=16)
    study_instance_uid = models.CharField(max_length=255, blank=True, null=True)
    patient_name = models.CharField(max_length=255, blank=True, null=True)
    patient_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True, null=True)
    bytes_transferred = models.BigIntegerField(default=0)
    transfer_time = models.FloatField(default=0.0)  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'DICOM Transfer Log'
        verbose_name_plural = 'DICOM Transfer Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transfer_type} from {self.calling_ae_title} to {self.called_ae_title} - {self.status}"