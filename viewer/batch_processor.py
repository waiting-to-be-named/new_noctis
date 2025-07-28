"""
Batch Processing Utility for DICOM Files
Handles large-scale processing of multiple DICOM files
"""
import os
import pydicom
from typing import List, Dict, Callable, Optional
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging
from tqdm import tqdm
import pandas as pd
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class DicomBatchProcessor:
    """Process multiple DICOM files in batch with parallel processing"""
    
    def __init__(self, num_workers: Optional[int] = None):
        """
        Initialize batch processor
        
        Args:
            num_workers: Number of parallel workers (default: CPU count)
        """
        self.num_workers = num_workers or mp.cpu_count()
        
    def process_directory(self, directory_path: str, 
                         process_func: Callable,
                         output_dir: Optional[str] = None,
                         file_filter: Optional[Callable] = None,
                         progress_callback: Optional[Callable] = None) -> Dict:
        """
        Process all DICOM files in a directory
        
        Args:
            directory_path: Path to directory containing DICOM files
            process_func: Function to process each DICOM file
            output_dir: Directory to save processed files
            file_filter: Optional filter function for files
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with processing results
        """
        # Find all DICOM files
        dicom_files = self._find_dicom_files(directory_path, file_filter)
        
        if not dicom_files:
            logger.warning(f"No DICOM files found in {directory_path}")
            return {'processed': 0, 'failed': 0, 'files': []}
        
        logger.info(f"Found {len(dicom_files)} DICOM files to process")
        
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Process files
        results = self._process_files_parallel(
            dicom_files, 
            process_func, 
            output_dir,
            progress_callback
        )
        
        return results
    
    def _find_dicom_files(self, directory: str, 
                         file_filter: Optional[Callable] = None) -> List[str]:
        """Find all DICOM files in directory"""
        dicom_files = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                filepath = os.path.join(root, file)
                
                # Check if it's a DICOM file
                if self._is_dicom_file(filepath):
                    # Apply filter if provided
                    if file_filter is None or file_filter(filepath):
                        dicom_files.append(filepath)
        
        return dicom_files
    
    def _is_dicom_file(self, filepath: str) -> bool:
        """Check if file is a valid DICOM file"""
        try:
            # Try to read DICOM header
            pydicom.dcmread(filepath, stop_before_pixels=True)
            return True
        except:
            return False
    
    def _process_files_parallel(self, files: List[str],
                               process_func: Callable,
                               output_dir: Optional[str],
                               progress_callback: Optional[Callable]) -> Dict:
        """Process files in parallel"""
        results = {
            'processed': 0,
            'failed': 0,
            'files': [],
            'errors': []
        }
        
        # Use ThreadPoolExecutor for I/O bound tasks
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            futures = []
            for i, filepath in enumerate(files):
                future = executor.submit(
                    self._process_single_file,
                    filepath,
                    process_func,
                    output_dir,
                    i
                )
                futures.append((filepath, future))
            
            # Collect results
            for i, (filepath, future) in enumerate(futures):
                try:
                    result = future.result()
                    if result['success']:
                        results['processed'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(result['error'])
                    
                    results['files'].append(result)
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(i + 1, len(files))
                        
                except Exception as e:
                    logger.error(f"Error processing {filepath}: {e}")
                    results['failed'] += 1
                    results['errors'].append(str(e))
        
        return results
    
    def _process_single_file(self, filepath: str,
                            process_func: Callable,
                            output_dir: Optional[str],
                            index: int) -> Dict:
        """Process a single DICOM file"""
        try:
            # Read DICOM file
            ds = pydicom.dcmread(filepath)
            
            # Apply processing function
            processed_ds = process_func(ds)
            
            # Save if output directory specified
            output_path = None
            if output_dir and processed_ds is not None:
                filename = f"processed_{index:06d}.dcm"
                output_path = os.path.join(output_dir, filename)
                processed_ds.save_as(output_path)
            
            return {
                'success': True,
                'input_path': filepath,
                'output_path': output_path,
                'patient_id': getattr(ds, 'PatientID', 'Unknown'),
                'study_date': str(getattr(ds, 'StudyDate', 'Unknown'))
            }
            
        except Exception as e:
            return {
                'success': False,
                'input_path': filepath,
                'error': str(e)
            }
    
    def generate_report(self, results: Dict, output_path: str):
        """Generate processing report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_files': results['processed'] + results['failed'],
            'processed': results['processed'],
            'failed': results['failed'],
            'success_rate': results['processed'] / (results['processed'] + results['failed']) * 100,
            'errors': results['errors']
        }
        
        # Save report
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Create detailed CSV report
        csv_path = output_path.replace('.json', '.csv')
        df = pd.DataFrame(results['files'])
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Reports saved to {output_path} and {csv_path}")


class DicomSeriesProcessor:
    """Process DICOM files organized by series"""
    
    def __init__(self):
        self.series_map = {}
        
    def organize_by_series(self, dicom_files: List[str]) -> Dict[str, List[str]]:
        """Organize DICOM files by series"""
        series_map = {}
        
        for filepath in dicom_files:
            try:
                ds = pydicom.dcmread(filepath, stop_before_pixels=True)
                series_uid = getattr(ds, 'SeriesInstanceUID', 'Unknown')
                
                if series_uid not in series_map:
                    series_map[series_uid] = []
                
                series_map[series_uid].append(filepath)
                
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")
        
        return series_map
    
    def process_series(self, series_files: List[str],
                      process_func: Callable) -> List[pydicom.Dataset]:
        """Process all files in a series"""
        processed_files = []
        
        # Sort files by instance number
        sorted_files = self._sort_by_instance_number(series_files)
        
        for filepath in sorted_files:
            try:
                ds = pydicom.dcmread(filepath)
                processed_ds = process_func(ds)
                processed_files.append(processed_ds)
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
        
        return processed_files
    
    def _sort_by_instance_number(self, files: List[str]) -> List[str]:
        """Sort files by instance number"""
        file_info = []
        
        for filepath in files:
            try:
                ds = pydicom.dcmread(filepath, stop_before_pixels=True)
                instance_num = getattr(ds, 'InstanceNumber', 0)
                file_info.append((instance_num, filepath))
            except:
                file_info.append((0, filepath))
        
        # Sort by instance number
        file_info.sort(key=lambda x: x[0])
        
        return [f[1] for f in file_info]


class DicomMetadataExtractor:
    """Extract metadata from DICOM files for analysis"""
    
    def __init__(self):
        self.metadata_fields = [
            'PatientID', 'PatientName', 'PatientBirthDate', 'PatientSex',
            'StudyInstanceUID', 'StudyDate', 'StudyTime', 'StudyDescription',
            'SeriesInstanceUID', 'SeriesNumber', 'SeriesDescription', 'Modality',
            'InstanceNumber', 'SOPInstanceUID', 'Rows', 'Columns',
            'PixelSpacing', 'SliceThickness', 'WindowCenter', 'WindowWidth',
            'InstitutionName', 'Manufacturer', 'ManufacturerModelName'
        ]
    
    def extract_from_directory(self, directory: str,
                              output_csv: Optional[str] = None) -> pd.DataFrame:
        """Extract metadata from all DICOM files in directory"""
        processor = DicomBatchProcessor()
        dicom_files = processor._find_dicom_files(directory)
        
        metadata_list = []
        
        for filepath in tqdm(dicom_files, desc="Extracting metadata"):
            metadata = self.extract_from_file(filepath)
            if metadata:
                metadata['filepath'] = filepath
                metadata_list.append(metadata)
        
        # Create DataFrame
        df = pd.DataFrame(metadata_list)
        
        # Save to CSV if specified
        if output_csv:
            df.to_csv(output_csv, index=False)
            logger.info(f"Metadata saved to {output_csv}")
        
        return df
    
    def extract_from_file(self, filepath: str) -> Optional[Dict]:
        """Extract metadata from single DICOM file"""
        try:
            ds = pydicom.dcmread(filepath, stop_before_pixels=True)
            
            metadata = {}
            for field in self.metadata_fields:
                if hasattr(ds, field):
                    value = getattr(ds, field)
                    # Convert to string for consistency
                    metadata[field] = str(value)
                else:
                    metadata[field] = None
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {filepath}: {e}")
            return None
    
    def analyze_metadata(self, df: pd.DataFrame) -> Dict:
        """Analyze extracted metadata"""
        analysis = {
            'total_files': len(df),
            'unique_patients': df['PatientID'].nunique(),
            'unique_studies': df['StudyInstanceUID'].nunique(),
            'unique_series': df['SeriesInstanceUID'].nunique(),
            'modalities': df['Modality'].value_counts().to_dict(),
            'date_range': {
                'earliest': df['StudyDate'].min(),
                'latest': df['StudyDate'].max()
            },
            'manufacturers': df['Manufacturer'].value_counts().to_dict()
        }
        
        return analysis


# Example processing functions
def example_anonymize_func(ds: pydicom.Dataset) -> pydicom.Dataset:
    """Example function to anonymize DICOM dataset"""
    from .anonymizer import DicomAnonymizer
    anonymizer = DicomAnonymizer()
    return anonymizer.anonymize_dataset(ds)


def example_enhance_func(ds: pydicom.Dataset) -> pydicom.Dataset:
    """Example function to enhance DICOM image"""
    from .ai_utils import DicomImageAnalyzer
    
    if hasattr(ds, 'pixel_array'):
        analyzer = DicomImageAnalyzer()
        image_array = ds.pixel_array
        enhanced = analyzer.enhance_image(image_array, 'auto')
        ds.PixelData = enhanced.tobytes()
    
    return ds