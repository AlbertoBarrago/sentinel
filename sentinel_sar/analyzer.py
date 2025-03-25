"""
Main SARAnalyzer class that coordinates all SAR data operations.
"""

from typing import Optional, Dict, List, Any
import logging
from pathlib import Path

from sentinel_sar.auth import authenticate, authenticate_cosmo
from sentinel_sar.processing import (
    create_aoi_from_coordinates,
    search_sar_data,
    download_products,
    process_sentinel1_data,
    search_cosmo_data,
    download_cosmo_products,
    process_cosmo_data,
    preprocess_sar_data,
    detect_subsurface_features
)
from sentinel_sar.visualization import visualize_results

logger = logging.getLogger(__name__)

class SARAnalyzer:
    """A class for fetching and analyzing SAR data from Copernicus and COSMO-SkyMed."""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, 
                 client_id: Optional[str] = None, client_secret: Optional[str] = None,
                 cosmo_username: Optional[str] = None, cosmo_password: Optional[str] = None):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.cosmo_username = cosmo_username
        self.cosmo_password = cosmo_password
        self.api = None
        self.cosmo_api_token = None
        self.products = None
        self.download_path = Path.cwd() / 'data'
        self.download_path.mkdir(exist_ok=True)
    
    def authenticate(self, api_url: str = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token') -> bool:
        """Authenticate with the Copernicus Data Space Ecosystem or Open Access Hub."""
        return authenticate(self, api_url)
    
    def authenticate_cosmo(self, api_url: str = 'https://api.registration.cosmo-skymed.it/auth/login') -> bool:
        """Authenticate with the COSMO-SkyMed data portal."""
        return authenticate_cosmo(self, api_url)
    
    def create_aoi_from_coordinates(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
        """Create an Area of Interest (AOI) from coordinates."""
        return create_aoi_from_coordinates(self, min_lon, min_lat, max_lon, max_lat)
    
    def search_sar_data(self, footprint: str, start_date: str, end_date: str, platform_name: str = 'Sentinel-1') -> Dict:
        """Search for SAR data within the specified parameters."""
        return search_sar_data(self, footprint, start_date, end_date, platform_name)
    
    def search_cosmo_data(self, footprint: str, start_date: str, end_date: str) -> Dict:
        """Search for COSMO-SkyMed SAR data within the specified parameters."""
        return search_cosmo_data(self, footprint, start_date, end_date)
    
    def download_products(self, limit: int = 1) -> List[str]:
        """Download the found products."""
        return download_products(self, limit)
    
    def download_cosmo_products(self, limit: int = 1) -> List[str]:
        """Download the found COSMO-SkyMed products."""
        return download_cosmo_products(self, limit)
    
    def process_sentinel1_data(self, file_path: str) -> Optional[str]:
        """Process Sentinel-1 specific data format."""
        return process_sentinel1_data(self, file_path)
    
    def process_cosmo_data(self, file_path: str) -> Optional[str]:
        """Process COSMO-SkyMed specific data format."""
        return process_cosmo_data(self, file_path)
    
    def preprocess_sar_data(self, file_path: str) -> Optional[Any]:
        """Preprocess the SAR data for analysis."""
        return preprocess_sar_data(self, file_path)

    @staticmethod
    def detect_subsurface_features(sar_data: Any, threshold: float = 0.7) -> Optional[Any]:
        """Detect potential subsurface features in the SAR data."""
        return detect_subsurface_features(sar_data, threshold)
    
    def visualize_results(self, original_data: Any, processed_data: Any, 
                          features: Any, title: str = "SAR Analysis Results") -> None:
        """Visualize the original data, processed data, and detected features."""
        visualize_results(self, original_data, processed_data, features, title)
    
    def analyze_area(
        self,
        min_lon: float,
        min_lat: float, 
        max_lon: float,
        max_lat: float,
        start_date: str,
        end_date: str,
        data_source: str = 'sentinel'
    ) -> bool:
        """Complete workflow to analyze an area of interest."""
        try:
            footprint = self.create_aoi_from_coordinates(
                min_lon, min_lat, max_lon, max_lat
            )
            
            if data_source.lower() == 'cosmo':
                # Use COSMO-SkyMed data
                if not self.authenticate_cosmo():
                    return False
                
                products = self.search_cosmo_data(footprint, start_date, end_date)
                if not products:
                    logger.warning("No COSMO-SkyMed products found for the specified parameters.")
                    return False
                
                downloaded_files = self.download_cosmo_products(limit=1)
                if not downloaded_files:
                    logger.error("Failed to download any COSMO-SkyMed products.")
                    return False
                
                for file_path in downloaded_files:
                    logger.info(f"Processing {file_path}...")
                    
                    processed_file = self.process_cosmo_data(file_path)
                    if processed_file:
                        # Continue with the rest of the analysis
                        processed_data = self.preprocess_sar_data(processed_file)
                        if processed_data is not None:
                            features = self.detect_subsurface_features(processed_data)
                            if features is not None:
                                try:
                                    import rasterio
                                    with rasterio.open(processed_file) as src:
                                        original_data = src.read(1)
                                    self.visualize_results(
                                        original_data, 
                                        processed_data, 
                                        features,
                                        title="COSMO-SkyMed SAR Analysis Results"
                                    )
                                except Exception as e:
                                    logger.error(f"Error visualizing results: {e}")
                                    continue
            else:
                # Use Sentinel data (default)
                if not self.authenticate():
                    return False
                
                products = self.search_sar_data(footprint, start_date, end_date)
                if not products:
                    logger.warning("No products found for the specified parameters.")
                    return False
                
                downloaded_files = self.download_products(limit=1)
                if not downloaded_files:
                    logger.error("Failed to download any products.")
                    return False
                
                for file_path in downloaded_files:
                    logger.info(f"Processing {file_path}...")
                    
                    processed_file = self.process_sentinel1_data(file_path)
                    if processed_file:
                        processed_data = self.preprocess_sar_data(processed_file)
                        if processed_data is not None:
                            features = self.detect_subsurface_features(processed_data)
                            if features is not None:
                                try:
                                    import rasterio
                                    with rasterio.open(processed_file) as src:
                                        original_data = src.read(1)
                                    self.visualize_results(
                                        original_data, 
                                        processed_data, 
                                        features
                                    )
                                except Exception as e:
                                    logger.error(f"Error visualizing results: {e}")
                                    continue

            return True
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return False