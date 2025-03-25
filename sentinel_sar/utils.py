"""
Utility functions for the Sentinel SAR Analysis package.
"""

import os
import logging
import zipfile
import datetime
from typing import Optional, List
import numpy as np

logger = logging.getLogger(__name__)

def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def extract_zip_file(file_path: str, extract_dir: Optional[str] = None) -> str:
    """Extract a ZIP file and return the extraction directory."""
    if extract_dir is None:
        extract_dir = os.path.join(os.path.dirname(file_path), 'extracted')
    
    os.makedirs(extract_dir, exist_ok=True)
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        logger.info(f"Successfully extracted {file_path} to {extract_dir}")
        return extract_dir
    except Exception as e:
        logger.error(f"Error extracting ZIP file: {e}")
        return ""

def find_files_by_extension(directory: str, extension: str) -> List[str]:
    """Find all files with a specific extension in a directory (recursive)."""
    found_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(extension.lower()):
                found_files.append(os.path.join(root, file))
    return found_files

def convert_date_format(date_str: str, input_format: str, output_format: str) -> str:
    """Convert a date string from one format to another."""
    try:
        date_obj = datetime.datetime.strptime(date_str, input_format)
        return date_obj.strftime(output_format)
    except ValueError as e:
        logger.error(f"Error converting date format: {e}")
        return date_str

def normalize_array(array: np.ndarray) -> np.ndarray:
    """Normalize an array to the range [0, 1]."""
    min_val = np.min(array)
    max_val = np.max(array)
    if max_val == min_val:
        return np.zeros_like(array)
    return (array - min_val) / (max_val - min_val)

def create_directory_if_not_exists(directory: str) -> bool:
    """Create a directory if it doesn't exist."""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")
        return False

def get_file_size(file_path: str) -> str:
    """Get the size of a file in a human-readable format."""
    try:
        size_bytes = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    except Exception as e:
        logger.error(f"Error getting file size: {e}")
        return "Unknown"

def validate_coordinates(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> bool:
    """Validate geographic coordinates."""
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        logger.error("Longitude values must be between -180 and 180 degrees")
        return False
    
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        logger.error("Latitude values must be between -90 and 90 degrees")
        return False
    
    if min_lon >= max_lon:
        logger.error("Minimum longitude must be less than maximum longitude")
        return False
    
    if min_lat >= max_lat:
        logger.error("Minimum latitude must be less than maximum latitude")
        return False
    
    return True

def validate_date_range(start_date: str, end_date: str, date_format: str = '%Y%m%d') -> bool:
    """Validate a date range."""
    try:
        start = datetime.datetime.strptime(start_date, date_format).date()
        end = datetime.datetime.strptime(end_date, date_format).date()
        
        if start > end:
            logger.error("Start date must be before end date")
            return False
        
        # Check if the date range is not too large (e.g., more than 1 year)
        if (end - start).days > 365:
            logger.warning("Date range is more than 1 year, which may result in a large number of products")
        
        return True
    except ValueError as e:
        logger.error(f"Error validating date range: {e}")
        return False