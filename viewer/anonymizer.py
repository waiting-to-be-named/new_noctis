"""
DICOM Anonymization Utility
Removes or replaces patient identifiable information from DICOM files
"""
import pydicom
from datetime import datetime, timedelta
import hashlib
import random
import string
from typing import List, Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)


class DicomAnonymizer:
    """Anonymize DICOM files by removing/replacing patient information"""
    
    # Tags that contain patient identifiable information
    PATIENT_INFO_TAGS = [
        (0x0010, 0x0010),  # PatientName
        (0x0010, 0x0020),  # PatientID
        (0x0010, 0x0030),  # PatientBirthDate
        (0x0010, 0x0040),  # PatientSex
        (0x0010, 0x1000),  # OtherPatientIDs
        (0x0010, 0x1001),  # OtherPatientNames
        (0x0010, 0x1010),  # PatientAge
        (0x0010, 0x1020),  # PatientSize
        (0x0010, 0x1030),  # PatientWeight
        (0x0010, 0x1040),  # PatientAddress
        (0x0010, 0x2160),  # EthnicGroup
        (0x0010, 0x4000),  # PatientComments
    ]
    
    # Tags that may contain identifiable information
    POTENTIALLY_IDENTIFIABLE_TAGS = [
        (0x0008, 0x0014),  # InstanceCreatorUID
        (0x0008, 0x0018),  # SOPInstanceUID
        (0x0008, 0x0050),  # AccessionNumber
        (0x0008, 0x0080),  # InstitutionName
        (0x0008, 0x0081),  # InstitutionAddress
        (0x0008, 0x0090),  # ReferringPhysicianName
        (0x0008, 0x0092),  # ReferringPhysicianAddress
        (0x0008, 0x0094),  # ReferringPhysicianTelephoneNumbers
        (0x0008, 0x1048),  # PhysiciansOfRecord
        (0x0008, 0x1050),  # PerformingPhysicianName
        (0x0008, 0x1060),  # NameOfPhysiciansReadingStudy
        (0x0008, 0x1070),  # OperatorsName
        (0x0020, 0x000D),  # StudyInstanceUID
        (0x0020, 0x000E),  # SeriesInstanceUID
        (0x0020, 0x0010),  # StudyID
        (0x0020, 0x0052),  # FrameOfReferenceUID
        (0x0020, 0x0200),  # SynchronizationFrameOfReferenceUID
        (0x0040, 0x0275),  # RequestAttributesSequence
        (0x0040, 0xA730),  # ContentSequence
        (0x0088, 0x0140),  # StorageMediaFileSetUID
    ]
    
    def __init__(self, keep_dates: bool = False, keep_uid_structure: bool = True):
        """
        Initialize the anonymizer
        
        Args:
            keep_dates: If True, shifts dates instead of removing them
            keep_uid_structure: If True, maintains UID relationships
        """
        self.keep_dates = keep_dates
        self.keep_uid_structure = keep_uid_structure
        self.uid_mapping = {}
        self.date_shift = None
        self.patient_id_mapping = {}
        
    def anonymize_file(self, dicom_file_path: str, output_path: Optional[str] = None,
                      patient_id: Optional[str] = None) -> pydicom.Dataset:
        """
        Anonymize a single DICOM file
        
        Args:
            dicom_file_path: Path to the DICOM file
            output_path: Path to save anonymized file (optional)
            patient_id: Custom patient ID to use (optional)
            
        Returns:
            Anonymized DICOM dataset
        """
        try:
            # Read DICOM file
            ds = pydicom.dcmread(dicom_file_path)
            
            # Anonymize the dataset
            anonymized_ds = self.anonymize_dataset(ds, patient_id)
            
            # Save if output path provided
            if output_path:
                anonymized_ds.save_as(output_path)
                logger.info(f"Anonymized file saved to: {output_path}")
            
            return anonymized_ds
            
        except Exception as e:
            logger.error(f"Error anonymizing file {dicom_file_path}: {e}")
            raise
    
    def anonymize_dataset(self, ds: pydicom.Dataset, patient_id: Optional[str] = None) -> pydicom.Dataset:
        """
        Anonymize a DICOM dataset
        
        Args:
            ds: DICOM dataset to anonymize
            patient_id: Custom patient ID to use (optional)
            
        Returns:
            Anonymized DICOM dataset
        """
        # Create a copy to avoid modifying original
        anon_ds = ds.copy()
        
        # Generate or retrieve patient ID mapping
        original_patient_id = getattr(ds, 'PatientID', 'Unknown')
        if original_patient_id not in self.patient_id_mapping:
            if patient_id:
                self.patient_id_mapping[original_patient_id] = patient_id
            else:
                self.patient_id_mapping[original_patient_id] = self._generate_anonymous_id()
        
        # Set date shift if keeping dates
        if self.keep_dates and self.date_shift is None:
            self.date_shift = random.randint(-365, 365)
        
        # Remove patient information tags
        for tag in self.PATIENT_INFO_TAGS:
            if tag in anon_ds:
                if tag == (0x0010, 0x0010):  # PatientName
                    anon_ds.PatientName = f"Anonymous_{self.patient_id_mapping[original_patient_id]}"
                elif tag == (0x0010, 0x0020):  # PatientID
                    anon_ds.PatientID = self.patient_id_mapping[original_patient_id]
                elif tag == (0x0010, 0x0030) and self.keep_dates:  # PatientBirthDate
                    anon_ds.PatientBirthDate = self._shift_date(anon_ds.PatientBirthDate)
                else:
                    delattr(anon_ds, anon_ds[tag].keyword)
        
        # Handle potentially identifiable tags
        for tag in self.POTENTIALLY_IDENTIFIABLE_TAGS:
            if tag in anon_ds:
                if tag[0] == 0x0020 or tag == (0x0008, 0x0018):  # UIDs
                    if self.keep_uid_structure:
                        uid = str(anon_ds[tag].value)
                        anon_ds[tag].value = self._anonymize_uid(uid)
                    else:
                        delattr(anon_ds, anon_ds[tag].keyword)
                elif tag in [(0x0008, 0x0080), (0x0008, 0x0081)]:  # Institution info
                    anon_ds[tag].value = "Anonymous Institution"
                elif 'Physician' in anon_ds[tag].keyword or 'Operator' in anon_ds[tag].keyword:
                    anon_ds[tag].value = "Anonymous"
                else:
                    delattr(anon_ds, anon_ds[tag].keyword)
        
        # Handle dates
        if self.keep_dates:
            date_tags = [
                (0x0008, 0x0020),  # StudyDate
                (0x0008, 0x0021),  # SeriesDate
                (0x0008, 0x0022),  # AcquisitionDate
                (0x0008, 0x0023),  # ContentDate
            ]
            for tag in date_tags:
                if tag in anon_ds:
                    anon_ds[tag].value = self._shift_date(anon_ds[tag].value)
        
        # Remove private tags
        anon_ds.remove_private_tags()
        
        # Add anonymization information
        anon_ds.add_new((0x0012, 0x0062), 'CS', 'YES')  # PatientIdentityRemoved
        anon_ds.add_new((0x0012, 0x0063), 'LO', 'NoctisView Anonymizer')  # DeidentificationMethod
        
        return anon_ds
    
    def anonymize_batch(self, file_paths: List[str], output_dir: str,
                       progress_callback: Optional[callable] = None) -> List[str]:
        """
        Anonymize multiple DICOM files
        
        Args:
            file_paths: List of DICOM file paths
            output_dir: Directory to save anonymized files
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of anonymized file paths
        """
        anonymized_paths = []
        
        for i, file_path in enumerate(file_paths):
            try:
                # Generate output filename
                filename = f"anon_{i:06d}.dcm"
                output_path = f"{output_dir}/{filename}"
                
                # Anonymize file
                self.anonymize_file(file_path, output_path)
                anonymized_paths.append(output_path)
                
                # Progress callback
                if progress_callback:
                    progress_callback(i + 1, len(file_paths))
                    
            except Exception as e:
                logger.error(f"Failed to anonymize {file_path}: {e}")
                continue
        
        return anonymized_paths
    
    def _generate_anonymous_id(self) -> str:
        """Generate anonymous patient ID"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    def _anonymize_uid(self, uid: str) -> str:
        """Anonymize UID while maintaining structure"""
        if uid in self.uid_mapping:
            return self.uid_mapping[uid]
        
        # Generate new UID maintaining the prefix
        parts = uid.split('.')
        if len(parts) > 2:
            # Keep first two parts (usually root and org)
            prefix = '.'.join(parts[:2])
            # Generate hash for the rest
            suffix_hash = hashlib.md5(uid.encode()).hexdigest()[:16]
            new_uid = f"{prefix}.{suffix_hash}"
        else:
            # Generate completely new UID
            new_uid = f"2.25.{random.randint(10**15, 10**16-1)}"
        
        self.uid_mapping[uid] = new_uid
        return new_uid
    
    def _shift_date(self, date_string: str) -> str:
        """Shift date by random amount"""
        if not date_string or len(date_string) != 8:
            return date_string
        
        try:
            date = datetime.strptime(date_string, '%Y%m%d')
            shifted_date = date + timedelta(days=self.date_shift)
            return shifted_date.strftime('%Y%m%d')
        except ValueError:
            return date_string
    
    def create_anonymization_report(self, original_ds: pydicom.Dataset,
                                   anonymized_ds: pydicom.Dataset) -> Dict:
        """
        Create a report of what was anonymized
        
        Args:
            original_ds: Original DICOM dataset
            anonymized_ds: Anonymized DICOM dataset
            
        Returns:
            Dictionary containing anonymization details
        """
        report = {
            'original_patient_id': getattr(original_ds, 'PatientID', 'Unknown'),
            'anonymized_patient_id': getattr(anonymized_ds, 'PatientID', 'Unknown'),
            'removed_tags': [],
            'modified_tags': [],
            'date_shift': self.date_shift if self.keep_dates else None,
        }
        
        # Check removed tags
        for tag in self.PATIENT_INFO_TAGS + self.POTENTIALLY_IDENTIFIABLE_TAGS:
            if tag in original_ds and tag not in anonymized_ds:
                report['removed_tags'].append({
                    'tag': str(tag),
                    'name': original_ds[tag].keyword,
                    'original_value': str(original_ds[tag].value)
                })
            elif tag in original_ds and tag in anonymized_ds:
                if original_ds[tag].value != anonymized_ds[tag].value:
                    report['modified_tags'].append({
                        'tag': str(tag),
                        'name': original_ds[tag].keyword,
                        'original_value': str(original_ds[tag].value),
                        'anonymized_value': str(anonymized_ds[tag].value)
                    })
        
        return report


class SecureAnonymizer(DicomAnonymizer):
    """Enhanced anonymizer with additional security features"""
    
    def __init__(self, encryption_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.encryption_key = encryption_key or self._generate_key()
        
    def _generate_key(self) -> str:
        """Generate encryption key"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a value using the key"""
        # Simple XOR encryption for demonstration
        encrypted = []
        for i, char in enumerate(value):
            key_char = self.encryption_key[i % len(self.encryption_key)]
            encrypted.append(chr(ord(char) ^ ord(key_char)))
        return ''.join(encrypted)
    
    def save_mapping(self, filepath: str):
        """Save patient ID mapping to file"""
        import json
        with open(filepath, 'w') as f:
            json.dump({
                'patient_mapping': self.patient_id_mapping,
                'uid_mapping': self.uid_mapping,
                'date_shift': self.date_shift
            }, f, indent=2)
    
    def load_mapping(self, filepath: str):
        """Load patient ID mapping from file"""
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
            self.patient_id_mapping = data.get('patient_mapping', {})
            self.uid_mapping = data.get('uid_mapping', {})
            self.date_shift = data.get('date_shift', None)