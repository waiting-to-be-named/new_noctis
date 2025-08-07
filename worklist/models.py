from django.db import models
from django.contrib.auth.models import AbstractUser, User
from django.utils import timezone
import os

class UserRole(models.TextChoices):
    ADMIN = 'admin', 'Administrator'
    RADIOLOGIST = 'radiologist', 'Radiologist'
    FACILITY = 'facility', 'Facility User'
    TECHNICIAN = 'technician', 'Technician'

class Facility(models.Model):
    """Medical facility/institution model"""
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    
    # DICOM networking configuration
    dicom_ae_title = models.CharField(max_length=16, blank=True, help_text="DICOM Application Entity Title")
    dicom_host = models.GenericIPAddressField(blank=True, null=True, help_text="DICOM Host IP")
    dicom_port = models.PositiveIntegerField(default=104, help_text="DICOM Port")
    
    # Access control
    is_active = models.BooleanField(default=True)
    upload_quota_gb = models.PositiveIntegerField(default=100, help_text="Upload quota in GB")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Facilities"
    
    def __str__(self):
        return self.name
    
    def get_upload_usage_gb(self):
        """Calculate current upload usage in GB"""
        total_size = 0
        for study in self.studies.all():
            for series in study.series_set.all():
                for image in series.dicomimage_set.all():
                    if image.file_path and os.path.exists(image.file_path):
                        total_size += os.path.getsize(image.file_path)
        return total_size / (1024 ** 3)  # Convert to GB

class CustomUser(AbstractUser):
    """Extended User model with role-based access"""
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.FACILITY
    )
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users'
    )
    
    # Professional information
    license_number = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    notification_types = models.JSONField(default=list, help_text="List of notification types to receive")
    
    # Activity tracking
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def can_view_study(self, study):
        """Check if user can view a specific study"""
        if self.role == UserRole.ADMIN:
            return True
        elif self.role == UserRole.RADIOLOGIST:
            return True  # Radiologists can see all studies
        elif self.role == UserRole.FACILITY:
            return study.facility == self.facility
        elif self.role == UserRole.TECHNICIAN:
            return study.facility == self.facility
        return False
    
    def can_edit_study(self, study):
        """Check if user can edit a specific study"""
        if self.role == UserRole.ADMIN:
            return True
        elif self.role == UserRole.RADIOLOGIST:
            return True  # Radiologists can edit for reporting
        elif self.role in [UserRole.FACILITY, UserRole.TECHNICIAN]:
            return study.facility == self.facility and study.status in ['pending', 'in_progress']
        return False
    
    def get_accessible_studies(self):
        """Get studies this user can access"""
        if self.role == UserRole.ADMIN:
            return Study.objects.all()
        elif self.role == UserRole.RADIOLOGIST:
            return Study.objects.all()
        elif self.role in [UserRole.FACILITY, UserRole.TECHNICIAN]:
            return Study.objects.filter(facility=self.facility)
        return Study.objects.none()

class Study(models.Model):
    """DICOM Study model with facility association"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('in_progress', 'In Progress'),
        ('reviewed', 'Reviewed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
        ('stat', 'STAT'),
    ]
    
    # DICOM identifiers
    study_instance_uid = models.CharField(max_length=64, unique=True, db_index=True)
    accession_number = models.CharField(max_length=16, blank=True, db_index=True)
    
    # Patient information
    patient_name = models.CharField(max_length=64)
    patient_id = models.CharField(max_length=64, db_index=True)
    patient_birth_date = models.DateField(null=True, blank=True)
    patient_sex = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True)
    
    # Study information
    study_date = models.DateField()
    study_time = models.TimeField(null=True, blank=True)
    study_description = models.CharField(max_length=64, blank=True)
    referring_physician = models.CharField(max_length=64, blank=True)
    institution_name = models.CharField(max_length=64, blank=True)
    
    # System information
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='studies')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='uploaded_studies')
    assigned_radiologist = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to={'role': UserRole.RADIOLOGIST},
        related_name='assigned_studies'
    )
    
    # Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Quality assurance
    qa_checked = models.BooleanField(default=False)
    qa_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['facility', 'status']),
            models.Index(fields=['assigned_radiologist', 'status']),
            models.Index(fields=['study_date']),
        ]
    
    def __str__(self):
        return f"{self.patient_name} - {self.study_description} ({self.study_date})"
    
    def get_total_images(self):
        """Get total number of images in this study"""
        return DICOMImage.objects.filter(series__study=self).count()
    
    def get_modalities(self):
        """Get list of modalities in this study"""
        return list(self.series_set.values_list('modality', flat=True).distinct())

class Series(models.Model):
    """DICOM Series model"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    series_instance_uid = models.CharField(max_length=64, unique=True, db_index=True)
    series_number = models.IntegerField()
    series_description = models.CharField(max_length=64, blank=True)
    modality = models.CharField(max_length=16)
    body_part_examined = models.CharField(max_length=16, blank=True)
    series_date = models.DateField(null=True, blank=True)
    series_time = models.TimeField(null=True, blank=True)
    
    # Technical parameters
    manufacturer = models.CharField(max_length=64, blank=True)
    manufacturer_model_name = models.CharField(max_length=64, blank=True)
    station_name = models.CharField(max_length=16, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['series_number']
        unique_together = ['study', 'series_number']
        verbose_name_plural = "Series"
    
    def __str__(self):
        return f"Series {self.series_number}: {self.series_description}"
    
    def get_image_count(self):
        """Get number of images in this series"""
        return self.dicomimage_set.count()

class DICOMImage(models.Model):
    """DICOM Image model"""
    series = models.ForeignKey(Series, on_delete=models.CASCADE)
    sop_instance_uid = models.CharField(max_length=64, unique=True, db_index=True)
    instance_number = models.IntegerField()
    
    # Image geometry
    slice_location = models.FloatField(null=True, blank=True)
    image_position_patient = models.CharField(max_length=64, blank=True)
    image_orientation_patient = models.CharField(max_length=64, blank=True)
    pixel_spacing = models.CharField(max_length=32, blank=True)
    slice_thickness = models.FloatField(null=True, blank=True)
    
    # Image characteristics
    rows = models.IntegerField()
    columns = models.IntegerField()
    bits_allocated = models.IntegerField()
    bits_stored = models.IntegerField()
    high_bit = models.IntegerField()
    
    # Display parameters
    window_width = models.FloatField(null=True, blank=True)
    window_center = models.FloatField(null=True, blank=True)
    
    # File information
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['instance_number']
        unique_together = ['series', 'instance_number']
    
    def __str__(self):
        return f"Image {self.instance_number}"

class Notification(models.Model):
    """Notification system for users"""
    
    TYPE_CHOICES = [
        ('upload_complete', 'Upload Complete'),
        ('upload_error', 'Upload Error'),
        ('new_study', 'New Study Available'),
        ('study_assigned', 'Study Assigned'),
        ('report_ready', 'Report Ready'),
        ('system_alert', 'System Alert'),
        ('quota_warning', 'Quota Warning'),
        ('dicom_received', 'DICOM Received from Modality'),
    ]
    
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    study = models.ForeignKey(Study, on_delete=models.CASCADE, null=True, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    is_email_sent = models.BooleanField(default=False)
    is_sms_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

class AuditLog(models.Model):
    """Audit log for tracking user actions"""
    
    ACTION_CHOICES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('upload', 'File Upload'),
        ('view_study', 'View Study'),
        ('edit_study', 'Edit Study'),
        ('delete_study', 'Delete Study'),
        ('create_report', 'Create Report'),
        ('edit_report', 'Edit Report'),
        ('dicom_received', 'DICOM Received'),
        ('system_config', 'System Configuration'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    
    # Related objects
    study = models.ForeignKey(Study, on_delete=models.SET_NULL, null=True, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Technical details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"

class Report(models.Model):
    """Radiology Report model with role-based access control"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('preliminary', 'Preliminary'),
        ('final', 'Final'),
        ('amended', 'Amended'),
        ('cancelled', 'Cancelled'),
    ]
    
    REPORT_TYPE_CHOICES = [
        ('diagnostic', 'Diagnostic Report'),
        ('consultation', 'Consultation'),
        ('addendum', 'Addendum'),
        ('amended', 'Amended Report'),
    ]
    
    # Core relationships
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='reports')
    radiologist = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        limit_choices_to={'role': UserRole.RADIOLOGIST},
        related_name='authored_reports'
    )
    
    # Report metadata
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default='diagnostic')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    accession_number = models.CharField(max_length=16, blank=True)
    
    # Report content
    clinical_history = models.TextField(blank=True, help_text="Clinical history and indication")
    technique = models.TextField(blank=True, help_text="Imaging technique and parameters")
    findings = models.TextField(help_text="Detailed findings")
    impression = models.TextField(help_text="Clinical impression and diagnosis")
    recommendations = models.TextField(blank=True, help_text="Recommendations and follow-up")
    
    # Additional fields
    comparison_studies = models.TextField(blank=True, help_text="Comparison with prior studies")
    limitations = models.TextField(blank=True, help_text="Study limitations")
    
    # Signatures and verification
    radiologist_signature = models.TextField(blank=True, help_text="Digital signature")
    signed_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role__in': [UserRole.RADIOLOGIST, UserRole.ADMIN]},
        related_name='verified_reports'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    
    # Version control for amendments
    version = models.PositiveIntegerField(default=1)
    parent_report = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='amendments'
    )
    amendment_reason = models.TextField(blank=True)
    
    # Print tracking
    print_count = models.PositiveIntegerField(default=0)
    last_printed_at = models.DateTimeField(null=True, blank=True)
    last_printed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='printed_reports'
    )
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['study', 'version']
        indexes = [
            models.Index(fields=['study', 'status']),
            models.Index(fields=['radiologist', 'status']),
            models.Index(fields=['status', 'finalized_at']),
        ]
    
    def __str__(self):
        return f"Report for {self.study.patient_name} - {self.study.study_description} (v{self.version})"
    
    def can_edit(self, user):
        """Check if user can edit this report"""
        if user.role == UserRole.ADMIN:
            return True
        elif user.role == UserRole.RADIOLOGIST:
            # Radiologists can edit their own reports if not finalized
            return (self.radiologist == user and 
                   self.status in ['draft', 'preliminary'])
        return False
    
    def can_view(self, user):
        """Check if user can view this report"""
        if user.role == UserRole.ADMIN:
            return True
        elif user.role == UserRole.RADIOLOGIST:
            return True  # All radiologists can view all reports
        elif user.role in [UserRole.FACILITY, UserRole.TECHNICIAN]:
            # Facility users can only view reports for their facility's studies
            return (self.study.facility == user.facility and 
                   self.status in ['final', 'amended'])
        return False
    
    def can_print(self, user):
        """Check if user can print this report"""
        if user.role == UserRole.ADMIN:
            return True
        elif user.role == UserRole.RADIOLOGIST:
            return self.status in ['final', 'amended']
        elif user.role in [UserRole.FACILITY, UserRole.TECHNICIAN]:
            # Facility users can only print reports for their facility's studies
            return (self.study.facility == user.facility and 
                   self.status in ['final', 'amended'])
        return False
    
    def finalize(self, user):
        """Finalize the report (only radiologists can do this)"""
        if user.role == UserRole.RADIOLOGIST and self.radiologist == user:
            self.status = 'final'
            self.finalized_at = timezone.now()
            self.signed_at = timezone.now()
            self.save(update_fields=['status', 'finalized_at', 'signed_at'])
            
            # Create notification for facility
            self.create_report_notification()
            
            return True
        return False
    
    def create_amendment(self, user, reason):
        """Create an amended version of this report"""
        if not self.can_edit(user):
            return None
        
        # Create new report version
        amended_report = Report.objects.create(
            study=self.study,
            radiologist=user,
            report_type='amended',
            status='draft',
            version=self.version + 1,
            parent_report=self,
            amendment_reason=reason,
            clinical_history=self.clinical_history,
            technique=self.technique,
            findings=self.findings,
            impression=self.impression,
            recommendations=self.recommendations,
            comparison_studies=self.comparison_studies,
            limitations=self.limitations,
        )
        
        # Mark original as amended
        self.status = 'amended'
        self.save(update_fields=['status'])
        
        return amended_report
    
    def record_print(self, user):
        """Record that this report was printed"""
        self.print_count += 1
        self.last_printed_at = timezone.now()
        self.last_printed_by = user
        self.save(update_fields=['print_count', 'last_printed_at', 'last_printed_by'])
        
        # Log the print action
        AuditLog.objects.create(
            user=user,
            action='print_report',
            description=f"Printed report for study {self.study.study_instance_uid}",
            study=self.study,
            facility=user.facility,
            ip_address=getattr(user, '_current_ip', None),
        )
    
    def create_report_notification(self):
        """Create notifications when report is finalized"""
        # Notify facility users
        facility_users = CustomUser.objects.filter(
            facility=self.study.facility,
            role__in=[UserRole.FACILITY, UserRole.TECHNICIAN],
            email_notifications=True
        )
        
        for user in facility_users:
            Notification.objects.create(
                recipient=user,
                notification_type='report_ready',
                title=f'Report Ready - {self.study.patient_name}',
                message=f'Radiology report is now available for study: {self.study.study_description}',
                study=self.study,
                facility=self.study.facility
            )
        
        # Notify admins
        admin_users = CustomUser.objects.filter(
            role=UserRole.ADMIN,
            email_notifications=True
        )
        
        for user in admin_users:
            Notification.objects.create(
                recipient=user,
                notification_type='report_ready',
                title=f'Report Completed - {self.study.patient_name}',
                message=f'Dr. {self.radiologist.get_full_name()} completed report for {self.study.study_description}',
                study=self.study,
                facility=self.study.facility
            )
    
    def get_printable_content(self):
        """Get formatted content for printing"""
        return {
            'header': {
                'patient_name': self.study.patient_name,
                'patient_id': self.study.patient_id,
                'dob': self.study.patient_birth_date,
                'study_date': self.study.study_date,
                'accession_number': self.study.accession_number,
                'study_description': self.study.study_description,
                'facility': self.study.facility.name,
                'radiologist': self.radiologist.get_full_name(),
                'report_date': self.finalized_at or self.created_at,
                'version': self.version,
            },
            'content': {
                'clinical_history': self.clinical_history,
                'technique': self.technique,
                'findings': self.findings,
                'impression': self.impression,
                'recommendations': self.recommendations,
                'comparison_studies': self.comparison_studies,
                'limitations': self.limitations,
            },
            'signature': {
                'radiologist': self.radiologist.get_full_name(),
                'license': self.radiologist.license_number,
                'signed_at': self.signed_at,
                'verified_by': self.verified_by.get_full_name() if self.verified_by else None,
                'verified_at': self.verified_at,
            },
            'metadata': {
                'print_count': self.print_count,
                'printed_at': timezone.now(),
                'printed_by': getattr(self, '_printed_by', None),
                'status': self.get_status_display(),
            }
        }