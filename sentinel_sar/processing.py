"""
Processing functions for SAR data.
"""

import os
import datetime
import logging
import numpy as np
from sentinelsat import read_geojson, geojson_to_wkt
import rasterio
from rasterio.errors import RasterioIOError
from scipy import ndimage
from shapely.geometry import box
import geopandas as gpd
import requests
import traceback
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

def create_aoi_from_coordinates(analyzer, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    """Create an Area of Interest (AOI) from coordinates."""
    try:
        # Create a bounding box
        bbox = box(min_lon, min_lat, max_lon, max_lat)
        
        # Convert to GeoDataFrame
        geo_df = gpd.GeoDataFrame({'geometry': [bbox]}, crs='EPSG:4326')
        
        # Save to a temporary GeoJSON file
        temp_geojson = analyzer.download_path / 'temp_aoi.geojson'
        geo_df.to_file(temp_geojson, driver='GeoJSON')
        
        # Convert to WKT
        footprint = geojson_to_wkt(read_geojson(str(temp_geojson)))
        return footprint
    except Exception as e:
        logger.error(f"Error creating AOI: {e}")
        return ""

def search_sar_data(analyzer, footprint: str, start_date: str, end_date: str, platform_name: str = 'Sentinel-1') -> Dict:
    """Search for SAR data within the specified parameters."""
    try:
        # Check if API token is available
        if not analyzer.api:
            logger.error("API token not available. Call authenticate() first.")
            return {}
            
        # Convert string dates to datetime objects
        start = datetime.datetime.strptime(start_date, '%Y%m%d').date()
        end = datetime.datetime.strptime(end_date, '%Y%m%d').date()
        
        # Use the correct OpenSearch API endpoint
        search_url = "https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel1/search.json"
        
        # Create the search parameters
        params = {
            'q': '*',
            'platform': platform_name,
            'productType': 'SLC',
            'geometry': footprint,
            'startDate': f'{start.isoformat()}',
            'completionDate': f'{end.isoformat()}',
            'sortParam': 'startDate',
            'sortOrder': 'descending',
            'maxRecords': 100
        }
        
        # Set up headers with the token
        headers = {
            'Authorization': f'Bearer {analyzer.api}',
            'Accept': 'application/json'
        }
        
        # Log the request details for debugging
        logger.info(f"Making request to: {search_url}")
        logger.info(f"Search parameters: {params}")
        logger.info(f"Using token: {analyzer.api[:10]}...{analyzer.api[-10:] if len(analyzer.api) > 20 else ''}")
        
        # Make the search request
        response = requests.get(search_url, params=params, headers=headers)
        
        if response.status_code == 200:
            products_data = response.json()
            # RESTO API format has a different structure
            analyzer.products = products_data.get('features', [])
            logger.info(f"Found {len(analyzer.products)} products")
            return analyzer.products
        elif response.status_code == 403:
            logger.error("Authentication failed (403 Forbidden). Your token may be invalid or expired.")
            logger.error(f"Response: {response.text}")
            logger.info("Try re-authenticating to get a fresh token.")
            return {}
        else:
            logger.error(f"Search failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {}
            
    except Exception as e:
        logger.error(f"Error searching for data: {e}")
        logger.debug(f"Detailed error: {traceback.format_exc()}")
        return {}



def download_products(analyzer, limit: int = 1) -> List[str]:
    """Download the found products."""
    if not analyzer.products or len(analyzer.products) == 0:
        logger.warning("No products to download. Run search_sar_data first.")
        return []
    
    try:
        # Check if API is authenticated
        if analyzer.api is None:
            logger.error("API not authenticated. Call authenticate() first.")
            return []
            
        # Sort products by ingestion date
        products_df = analyzer.api.to_dataframe(analyzer.products)
        products_df_sorted = products_df.sort_values('ingestiondate', ascending=False)
        
        # Select the most recent products up to the limit
        products_to_download = products_df_sorted.head(limit)
        product_ids = products_to_download.index.tolist()
        
        # Download the products
        downloaded_products = analyzer.api.download_all(
            product_ids,
            directory_path=str(analyzer.download_path)
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



def process_sentinel1_data(analyzer, file_path: str) -> Optional[str]:
    """Process Sentinel-1 specific data format."""
    try:
        logger.info(f"Processing Sentinel-1 data: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error processing Sentinel-1 data: {e}")
        return None


def _lee_filter(img: np.ndarray, size: int) -> np.ndarray:
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

def preprocess_sar_data(analyzer, file_path: str) -> Optional[np.ndarray]:
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
            sar_filtered = _lee_filter(sar_db, size=5)
            
            # 3. Normalize the data
            sar_normalized = (sar_filtered - np.min(sar_filtered)) / (np.max(sar_filtered) - np.min(sar_filtered))
            
            return sar_normalized
    except RasterioIOError as e:
        logger.error(f"Rasterio IO Error: {e}")
        logger.error("This might be because the file is not a valid raster format or requires additional preprocessing.")
        return None
    except Exception as e:
        logger.error(f"Error preprocessing SAR data: {e}")
        logger.error(traceback.format_exc())
        return None

def detect_subsurface_features(sar_data: np.ndarray, threshold: float = 0.7) -> Optional[np.ndarray]:
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