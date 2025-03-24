#!/usr/bin/env python3
"""
Sentinel SAR Data Analysis Tool

Disclaimer: Work in progress...

This script fetches and analyzes Synthetic Aperture Radar (SAR) data from Copernicus
using the sentinelsat library. It allows for data acquisition based on coordinates,
processing the imagery using rasterio, and applying signal processing techniques
to detect subsurface anomalies.

Requirements:
    - sentinelsat
    - rasterio 
    - numpy
    - matplotlib
    - scipy
"""

from typing import Optional, Dict, List, Tuple, Any
import os
import sys
import datetime
import logging
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from datetime import date
import rasterio
from rasterio.errors import RasterioIOError
from rasterio.plot import show
from scipy import signal, ndimage
from shapely.geometry import box
import geopandas as gpd
from getpass import getpass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SARAnalyzer:
    """A class for fetching and analyzing SAR data from Copernicus."""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, 
                 client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.api: Optional[SentinelAPI] = None
        self.products: Optional[Dict] = None
        self.download_path = Path.cwd() / 'data'
        self.download_path.mkdir(exist_ok=True)
        
    def authenticate(self, api_url: str = 'https://apihub.copernicus.eu/apihub') -> bool:
        """Authenticate with the Copernicus Data Space Ecosystem or Open Access Hub."""
        try:
            # Check if we're using the new CDSE API
            if 'dataspace.copernicus.eu' in api_url or 'catalogue.dataspace.copernicus.eu' in api_url:
                if not self.client_id:
                    self.client_id = input("Enter your Copernicus Data Space client ID: ")
                if not self.client_secret:
                    self.client_secret = getpass("Enter your Copernicus Data Space client secret: ")
                
                logger.info(f"Attempting to authenticate with CDSE at {api_url}")
                # For CDSE, we use the client_id as username and client_secret as password
                self.api = SentinelAPI(
                    self.client_id,
                    self.client_secret,
                    api_url
                )
            else:
                # Traditional username/password for older APIs
                if not self.username:
                    self.username = input("Enter your Copernicus username: ")
                if not self.password:
                    self.password = getpass("Enter your Copernicus password: ")
                
                logger.info(f"Attempting to authenticate with {api_url}")
                self.api = SentinelAPI(
                    self.username, 
                    self.password, 
                    api_url
                )
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            logger.info("Note: For the new Copernicus Data Space Ecosystem, you need to register at https://dataspace.copernicus.eu/ and create API credentials")
            return False
    
    def create_aoi_from_coordinates(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
        """Create an Area of Interest (AOI) from coordinates."""
        try:
            # Create a bounding box
            bbox = box(min_lon, min_lat, max_lon, max_lat)
            
            # Convert to GeoDataFrame
            geo_df = gpd.GeoDataFrame({'geometry': [bbox]}, crs='EPSG:4326')
            
            # Save to a temporary GeoJSON file
            temp_geojson = self.download_path / 'temp_aoi.geojson'
            geo_df.to_file(temp_geojson, driver='GeoJSON')
            
            # Convert to WKT
            footprint = geojson_to_wkt(read_geojson(str(temp_geojson)))
            return footprint
        except Exception as e:
            logger.error(f"Error creating AOI: {e}")
            return ""
    
    def search_sar_data(self, footprint: str, start_date: str, end_date: str, platform_name: str = 'Sentinel-1') -> Dict:
        """Search for SAR data within the specified parameters."""
        try:
            # Check if API is authenticated
            if self.api is None:
                logger.error("API not authenticated. Call authenticate() first.")
                return {}
                
            # Convert string dates to datetime objects
            start = datetime.datetime.strptime(start_date, '%Y%m%d').date()
            end = datetime.datetime.strptime(end_date, '%Y%m%d').date()
            
            # Log connection attempt
            logger.info(f"Attempting to connect to Copernicus Open Access Hub at {self.api.api_url}")
            logger.info(f"Search parameters: footprint={footprint[:50]}..., date=({start} to {end}), platform={platform_name}")
            
            # Search for products
            self.products = self.api.query(
                footprint,
                date=(start, end),
                platformname=platform_name,
                producttype='SLC',  # Single Look Complex - best for subsurface analysis
                orbitdirection='ASCENDING'
            )
            
            logger.info(f"Found {len(self.products)} products")
            return self.products
        except Exception as e:
            logger.error(f"Error searching for data: {e}")
            # Add more detailed error information
            import traceback
            logger.debug(f"Detailed error: {traceback.format_exc()}")
            
            # Add connection troubleshooting information
            logger.info("Connection troubleshooting:")
            logger.info("1. Check your internet connection")
            logger.info("2. Verify that the Copernicus Open Access Hub is accessible (https://scihub.copernicus.eu/dhus/)")
            logger.info("3. Ensure your credentials are correct")
            logger.info("4. The service might be temporarily unavailable or under maintenance")
            
            return {}
    
    def download_products(self, limit: int = 1) -> List[str]:
        """Download the found products."""
        if not self.products or len(self.products) == 0:
            logger.warning("No products to download. Run search_sar_data first.")
            return []
        
        try:
            # Check if API is authenticated
            if self.api is None:
                logger.error("API not authenticated. Call authenticate() first.")
                return []
                
            # Sort products by ingestion date
            products_df = self.api.to_dataframe(self.products)
            products_df_sorted = products_df.sort_values('ingestiondate', ascending=False)
            
            # Select the most recent products up to the limit
            products_to_download = products_df_sorted.head(limit)
            product_ids = products_to_download.index.tolist()
            
            # Download the products
            downloaded_products = self.api.download_all(
                product_ids,
                directory_path=str(self.download_path)
            )
            
            # Extract the actual file paths from the downloaded products
            file_paths = []
            # Handle the ResultTuple object correctly
            for product_info in downloaded_products:
                if hasattr(product_info, 'path') and os.path.exists(product_info.path):
                    file_paths.append(product_info.path)
                    logger.info(f"Successfully downloaded: {product_info.path}")
                else:
                    logger.warning(f"Could not find path for product")
            
            return file_paths
        except Exception as e:
            logger.error(f"Error downloading products: {e}")
            return []
    
    def process_sentinel1_data(self, file_path: str) -> Optional[str]:
        """Process Sentinel-1 specific data format."""
        try:
            logger.info(f"Processing Sentinel-1 data: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error processing Sentinel-1 data: {e}")
            return None

    def analyze_area(
        self,
        min_lon: float,
        min_lat: float, 
        max_lon: float,
        max_lat: float,
        start_date: str,
        end_date: str
    ) -> bool:
        """Complete workflow to analyze an area of interest."""
        
        try:
            if not self.authenticate():
                return False

            footprint = self.create_aoi_from_coordinates(
                min_lon, min_lat, max_lon, max_lat
            )
            
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
                
                if processed_file := self.process_sentinel1_data(file_path):
                    if processed_data := self.preprocess_sar_data(processed_file):
                        if features := self.detect_subsurface_features(processed_data):
                            try:
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

    # After the process_sentinel1_data method and before the analyze_area method
    
    def preprocess_sar_data(self, file_path: str) -> Optional[np.ndarray]:
        """Preprocess the SAR data for analysis."""
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                logger.error(f"Error: File does not exist at {file_path}")
                return None
            
            # Print file information for debugging
            logger.info(f"Attempting to process file: {file_path}")
            logger.info(f"File size: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
            
            # Open the raster file
            with rasterio.open(file_path) as src:
                # Print raster information for debugging
                logger.info(f"Raster shape: {src.shape}")
                logger.info(f"Raster bands: {src.count}")
                
                # Read the data
                sar_data = src.read(1)  # Read the first band
                
                # Apply preprocessing steps
                # 1. Convert to decibels
                sar_db = 10 * np.log10(sar_data + 1e-10)  # Add small constant to avoid log(0)
                
                # 2. Apply speckle filtering (Lee filter)
                sar_filtered = self._lee_filter(sar_db, size=5)
                
                # 3. Normalize the data
                sar_normalized = (sar_filtered - np.min(sar_filtered)) / (np.max(sar_filtered) - np.min(sar_filtered))
                
                return sar_normalized
        except RasterioIOError as e:  # Change this line to use the imported class
            logger.error(f"Rasterio IO Error: {e}")
            logger.error("This might be because the file is not a valid raster format or requires additional preprocessing.")
            return None
        except Exception as e:
            logger.error(f"Error preprocessing SAR data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _lee_filter(self, img: np.ndarray, size: int) -> np.ndarray:
        """Apply Lee filter for speckle reduction."""
        img_mean = ndimage.uniform_filter(img, size=size)
        img_sqr_mean = ndimage.uniform_filter(img**2, size=size)
        img_variance = img_sqr_mean - img_mean**2
        
        # Compute the local variance
        overall_variance = np.var(img)
        
        # Lee filter
        img_weights = img_variance / (img_variance + overall_variance)
        img_output = img_mean + img_weights * (img - img_mean)
        
        return img_output
    
    def detect_subsurface_features(self, sar_data: np.ndarray, threshold: float = 0.7) -> Optional[np.ndarray]:
        """Detect potential subsurface features in the SAR data."""
        try:
            # 1. Apply edge detection
            edges = ndimage.sobel(sar_data)
            
            # 2. Apply thresholding to identify strong edges
            edge_threshold = np.max(edges) * threshold
            strong_edges = edges > edge_threshold
            
            # 3. Apply morphological operations to connect edges
            connected_edges = ndimage.binary_closing(strong_edges, structure=np.ones((3, 3)))
            
            # 4. Remove small objects (noise)
            cleaned_features = ndimage.binary_opening(connected_edges, structure=np.ones((2, 2)))
            
            return cleaned_features
        except Exception as e:
            logger.error(f"Error detecting subsurface features: {e}")
            return None
    
    def visualize_results(self, original_data: np.ndarray, processed_data: np.ndarray, 
                          features: np.ndarray, title: str = "SAR Analysis Results") -> None:
        """Visualize the original data, processed data, and detected features."""
        try:
            fig, axes = plt.subplots(1, 3, figsize=(18, 6))
            
            # Plot original data
            axes[0].imshow(original_data, cmap='gray')
            axes[0].set_title('Original SAR Data')
            axes[0].axis('off')
            
            # Plot processed data
            axes[1].imshow(processed_data, cmap='viridis')
            axes[1].set_title('Processed SAR Data')
            axes[1].axis('off')
            
            # Plot detected features
            axes[2].imshow(processed_data, cmap='gray')
            axes[2].imshow(features, cmap='hot', alpha=0.5)
            axes[2].set_title('Detected Subsurface Features')
            axes[2].axis('off')
            
            plt.suptitle(title)
            plt.tight_layout()
            
            # Save the figure
            output_path = self.download_path / 'sar_analysis_results.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Results saved to {output_path}")
            
            plt.show()
        except Exception as e:
            logger.error(f"Error visualizing results: {e}")

def main():
    """Main function to run the SAR analysis tool."""
    logger.info("\n=== Sentinel SAR Data Analysis Tool ===")
    logger.info("This tool fetches and analyzes SAR data to detect potential subsurface features.")
    
    analyzer = SARAnalyzer()
    
    # Default coordinates (Giza, Egypt)
    giza_coords = {
        'min_lon': 31.0,
        'min_lat': 29.9,
        'max_lon': 31.2,
        'max_lat': 30.1
    }
    
    try:
        # Get coordinates with validation
        coords = {}
        for key, default in giza_coords.items():
            while True:
                try:
                    value = input(f"{key} [{default}]: ").strip() or default
                    coords[key] = float(value)
                    break
                except ValueError:
                    logger.error("Please enter a valid number")
        
        # Get date range
        today = datetime.datetime.now()
        one_year_ago = today - datetime.timedelta(days=365)
        
        start_date = input(f"Start date [{one_year_ago.strftime('%Y%m%d')}]: ") or one_year_ago.strftime('%Y%m%d')
        end_date = input(f"End date [{today.strftime('%Y%m%d')}]: ") or today.strftime('%Y%m%d')
        
        logger.info("\nStarting analysis...")
        if analyzer.analyze_area(
            coords['min_lon'],
            coords['min_lat'],
            coords['max_lon'], 
            coords['max_lat'],
            start_date,
            end_date
        ):
            logger.info("\nAnalysis completed successfully!")
            logger.info(f"Results saved to {analyzer.download_path / 'sar_analysis_results.png'}")
        else:
            logger.error("\nAnalysis failed. Please check the error messages above.")
            
    except KeyboardInterrupt:
        logger.info("\nAnalysis cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
